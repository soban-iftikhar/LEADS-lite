from typing import Literal, Optional
from pydantic import BaseModel, Field

CITIES = ["Islamabad", "Lahore", "Karachi", "Rawalpindi", "Peshawar"]


class ScrapeRequest(BaseModel):
    platform: Literal["zameen", "olx"]
    city: str
    count: int = Field(gt=0, le=500)


class ScrapeResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    platform: str
    city: str
    limit: int
    count: int
    status: str
    elapsed_seconds: float
    reason: Optional[str] = None
