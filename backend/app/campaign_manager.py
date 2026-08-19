import asyncio
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import WebSocket

from app.db import get_db
from app.config import WHATSAPP_MOCK_MODE, WHATSAPP_SEND_DELAY_SECONDS
from app.whatsapp.client import send_template_message, WhatsAppSendError
from app.whatsapp.phone import normalize_for_whatsapp
from app.whatsapp.template import TEMPLATE_NAME

# Status progression rank — used so a late-arriving webhook can't
# downgrade a message that's already progressed further.
STATUS_RANK = {"queued": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 1, "skipped": 1}


class CampaignManager:
    def __init__(self):
        self.sockets: Dict[str, List[WebSocket]] = {}

    # ---- setup -----------------------------------------------------

    def create_campaign(self, job_id: str) -> dict:
        db = get_db()
        leads_col = db["leads"]
        campaigns_col = db["campaigns"]
        messages_col = db["campaign_messages"]

        leads = list(leads_col.find({"job_id": job_id}))
        if not leads:
            raise ValueError("No leads found for this job")

        # Never message the same contact twice across campaigns.
        already_contacted = {
            doc["contact"]
            for doc in messages_col.find(
                {"status": {"$in": ["sent", "delivered", "read"]}},
                {"contact": 1},
            )
        }

        campaign_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        docs = []
        for lead in leads:
            contact = lead.get("contact", "")
            normalized = normalize_for_whatsapp(contact)
            if contact in already_contacted:
                status, error = "skipped", "already contacted in a previous campaign"
            elif not normalized:
                status, error = "skipped", "unusable phone number"
            else:
                status, error = "queued", None
            docs.append({
                "campaign_id": campaign_id,
                "contact": contact,
                "normalized_contact": normalized,
                "seller_name": lead.get("seller_name", ""),
                "status": status,
                "error": error,
                "wa_message_id": None,
                "updated_at": now,
            })

        if docs:
            messages_col.insert_many(docs)

        campaigns_col.insert_one({
            "_id": campaign_id,
            "job_id": job_id,
            "template_name": TEMPLATE_NAME,
            "mock_mode": WHATSAPP_MOCK_MODE,
            "total": len(docs),
            "queued": sum(1 for d in docs if d["status"] == "queued"),
            "skipped": sum(1 for d in docs if d["status"] == "skipped"),
            "status": "draft",
            "created_at": now,
            "started_at": None,
        })
        self.sockets[campaign_id] = []

        return {"campaign_id": campaign_id, "total": len(docs)}

    # ---- sending -----------------------------------------------------

    async def run_campaign(self, campaign_id: str):
        db = get_db()
        campaigns_col = db["campaigns"]
        messages_col = db["campaign_messages"]

        campaigns_col.update_one(
            {"_id": campaign_id},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
        )
        await self.broadcast(campaign_id)

        queued = list(messages_col.find({"campaign_id": campaign_id, "status": "queued"}))
        for msg in queued:
            try:
                wa_id = await send_template_message(
                    msg["normalized_contact"], msg.get("seller_name", "")
                )
                messages_col.update_one(
                    {"_id": msg["_id"]},
                    {"$set": {
                        "status": "sent",
                        "wa_message_id": wa_id,
                        "updated_at": datetime.now(timezone.utc),
                    }},
                )
                if WHATSAPP_MOCK_MODE:
                    asyncio.create_task(self._simulate_delivery(campaign_id, msg["_id"]))
            except WhatsAppSendError as e:
                messages_col.update_one(
                    {"_id": msg["_id"]},
                    {"$set": {
                        "status": "failed",
                        "error": str(e),
                        "updated_at": datetime.now(timezone.utc),
                    }},
                )
            await self.broadcast(campaign_id)
            await asyncio.sleep(WHATSAPP_SEND_DELAY_SECONDS)

        campaigns_col.update_one({"_id": campaign_id}, {"$set": {"status": "completed"}})
        await self.broadcast(campaign_id)

    async def _simulate_delivery(self, campaign_id: str, message_object_id):
        """Mock-mode only: fakes the delivered/read progression a real
        webhook would report, so the stats screen is fully demoable
        before real WhatsApp credentials exist."""
        db = get_db()
        messages_col = db["campaign_messages"]

        await asyncio.sleep(random.uniform(2, 5))
        if random.random() < 0.06:
            messages_col.update_one(
                {"_id": message_object_id},
                {"$set": {"status": "failed", "error": "simulated delivery failure",
                          "updated_at": datetime.now(timezone.utc)}},
            )
            await self.broadcast(campaign_id)
            return

        messages_col.update_one(
            {"_id": message_object_id},
            {"$set": {"status": "delivered", "updated_at": datetime.now(timezone.utc)}},
        )
        await self.broadcast(campaign_id)

        await asyncio.sleep(random.uniform(3, 8))
        if random.random() < 0.75:
            messages_col.update_one(
                {"_id": message_object_id},
                {"$set": {"status": "read", "updated_at": datetime.now(timezone.utc)}},
            )
            await self.broadcast(campaign_id)

    # ---- webhook -----------------------------------------------------

    def apply_webhook_status(self, wa_message_id: str, new_status: str):
        db = get_db()
        messages_col = db["campaign_messages"]
        doc = messages_col.find_one({"wa_message_id": wa_message_id})
        if not doc:
            return None

        if STATUS_RANK.get(new_status, 0) <= STATUS_RANK.get(doc["status"], 0) and new_status != "failed":
            return doc["campaign_id"]

        messages_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}},
        )
        return doc["campaign_id"]

    # ---- status / websocket -----------------------------------------------------

    def get_status(self, campaign_id: str):
        db = get_db()
        campaign = db["campaigns"].find_one({"_id": campaign_id})
        if not campaign:
            return None

        counts = {"queued": 0, "sent": 0, "delivered": 0, "read": 0, "failed": 0, "skipped": 0}
        for doc in db["campaign_messages"].find({"campaign_id": campaign_id}):
            counts[doc["status"]] = counts.get(doc["status"], 0) + 1

        return {
            "campaign_id": campaign_id,
            "job_id": campaign["job_id"],
            "template_name": campaign["template_name"],
            "mock_mode": campaign["mock_mode"],
            "status": campaign["status"],
            "total": campaign["total"],
            "counts": counts,
        }

    def get_messages(self, campaign_id: str):
        db = get_db()
        return [
            {
                "seller_name": d.get("seller_name", ""),
                "contact": d.get("contact", ""),
                "status": d["status"],
                "error": d.get("error"),
            }
            for d in db["campaign_messages"].find({"campaign_id": campaign_id})
        ]

    def register_socket(self, campaign_id: str, ws: WebSocket):
        self.sockets.setdefault(campaign_id, []).append(ws)

    def unregister_socket(self, campaign_id: str, ws: WebSocket):
        if campaign_id in self.sockets and ws in self.sockets[campaign_id]:
            self.sockets[campaign_id].remove(ws)

    async def broadcast(self, campaign_id: str):
        state = self.get_status(campaign_id)
        if not state:
            return
        dead = []
        for ws in self.sockets.get(campaign_id, []):
            try:
                await ws.send_json(state)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister_socket(campaign_id, ws)


campaign_manager = CampaignManager()
