import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.campaign_manager import campaign_manager
from app.whatsapp.template import BODY_PREVIEW

router = APIRouter()


class CreateCampaignRequest(BaseModel):
    job_id: str


@router.get("/campaigns/template-preview")
def template_preview():
    return {"body_preview": BODY_PREVIEW}


@router.post("/campaigns")
def create_campaign(req: CreateCampaignRequest):
    try:
        result = campaign_manager.create_campaign(req.job_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


@router.post("/campaigns/{campaign_id}/launch")
async def launch_campaign(campaign_id: str):
    status = campaign_manager.get_status(campaign_id)
    if not status:
        raise HTTPException(404, "Campaign not found")
    if status["status"] != "draft":
        raise HTTPException(400, f"Campaign already {status['status']}")

    asyncio.create_task(campaign_manager.run_campaign(campaign_id))
    return {"status": "launched"}


@router.get("/campaigns/{campaign_id}/status")
def get_campaign_status(campaign_id: str):
    status = campaign_manager.get_status(campaign_id)
    if not status:
        raise HTTPException(404, "Campaign not found")
    return status


@router.get("/campaigns/{campaign_id}/messages")
def get_campaign_messages(campaign_id: str):
    status = campaign_manager.get_status(campaign_id)
    if not status:
        raise HTTPException(404, "Campaign not found")
    return {"messages": campaign_manager.get_messages(campaign_id)}


@router.websocket("/ws/campaigns/{campaign_id}")
async def campaign_socket(websocket: WebSocket, campaign_id: str):
    await websocket.accept()
    campaign_manager.register_socket(campaign_id, websocket)
    try:
        while True:
            state = campaign_manager.get_status(campaign_id)
            if state:
                await websocket.send_json(state)
                if state["status"] == "completed":
                    break
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        campaign_manager.unregister_socket(campaign_id, websocket)
