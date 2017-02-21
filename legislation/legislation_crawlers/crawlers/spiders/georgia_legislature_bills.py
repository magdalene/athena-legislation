# -*- coding: utf-8 -*-
from datetime import datetime
import os
from urllib.parse import urljoin

import django
from scrapy.spiders import CrawlSpider


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legislation.settings")
django.setup()
from legislation_models.models import *
GEORGIA = Place.objects.get(name='Georgia')
GEORGIA_LEGISLATURE = LegislativeBody.objects.get(place=GEORGIA)

YEAR = datetime.now().year
YEAR_INFO = '%s%s' % (YEAR, YEAR + 1)

BILL_URL_FORMAT = 'http://www.legis.ga.gov/Legislation/en-US/display/%s/%%(bill_type)s/%%(number)s' % YEAR_INFO

min_got_404 = {
    'HB': 9999999999,
    'HR': 9999999999,
    'SB': 9999999999,
    'SR': 9999999999
}

def urls():
    global min_got_404
    for bill_type in min_got_404.keys():
        for n in range(0, 100000):
            if min_got_404[bill_type] < n:
                break
            yield BILL_URL_FORMAT % {'bill_type': bill_type, 'number': n}


class GeorgiaLegislatureBillsSpider(CrawlSpider):
    name = 'georgia_bills'
    start_urls = urls()

    def parse(self, response):
        # Check if we found a non-existent bill
        global min_got_404
        split_url = response.url.split('/')
        bill_type = split_url[-2]
        bill_number = int(split_url[-1])
        error = response.xpath(".//div[contains(@class, 'ggaError')]//text()").extract()
        if len(error) and 'Error Returning Legislation Search Results' in error[0]:
            if min_got_404[bill_type] > bill_number:
                min_got_404[bill_type] = bill_number
            return

        # if not, process it
        title_candidates = response.xpath(".//div[contains(@class, 'ggah1')]/text()").extract()
        title = title_candidates[-1] if len(title_candidates) else None
        summary_candidates = response.xpath(".//div[contains(@class, 'itemBar') and contains(., 'Summary')]/following-sibling::div[contains(@class, 'item')]")
        summary = '\n\n'.join(summary_candidates[0].xpath('.//text()').extract()) if len(summary_candidates) else None
        number = '%s %s' % (bill_type, bill_number)
        candidate_text_links = [link for link in response.xpath(".//div[contains(@class, 'itemBar')]//a/@href").extract() if link.endswith('pdf')]
        text_link = candidate_text_links[0] if len(candidate_text_links) else None
        if text_link and not text_link.startswith('http'):
            text_link = urljoin(response.url, text_link)
        bill, _ = Bill.objects.get_or_create(number=number, legislative_body=GEORGIA_LEGISLATURE, link=response.url)
        if (bill.summary != summary
                or bill.title != title
                or bill.full_text_link != text_link):
            bill.status = Bill.STATUS_NEEDS_UPDATE if text_link else Bill.STATUS_UP_TO_DATE
            bill.summary = summary
            bill.title = title
            bill.full_text_link = text_link
            bill.bill_type = 'Bill' if bill_type.endswith('B') else 'Resolution'
            bill.save()
