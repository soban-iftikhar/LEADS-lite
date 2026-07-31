import re
import json
import scrapy
from leads_scraper.spiders.base_lite_spider import BaseLiteSpider


class OLXLiteSpider(BaseLiteSpider):
    name = "olx_lite"
    platform_name = "olx"
    allowed_domains = ["olx.com.pk"]
    BASE_URL = "https://www.olx.com.pk"

    CATEGORIES = {
        "/houses_c1721/": "Houses",
        "/apartments-flats_c1725/": "Apartments",
        "/portions-floors_c41/": "Portions",
        "/residential-plots-land-plots_c40/?filter=type_eq_residential-plots-sale": "Residential Plot",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.id_token = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.access_token = crawler.settings.get("OLX_ACCESS_TOKEN")
        spider.id_token = crawler.settings.get("OLX_ID_TOKEN")
        return spider

    PLAYWRIGHT_META = {
        "playwright": True,
        "playwright_page_goto_kwargs": {
            "wait_until": "networkidle",
            "timeout": 30000,
        },
    }

    def start_requests(self):
        city_slug = self.city.lower()
        for cat_path, cat_name in self.CATEGORIES.items():
            separator = "&" if "?" in cat_path else "?"
            url = f"{self.BASE_URL}{cat_path}{separator}location={city_slug}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_listing_page,
                cb_kwargs={"page": 1},
                meta=self.PLAYWRIGHT_META,
                errback=self.handle_error,
            )

    def parse_listing_page(self, response, page):
        if not self.should_dispatch():
            return
        cards = response.css("li[aria-label='Listing']")
        if not cards:
            self.logger.warning(f"[olx_lite] 0 listings: {response.url}")
            return

        for card in cards:
            if not self.should_dispatch():
                return
            href = card.css("a[title]::attr(href)").get("")
            if not href:
                continue
            url = href if href.startswith("http") else self.BASE_URL + href
            self.dispatched += 1
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta=self.PLAYWRIGHT_META,
                errback=self.handle_error,
            )

        if self.should_dispatch() and page < 20:
            next_url = self._build_next_page_url(response.url, page + 1)
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_listing_page,
                cb_kwargs={"page": page + 1},
                meta=self.PLAYWRIGHT_META,
                errback=self.handle_error,
            )

    def _build_next_page_url(self, current_url, next_page):
        if re.search(r"[?&]page=\d+", current_url):
            return re.sub(r"([?&]page=)\d+", rf"\g<1>{next_page}", current_url)
        separator = "&" if "?" in current_url else "?"
        return f"{current_url}{separator}page={next_page}"

    def parse_detail(self, response):
        # Same rule as zameen_lite: this response was already fetched, so
        # only stop if the actual lead target is met — never on the
        # dispatch cap, which governs *new* requests only.
        if self.leads_collected >= self.limit:
            return
        if response.status in (403, 429):
            self.logger.warning(f"[olx_lite] Blocked [{response.status}]: {response.url}")
            return

        listing_id = self._extract_id(response.url)
        seller_name = response.xpath(
            "//span[normalize-space(text())='Posted by']/following-sibling::div[1]//span/text()"
        ).get("").strip()

        if not seller_name:
            page_title = (response.css("title::text").get("") or "").strip()
            self.logger.warning(
                f"[olx_lite] No seller_name found on {response.url} — <title>: '{page_title}'"
            )
            if not getattr(self, "_debug_dumped", False):
                self._debug_dumped = True
                try:
                    with open("olx_debug_page.html", "wb") as f:
                        f.write(response.body)
                    self.logger.warning(
                        "[olx_lite] Saved full page to scraper/olx_debug_page.html for inspection"
                    )
                except Exception as e:
                    self.logger.warning(f"[olx_lite] Could not save debug page: {e}")

        if self.access_token:
            contact_url = f"{self.BASE_URL}/api/listing/{listing_id}/contactInfo/"
            yield scrapy.Request(
                url=contact_url,
                callback=self.parse_contact_info,
                cb_kwargs={"seller_name": seller_name},
                headers={
                    "Accept": "application/json",
                    "Referer": response.url,
                    "X-Requested-With": "XMLHttpRequest",
                },
                cookies={
                    "kc_access_token": self.access_token,
                    "kc_id_token": self.id_token,
                },
                errback=self.handle_error,
            )
        elif seller_name:
            yield self.build_lead(seller_name=seller_name, contact="")

    def parse_contact_info(self, response, seller_name):
        if response.status == 401:
            if self.access_token:
                self.logger.error(
                    f"[olx_lite] OLX_ACCESS_TOKEN is expired/invalid (401 on {response.url}). "
                    f"Skipping contact lookups for the rest of this run — refresh the token in .env."
                )
                self.access_token = None
            if seller_name:
                yield self.build_lead(seller_name=seller_name, contact="")
            return

        contact = ""
        name = seller_name
        try:
            data = json.loads(response.text)
            name = data.get("name", "") or seller_name
            mobiles = data.get("mobileNumbers") or []
            contact = mobiles[0] if mobiles else data.get("mobile", "")
            if not contact:
                self.logger.warning(
                    f"[olx_lite] contactInfo returned no number — status {response.status} — "
                    f"body starts: '{response.text[:150]}'"
                )
        except Exception as e:
            self.logger.warning(
                f"[olx_lite] contactInfo parse error: {e} — status {response.status} — "
                f"body starts: '{response.text[:150]}'"
            )

        if name or contact:
            yield self.build_lead(seller_name=name, contact=contact)

    def _extract_id(self, url):
        match = re.search(r"iid-(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"-(\d+)/?$", url.rstrip("/"))
        return match.group(1) if match else url.split("/")[-1]
