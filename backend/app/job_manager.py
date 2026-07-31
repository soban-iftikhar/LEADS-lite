import time
from typing import Dict, List
from fastapi import WebSocket


class JobManager:
    """
    In-memory registry of scrape jobs. Fine for a single-process FastAPI
    instance (which is exactly this subsystem's setup) — no external
    queue needed.
    """

    def __init__(self):
        self.jobs: Dict[str, dict] = {}
        self.sockets: Dict[str, List[WebSocket]] = {}

    def create_job(self, job_id, platform, city, limit, process):
        self.jobs[job_id] = {
            "job_id": job_id,
            "platform": platform,
            "city": city,
            "limit": limit,
            "count": 0,
            "status": "running",
            "started_at": time.time(),
            "reason": None,
            "process": process,
            "log_tail": None,
        }
        self.sockets[job_id] = []

    def mark_crashed(self, job_id, log_tail=""):
        job = self.jobs.get(job_id)
        if job and job["status"] == "running":
            job["status"] = "crashed"
            job["reason"] = "crashed"
            job["log_tail"] = log_tail

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def elapsed(self, job_id):
        job = self.jobs.get(job_id)
        if not job:
            return 0
        return round(time.time() - job["started_at"], 1)

    def public_state(self, job_id):
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job_id,
            "platform": job["platform"],
            "city": job["city"],
            "limit": job["limit"],
            "count": job["count"],
            "status": job["status"],
            "elapsed_seconds": self.elapsed(job_id),
            "reason": job["reason"],
            "log_tail": job.get("log_tail"),
        }

    def update_progress(self, job_id, count):
        job = self.jobs.get(job_id)
        if job and job["status"] == "running":
            job["count"] = count

    def finish_job(self, job_id, count, reason):
        job = self.jobs.get(job_id)
        if job:
            job["count"] = count
            job["reason"] = reason
            if job["status"] == "running":
                job["status"] = "completed" if reason == "target_reached" else "stopped"

    def cancel_job(self, job_id):
        job = self.jobs.get(job_id)
        if job and job.get("process"):
            try:
                job["process"].terminate()
            except Exception:
                pass
            job["status"] = "cancelled"
            job["reason"] = "cancelled"

    def register_socket(self, job_id, ws: WebSocket):
        self.sockets.setdefault(job_id, []).append(ws)

    def unregister_socket(self, job_id, ws: WebSocket):
        if job_id in self.sockets and ws in self.sockets[job_id]:
            self.sockets[job_id].remove(ws)

    async def broadcast(self, job_id):
        state = self.public_state(job_id)
        if not state:
            return
        dead = []
        for ws in self.sockets.get(job_id, []):
            try:
                await ws.send_json(state)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister_socket(job_id, ws)


job_manager = JobManager()
