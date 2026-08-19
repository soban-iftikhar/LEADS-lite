from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import WHATSAPP_WEBHOOK_VERIFY_TOKEN
from app.campaign_manager import campaign_manager

router = APIRouter()


@router.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    """
    Meta's one-time handshake when you register this URL in the
    WhatsApp app dashboard: it GETs with hub.mode/hub.verify_token/
    hub.challenge and expects the challenge echoed back verbatim if
    the verify token matches.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Verification failed", status_code=403)


@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request):
    """
    Meta POSTs delivery/read/failed status updates here as messages
    move through their lifecycle. Not reachable from Meta in local dev
    without a public URL (e.g. ngrok) pointed at this endpoint and
    registered in the WhatsApp app dashboard.
    """
    payload = await request.json()

    touched_campaigns = set()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status_update in value.get("statuses", []):
                wa_message_id = status_update.get("id")
                status = status_update.get("status")
                if not wa_message_id or not status:
                    continue
                campaign_id = campaign_manager.apply_webhook_status(wa_message_id, status)
                if campaign_id:
                    touched_campaigns.add(campaign_id)

    for campaign_id in touched_campaigns:
        await campaign_manager.broadcast(campaign_id)

    return {"status": "ok"}
