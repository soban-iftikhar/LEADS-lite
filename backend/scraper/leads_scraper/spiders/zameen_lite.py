import re
import json
import scrapy
from itertools import product
from leads_scraper.spiders.base_lite_spider import BaseLiteSpider


class ZameenLiteSpider(BaseLiteSpider):
    name = "zameen_lite"
    platform_name = "zameen"
    allowed_domains = ["zameen.com"]

    CITY_IDS = {
        "Islamabad": 3,
        "Lahore": 2,
        "Karachi": 1,
        "Rawalpindi": 41,
        "Peshawar": 6,
    }

    CATEGORIES = {
        "Homes": "Homes",
        "Plots": "Plots",
        "Flats": "Flats",
        "Commercial": "Commercial",
    }

    PURPOSES = {"buy": 1, "rent": 2}

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def start_requests(self):
        city_id = self.CITY_IDS.get(self.city)
        if not city_id:
            self.logger.error(f"[zameen_lite] Unsupported city: {self.city}")
            return

        for (cat_name, cat_path), (purpose_name, purpose_id) in product(
            self.CATEGORIES.items(), self.PURPOSES.items()
        ):
            url = (
                f"https://www.zameen.com/{cat_path}/"
                f"{self.city}-{city_id}-1.html?purpose={purpose_id}"
            )
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                cb_kwargs={"page": 1},
                headers=self.HEADERS,
                errback=self.handle_error,
            )

    def parse(self, response, page):
        if not self.should_dispatch():
            return

        listings = response.css("li[aria-label='Listing']")
        if not listings:
            self.logger.warning(f"[zameen_lite] 0 listings: {response.url}")
            return

        for listing in listings:
            if not self.should_dispatch():
                return
            link = listing.css("a[aria-label='Listing link']::attr(href)").get()
            if not link:
                link = listing.css("a::attr(href)").get()
            if not link:
                continue
            detail_url = link if link.startswith("http") else f"https://www.zameen.com{link}"
            self.dispatched += 1
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_property,
                meta={
                    "playwright": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "domcontentloaded",
                        "timeout": 30000,
                    },
                },
                headers={**self.HEADERS, "Referer": response.url},
                errback=self.handle_error,
            )

        if self.should_dispatch() and page < 20:
            next_url = self._get_next_page(response, page)
            if next_url:
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse,
                    cb_kwargs={"page": page + 1},
                    headers=self.HEADERS,
                    errback=self.handle_error,
                )

    def _get_next_page(self, response, current_page):
        next_link = response.css("a[title='Next']::attr(href)").get()
        if next_link:
            return next_link if next_link.startswith("http") else f"https://www.zameen.com{next_link}"
        base_url = response.url.split("?")[0]
        match = re.search(r"-(\d+)(\.html)$", base_url)
        if match:
            next_page = current_page + 1
            next_url = base_url.replace(
                f"-{match.group(1)}{match.group(2)}", f"-{next_page}{match.group(2)}"
            )
            if "?" in response.url:
                next_url += "?" + response.url.split("?")[1]
            return next_url
        return None

    def parse_property(self, response):
        # NOTE: this runs on a response we already paid the network cost
        # for — only bail if we've truly hit the lead target, never on
        # should_dispatch() (that cap is only for deciding whether to send
        # *new* requests, checked in parse() before yielding them).
        if self.leads_collected >= self.limit:
            return
        if response.status in (403, 429):
            self.logger.warning(f"[zameen_lite] Blocked [{response.status}]: {response.url}")
            return

        seller_name = (
            response.css("[aria-label='Agent name']::text").get("")
            or response.css("[aria-label='Seller name']::text").get("")
        ).strip()
        external_id = self._extract_external_id(response.url)

        if not seller_name and not external_id:
            page_title = (response.css("title::text").get("") or "").strip()
            has_price = bool(response.css("span[aria-label='Price']::text").get())
            has_title_marker = bool(response.css("[aria-label='Title']::text").get())
            self.logger.warning(
                f"[zameen_lite] No seller_name/external_id on {response.url} — "
                f"<title>: '{page_title}' — has_price_marker: {has_price} — "
                f"has_title_marker: {has_title_marker}"
            )
            if not getattr(self, "_debug_dumped", False):
                self._debug_dumped = True
                try:
                    with open("zameen_debug_page.html", "wb") as f:
                        f.write(response.body)
                    self.logger.warning(
                        "[zameen_lite] Saved full page to scraper/zameen_debug_page.html for inspection"
                    )
                except Exception as e:
                    self.logger.warning(f"[zameen_lite] Could not save debug page: {e}")
            return

        if external_id:
            phone_api_url = (
                f"https://www.zameen.com/api/showNumbers?"
                f"listingExternalID={external_id}&isProject=false"
            )
            yield scrapy.Request(
                url=phone_api_url,
                callback=self.parse_phone,
                cb_kwargs={"seller_name": seller_name},
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Referer": response.url,
                    "X-Requested-With": "XMLHttpRequest",
                },
                errback=self.handle_error,
            )
        elif seller_name:
            yield self.build_lead(seller_name=seller_name, contact="")

    def parse_phone(self, response, seller_name):
        contact = ""
        agency_name = ""
        try:
            data = json.loads(response.text)
            if data.get("success"):
                details = data.get("contact_details", {})
                phones = details.get("phone", [])
                contact = phones[0] if phones else details.get("mobile", "")
                agency_name = details.get("agency_name", "")
            else:
                self.logger.warning(
                    f"[zameen_lite] Phone API success=false — status {response.status} — "
                    f"body starts: '{response.text[:150]}'"
                )
        except Exception as e:
            self.logger.warning(
                f"[zameen_lite] Phone API error: {e} — status {response.status} — "
                f"body starts: '{response.text[:150]}'"
            )

        final_name = seller_name or agency_name
        if final_name or contact:
            yield self.build_lead(seller_name=final_name, contact=contact)

    def _extract_external_id(self, url):
        match = re.search(r"-(\d{7,})-\d+-\d+\.html$", url)
        return match.group(1) if match else ""
