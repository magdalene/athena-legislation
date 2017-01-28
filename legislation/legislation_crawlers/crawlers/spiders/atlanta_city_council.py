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


class AlantaCityCouncilSpider(CrawlSpider):
    name = "atlanta"
    allowed_domains = ["atlantacityga.iqm2.com"]
    start_urls = ['http://atlantacityga.iqm2.com/Citizens/Calendar.aspx']
    rules = (
        # TODO: add motions?
        Rule(LinkExtractor(allow='.*Detail_LegiFile.*',
                           deny=['.*Print=Yes.*', '.*FileOpen.*', '.*Detail_Motion.*']),
             callback='parse_ordinance'),
        Rule(LinkExtractor(allow='.*Detail_Meeting.*',
                           deny=['.*Print=Yes.*', '.*FileOpen.*', '.*Detail_Motion.*']),
             callback='parse_meeting', follow=True)
    )

    def parse_ordinance(self, response):
        bill_type = response.css('#ContentPlaceholder1_lblLegiFileType')[0].xpath('text()').extract()[0]
        number = response.css('#ContentPlaceholder1_lblResNum')[0].xpath('text()').extract()[0]
        summary = response.css('#ContentPlaceholder1_lblLegiFileTitle')[0].xpath('text()').extract()[0]
        text_paragraphs = response.css('#divBody .LegiFileSectionContents p')
        text_paragraph_texts = [' '.join(p.xpath('.//text()').extract()).strip() for p in text_paragraphs]
        text = '\n\n'.join([p for p in text_paragraph_texts if len(p)])
        link = response.url
        # TODO: history
        # TODO: sponsor(s)
        bill, _ = Bill.objects.get_or_create(number=number, legislative_body=ATLANTA_CITY_COUNCIL)
        bill.bill_type = bill_type
        bill.summary = summary
        bill.link = link
        bill.text = text
        bill.save()

    def parse_meeting(self, response):
        datestring = response.css('#ContentPlaceholder1_lblMeetingDate::text').extract()[0]
        name = response.css('#ContentPlaceholder1_lblMeetingGroup::text')[0].extract()
        address = response.css('.MeetingAddress::text').extract()[0].replace('\xa0', ' ')
        meeting, _ = Meeting.objects.get_or_create(
            legislative_body=ATLANTA_CITY_COUNCIL, date=parsedate(datestring), name=name)
        meeting.address = address
        meeting.link = response.url
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
                bill.save()
            agenda_item, _ = AgendaItem.objects.get_or_create(meeting=meeting, bill=bill)


