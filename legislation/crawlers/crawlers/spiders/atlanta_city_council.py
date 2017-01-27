# -*- coding: utf-8 -*-
from urllib.parse import urljoin

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from dateutil.parser import parse as parsedate

from models.models import *

ATLANTA = Place.objects.get(name='Atlanta')
ATLANTA_CITY_COUNCIL = LegislativeBody.objects.get(place=ATLANTA)


class AlantaCityCouncilSpider(CrawlSpider):
    name = "atlanta"
    allowed_domains = ["http://atlantacityga.iqm2.com/"]
    start_urls = ['http://atlantacityga.iqm2.com/Citizens/Calendar.aspx']
    rules = (
        Rule(LinkExtractor(allow=('.*Detail_LegiFile.*')), callback='parse_ordinance'),
        Rule(LinkExtractor(allow='.*Detail_Meeting.*'), callback='parse_meeting')
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
        ordinance_urls = []
        ordinance_links = response.css('#MeetingDetail tr .Title .Link')
        for ordinance_link in ordinance_links:
            text = ordinance_link.xpath('./text()').extract()[0]
            number = text.split(':')[0].strip()
            summary = ':'.join([s for s in text.split(':')[1:]]).strip()
            link = urljoin(response.url, ordinance_link.xpath('./@href').extract()[0])
            ordinance_urls.append(link)
            bill, created = Bill.objects.get_or_create(number=number, legislative_body=ATLANTA_CITY_COUNCIL)
            if created:
                bill.summary = summary
                bill.link = link
                bill.save()
            agenda_item, _ = AgendaItem.objects.get_or_create(meeting=meeting, bill=bill)
        #for url in ordinance_urls:
        #    yield scrapy.Request(url)


