from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.job_manager import job_manager

router = APIRouter()


class ProgressPayload(BaseModel):
    count: int
    limit: Optional[int] = None


class FinishedPayload(BaseModel):
    count: int
    reason: str


@router.post("/jobs/{job_id}/progress")
async def report_progress(job_id: str, payload: ProgressPayload):
    job_manager.update_progress(job_id, payload.count)
    await job_manager.broadcast(job_id)
    return {"ok": True}


@router.post("/jobs/{job_id}/finished")
async def report_finished(job_id: str, payload: FinishedPayload):
    job_manager.finish_job(job_id, payload.count, payload.reason)
    await job_manager.broadcast(job_id)
    return {"ok": True}
