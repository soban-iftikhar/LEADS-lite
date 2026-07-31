import os
import scrapy


class BaseLiteSpider(scrapy.Spider):
    """
    Shared logic for the lead-only spiders. A child spider only needs to
    yield LeadItem via self.build_lead(...) — counting, stopping and the
    "job finished" callback are all handled here.
    """

    platform_name = None

    def __init__(self, city=None, limit=50, job_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.limit = int(limit)
        self.job_id = job_id
        self.leads_collected = 0
        self.dispatched = 0  # detail-page requests sent — caps runaway bursts

    def build_lead(self, seller_name="", contact=""):
        from leads_scraper.items import LeadItem
        item = LeadItem()
        item["job_id"] = self.job_id
        item["platform"] = self.platform_name
        item["city"] = self.city
        item["seller_name"] = seller_name
        item["contact"] = contact
        return item

    def should_dispatch(self):
        """
        Caps the number of detail-page requests in flight/scheduled to a
        small multiple of the requested lead count. Without this, a single
        search-results page (which can list 25+ items) gets all of its
        detail requests queued in one shot — before any of them have had a
        chance to complete and update leads_collected — so hitting the
        target doesn't stop the crawl from grinding through the rest of
        that backlog.
        """
        if self.leads_collected >= self.limit:
            return False
        if self.dispatched >= self.limit * 10:
            return False
        return True

    def handle_error(self, failure):
        self.logger.error(f"[{self.platform_name}] Failed: {failure.request.url} — {failure.value}")

    def closed(self, reason):
        import requests
        callback = os.getenv("CALLBACK_BASE_URL", "http://127.0.0.1:8000")
        try:
            requests.post(
                f"{callback}/internal/jobs/{self.job_id}/finished",
                json={"count": self.leads_collected, "reason": reason},
                timeout=3,
            )
        except Exception:
            self.logger.warning("[base_lite] Could not notify backend of completion")
