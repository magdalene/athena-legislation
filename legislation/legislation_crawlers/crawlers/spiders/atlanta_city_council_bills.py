# -*- coding: utf-8 -*-
"""
    This file is part of Athena.

    Athena is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Athena is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Athena.  If not, see <http://www.gnu.org/licenses/>.
"""
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
        sponsor_texts = response.xpath(".//tr/th[contains(., 'Sponsors')]/following-sibling::td//text()").extract()
        sponsors = []
        if len(sponsor_texts):
            sponsor_text = sponsor_texts[0]
            sponsors = ['Councilmember' + name for name in sponsor_text.split('Councilmember')[1:]]
            sponsors = [s.strip(', ') for s in sponsors]
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
        for sponsor_name in sponsors:
            sponsor, created = Sponsor.objects.get_or_create(name_string=sponsor_name, bill=bill)
            if created:
                sponsor.sponsor_type = Sponsor.SPONSOR
                sponsor.save()
