import os
from dotenv import load_dotenv

load_dotenv()

SCRAPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://leads_user:leads_password@127.0.0.1:27018/leads_lite?authSource=admin",
)
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "leads_lite")
CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL", "http://127.0.0.1:8000")

# WhatsApp Cloud API — not issued yet (pending from supervisor). When
# WHATSAPP_TOKEN is unset, the campaign sender automatically runs in mock
# mode (simulates sent/delivered/read/failed) so the rest of the system
# is fully testable without real credentials. Once real values land in
# .env, real sending kicks in automatically — no code changes needed.
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "leads_lite_verify")
WHATSAPP_SEND_DELAY_SECONDS = float(os.getenv("WHATSAPP_SEND_DELAY_SECONDS", "1.0"))

WHATSAPP_MOCK_MODE = not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID)
