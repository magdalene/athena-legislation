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


class AlantaCityCouncilMeetingSpider(CrawlSpider):
    name = "atlanta"
    allowed_domains = ["atlantacityga.iqm2.com"]
    start_urls = ['http://atlantacityga.iqm2.com/Citizens/Calendar.aspx']
    #start_urls = ['http://atlantacityga.iqm2.com/Citizens/Detail_Meeting.aspx?ID=1984']
    rules = (
        Rule(LinkExtractor(allow='.*Detail_Meeting.*',
                           deny=['.*Print=Yes.*', '.*FileOpen.*', '.*Detail_Motion.*']),
             callback='parse_meeting', follow=True, process_links='process_links'),
    )

    def process_links(self, links):
        for link in links:
            if Meeting.objects.filter(link=link.url).count():
                continue
            yield link

    def parse_meeting(self, response):
        datestring = response.css('#ContentPlaceholder1_lblMeetingDate::text').extract()[0]
        name = response.css('#ContentPlaceholder1_lblMeetingGroup::text')[0].extract()
        address = response.css('.MeetingAddress::text').extract()[0].replace('\xa0', ' ')
        meeting, _ = Meeting.objects.get_or_create(
            legislative_body=ATLANTA_CITY_COUNCIL, date=parsedate(datestring), name=name)
        meeting.address = address
        meeting.link = response.url
        meeting.save()
        ordinance_urls = []
        ordinance_links = response.css('#MeetingDetail tr .Title .Link')
        for ordinance_link in ordinance_links:
            text_list = ordinance_link.xpath('./text()').extract()
            if not len(text_list):
                continue
            link = urljoin(response.url, ordinance_link.xpath('./@href').extract()[0])
            if 'Detail_Meeting' in link or 'FileOpen' in link or 'Detail_Motion' in link:
                continue
            text = text_list[0]
            number = text.split(':')[0].strip()
            summary = ':'.join([s for s in text.split(':')[1:]]).strip()
            ordinance_urls.append(link)
            bill, created = Bill.objects.get_or_create(number=number, legislative_body=ATLANTA_CITY_COUNCIL)
            if created:
                bill.summary = summary
                bill.link = link
            if created or bill.status != Bill.STATUS_NEEDS_UPDATE:
                bill.status = Bill.STATUS_NEEDS_UPDATE
                bill.save()
            agenda_item, _ = AgendaItem.objects.get_or_create(meeting=meeting, bill=bill)


