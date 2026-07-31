import csv
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db import get_db

router = APIRouter()


@router.get("/scrape/{job_id}/export")
def export_csv(job_id: str):
    db = get_db()
    leads = list(db["leads"].find({"job_id": job_id}, {"_id": 0}))
    if not leads:
        raise HTTPException(404, "No leads found for this job")

    buffer = io.StringIO()
    fieldnames = ["platform", "city", "seller_name", "contact", "scraped_at"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_{job_id[:8]}.csv"},
    )
