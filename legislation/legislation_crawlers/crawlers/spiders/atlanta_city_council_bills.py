# -*- coding: utf-8 -*-
from urllib.parse import urljoin

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from dateutil.parser import parse as parsedate

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legislation.settings")
django.setup()
from legislation_models.models import *
ATLANTA = Place.objects.get(name='Atlanta')
ATLANTA_CITY_COUNCIL = LegislativeBody.objects.get(place=ATLANTA)


class AlantaCityCouncilOrdinanceSpider(CrawlSpider):
    name = "atlanta_bills"
    start_urls = [bill.link
                  for bill in Bill.objects.filter(status=Bill.STATUS_NEEDS_UPDATE, legislative_body=ATLANTA_CITY_COUNCIL)
                  if bill.link is not None]

    def parse(self, response):
        bill_type = response.css('#ContentPlaceholder1_lblLegiFileType')[0].xpath('text()').extract()[0]
        number = response.css('#ContentPlaceholder1_lblResNum')[0].xpath('text()').extract()[0]
        summary = response.css('#ContentPlaceholder1_lblLegiFileTitle')[0].xpath('text()').extract()[0]
        text_paragraphs = response.css('#divBody .LegiFileSectionContents p')
        text_paragraph_texts = [''.join(p.xpath('.//text()').extract()).strip() for p in text_paragraphs]
        text = '\n\n'.join([p for p in text_paragraph_texts if len(p)])
        link = response.url
        # TODO: history
        # TODO: sponsor(s)
        bill, _ = Bill.objects.get_or_create(number=number, legislative_body=ATLANTA_CITY_COUNCIL)
        bill.bill_type = bill_type
        bill.summary = summary
        bill.link = link
        bill.text = text
        bill.status = Bill.STATUS_UP_TO_DATE
        bill.save()
