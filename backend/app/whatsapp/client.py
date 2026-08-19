"""
Thin wrapper around the WhatsApp Cloud API's template-message send call.

Real mode: POSTs to graph.facebook.com using WHATSAPP_TOKEN /
WHATSAPP_PHONE_NUMBER_ID from .env.

Mock mode (default until Meta issues real credentials): returns a fake
message id immediately so the rest of the pipeline — DB writes,
websocket updates, the stats dashboard — works exactly the same way.
Delivery/read progression in mock mode is simulated by campaign_manager,
not here (this module only covers the initial "send" call).
"""
import uuid
import httpx

from app.config import (
    WHATSAPP_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_VERSION,
    WHATSAPP_MOCK_MODE,
)
from app.whatsapp.template import TEMPLATE_NAME, LANGUAGE_CODE, build_components


class WhatsAppSendError(Exception):
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


async def send_template_message(to: str, seller_name: str) -> str:
    """
    Sends the configured template to `to` (already normalized, digits
    only, e.g. 923001234567). Returns the WhatsApp message id (used
    later to match incoming webhook status updates back to this send).
    Raises WhatsAppSendError on failure.
    """
    if WHATSAPP_MOCK_MODE:
        return f"mock.{uuid.uuid4().hex}"

    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": LANGUAGE_CODE},
            "components": build_components(seller_name),
        },
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise WhatsAppSendError("Network error calling WhatsApp API", str(e))

    if resp.status_code >= 400:
        raise WhatsAppSendError(
            f"WhatsApp API returned {resp.status_code}", resp.text[:300]
        )

    data = resp.json()
    try:
        return data["messages"][0]["id"]
    except (KeyError, IndexError):
        raise WhatsAppSendError("Unexpected WhatsApp API response", str(data)[:300])
