import scrapy


class LeadItem(scrapy.Item):
    job_id = scrapy.Field()
    platform = scrapy.Field()
    city = scrapy.Field()
    seller_name = scrapy.Field()
    contact = scrapy.Field()
    scraped_at = scrapy.Field()
