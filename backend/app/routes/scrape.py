import asyncio
import collections
import os
import subprocess
import sys
import threading
import uuid
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.models import ScrapeRequest, ScrapeResponse, CITIES
from app.job_manager import job_manager
from app.config import SCRAPER_DIR, CALLBACK_BASE_URL

router = APIRouter()

SPIDER_MAP = {
    "zameen": "zameen_lite",
    "olx": "olx_lite",
}


def _watch_process(job_id: str, process: subprocess.Popen, tail: collections.deque):
    """
    Runs in a background thread. Continuously drains the subprocess's
    stdout into an in-memory rolling buffer (never written to disk —
    the job_*.log files were only ever for debugging) so the pipe can't
    fill up and block the subprocess. If the process dies without the
    spider's own closed()-hook marking the job finished (i.e. it crashed
    on startup), surface the buffered tail instead of leaving the
    frontend stuck on "running" forever.
    """
    if process.stdout:
        for line in process.stdout:
            tail.append(line)
        process.stdout.close()
    process.wait()

    job = job_manager.get_job(job_id)
    if job and job["status"] == "running":
        job_manager.mark_crashed(job_id, "".join(tail))


@router.get("/cities")
def get_cities():
    return {"cities": CITIES}


@router.post("/scrape/start", response_model=ScrapeResponse)
def start_scrape(req: ScrapeRequest):
    if req.city not in CITIES:
        raise HTTPException(400, f"Unsupported city: {req.city}")

    job_id = str(uuid.uuid4())
    spider_name = SPIDER_MAP[req.platform]

    env = os.environ.copy()
    env["CALLBACK_BASE_URL"] = CALLBACK_BASE_URL

    # Use "python -m scrapy" with sys.executable instead of the bare "scrapy"
    # command — guarantees the subprocess runs under the exact same venv as
    # FastAPI itself, regardless of what PATH resolves "scrapy" to.
    cmd = [
        sys.executable, "-m", "scrapy", "crawl", spider_name,
        "-a", f"city={req.city}",
        "-a", f"limit={req.count}",
        "-a", f"job_id={job_id}",
    ]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=SCRAPER_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        raise HTTPException(500, "scrapy not found — did you install backend/requirements.txt?")

    job_manager.create_job(job_id, req.platform, req.city, req.count, process)

    tail = collections.deque(maxlen=50)
    threading.Thread(
        target=_watch_process, args=(job_id, process, tail), daemon=True
    ).start()

    return ScrapeResponse(job_id=job_id)


@router.get("/scrape/{job_id}/status")
def get_status(job_id: str):
    state = job_manager.public_state(job_id)
    if not state:
        raise HTTPException(404, "Job not found")
    return state


@router.post("/scrape/{job_id}/cancel")
def cancel_scrape(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job_manager.cancel_job(job_id)
    return {"status": "cancelled"}


@router.websocket("/ws/jobs/{job_id}")
async def job_socket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job_manager.register_socket(job_id, websocket)
    try:
        while True:
            state = job_manager.public_state(job_id)
            if state:
                await websocket.send_json(state)
                if state["status"] != "running":
                    break
            try:
                # Don't just wait for a push — poll every 2s too, so a
                # crashed subprocess (detected by the watchdog thread)
                # shows up even if it never got to call back in.
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        job_manager.unregister_socket(job_id, websocket)
