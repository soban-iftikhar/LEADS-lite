import requests
from datetime import datetime
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem, CloseSpider
import pymongo


class LeadsPipeline:
    """
    Stripped-down pipeline for the lead-generation subsystem.
    Stores only platform/city/seller_name/contact, reports progress
    back to the FastAPI backend after every item, and stops the spider
    once the requested lead count is reached.
    """

    def __init__(self, mongo_uri, mongo_db, callback_base_url):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.callback_base_url = callback_base_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_db=crawler.settings.get("MONGO_DATABASE"),
            callback_base_url=crawler.settings.get("CALLBACK_BASE_URL"),
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[self.mongo_db]
        self.collection = self.db["leads"]
        self.seen_contacts = set()
        try:
            self.client.admin.command("ping")
            spider.logger.info("[leads_pipeline] MongoDB connected")
        except Exception as e:
            spider.logger.error(f"[leads_pipeline] MongoDB connection failed: {e}")
            raise
        self.collection.create_index([("job_id", 1)])

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        contact = adapter.get("contact")
        if not contact:
            raise DropItem("No contact number — dropped")

        # Same seller often has several listings — one contact should
        # only ever produce one lead per run.
        normalized_contact = "".join(ch for ch in contact if ch.isdigit())
        if normalized_contact and normalized_contact in self.seen_contacts:
            raise DropItem(f"Duplicate contact — already have {normalized_contact}")
        if normalized_contact:
            self.seen_contacts.add(normalized_contact)

        # Stop accepting new items once target is already hit
        # (protects against a burst of in-flight responses landing together)
        if spider.leads_collected >= spider.limit:
            raise DropItem("Target already reached")

        adapter["scraped_at"] = datetime.utcnow()
        doc = dict(adapter)

        try:
            self.collection.insert_one(doc)
        except Exception as e:
            spider.logger.error(f"[leads_pipeline] Mongo insert failed: {e}")
            raise DropItem(f"DB write failure: {e}")

        spider.leads_collected += 1
        self._report_progress(spider)

        if spider.leads_collected >= spider.limit:
            raise CloseSpider("target_reached")

        return item

    def _report_progress(self, spider):
        try:
            requests.post(
                f"{self.callback_base_url}/internal/jobs/{spider.job_id}/progress",
                json={"count": spider.leads_collected, "limit": spider.limit},
                timeout=2,
            )
        except Exception:
            spider.logger.warning("[leads_pipeline] progress callback failed")
