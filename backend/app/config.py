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
