from fastapi import APIRouter, HTTPException

from app.db import get_db

router = APIRouter()


@router.get("/leads/jobs")
def list_lead_jobs():
    """
    Groups the leads collection by job_id so the "Review Leads" screen
    can show past scrape runs to pick from — no separate job-persistence
    needed since every lead already carries its job_id, platform, city.
    """
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": "$job_id",
            "platform": {"$first": "$platform"},
            "city": {"$first": "$city"},
            "count": {"$sum": 1},
            "scraped_at": {"$max": "$scraped_at"},
        }},
        {"$sort": {"scraped_at": -1}},
    ]
    jobs = list(db["leads"].aggregate(pipeline))
    return {
        "jobs": [
            {
                "job_id": j["_id"],
                "platform": j["platform"],
                "city": j["city"],
                "count": j["count"],
                "scraped_at": j["scraped_at"].isoformat() if j.get("scraped_at") else None,
            }
            for j in jobs
        ]
    }


@router.get("/leads/jobs/{job_id}")
def get_job_leads(job_id: str):
    db = get_db()
    leads = list(db["leads"].find({"job_id": job_id}, {"_id": 0}))
    if not leads:
        raise HTTPException(404, "No leads found for this job")
    return {
        "job_id": job_id,
        "leads": [
            {
                "seller_name": l.get("seller_name", ""),
                "contact": l.get("contact", ""),
                "platform": l.get("platform", ""),
                "city": l.get("city", ""),
            }
            for l in leads
        ],
    }
