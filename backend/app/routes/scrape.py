import asyncio
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


def _watch_process(job_id: str, process: subprocess.Popen, log_path: str):
    """
    Runs in a background thread. If the scrapy subprocess dies without the
    spider's own closed()-hook ever marking the job finished (i.e. it
    crashed on startup, like an import error), surface the real error
    instead of leaving the frontend stuck on "running" forever.
    """
    process.wait()
    job = job_manager.get_job(job_id)
    if job and job["status"] == "running":
        tail = ""
        try:
            with open(log_path, "r", errors="ignore") as f:
                lines = f.readlines()
                tail = "".join(lines[-25:])
        except Exception:
            pass
        job_manager.mark_crashed(job_id, tail)


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

    log_path = os.path.join(SCRAPER_DIR, f"job_{job_id}.log")
    log_file = open(log_path, "w")

    try:
        process = subprocess.Popen(
            cmd,
            cwd=SCRAPER_DIR,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        raise HTTPException(500, "scrapy not found — did you install backend/requirements.txt?")

    job_manager.create_job(job_id, req.platform, req.city, req.count, process)

    threading.Thread(
        target=_watch_process, args=(job_id, process, log_path), daemon=True
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
