# -*- coding: utf-8 -*-
from urllib.parse import urljoin

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from dateutil.parser import parse as parsedate

import os
import django
import re
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legislation.settings")
django.setup()
from legislation_models.models import *
SANDY_SPRINGS = Place.objects.get(name='Sandy Springs')
SANDY_SPRINGS_CITY_COUNCIL = LegislativeBody.objects.get(place=SANDY_SPRINGS)

TIME_PATTERN = re.compile(r'(\d:\d\d\s[a|p]\.m\.)')

class SandySpringsCityCouncilMeetingSpider(CrawlSpider):
    name = "sandy_springs_meetings"
    allowed_domains = ["www.sandyspringsga.gov", "sandyspringsga.gov"]
    start_urls = ['http://www.sandyspringsga.gov/government/public-meetings-calendar']
    #http://www.sandyspringsga.gov/Home/Components/MeetingsManager/MeetingAgenda/HtmlView/?id=2476&published=True&includeTrash=False
    rules = (
        Rule(LinkExtractor(allow='.*MeetingAgenda\/HtmlView.*'),
             callback='parse_meeting', follow=True, process_links='process_links'),
    )

    def process_links(self, links):
        for link in links:
            if Meeting.objects.filter(link=link.url).count():
                continue
            yield link

    def parse_meeting(self, response):
        meeting_info_pars = response.css('.meeting_header .layout_column p::text')
        name = meeting_info_pars[1].extract().strip()
        date_text = meeting_info_pars[2].extract()
        if 'CANCELLED' in date_text:
            other_info = 'MEETING CANCELLED'
        else:
            other_info = None
        date_text = date_text.replace('- Meeting CANCELLED', '').strip()
        time_text = meeting_info_pars[3].extract().strip()
        address = meeting_info_pars[4].extract().strip() if len(meeting_info_pars) >= 5 else None
        candidate_times = [match for match in re.findall(TIME_PATTERN, time_text)]
        if len(candidate_times):
            meeting_time = min([parsedate('%s %s' % (date_text, candidate_time))
                                for candidate_time in candidate_times])
        else:
            meeting_time = parsedate(date_text.replace(', \xa0', ' '))
        meeting, _ = Meeting.objects.get_or_create(legislative_body=SANDY_SPRINGS_CITY_COUNCIL,
                                                   date=meeting_time, name=name, other_info=other_info)
        meeting.address = address
        meeting.link = response.url
        meeting.save()

        meeting_item_contents = response.css('.meeting_item_content')

        for meeting_item_el in meeting_item_contents:
            if not (len(meeting_item_el.xpath(".//span[contains(@class, 'item_id_number')]"))
                    and len(meeting_item_el.xpath(".//div[contains(@class, 'item_content')]"))):
                continue
            number = meeting_item_el.xpath(".//span[contains(@class, 'item_id_number')]/span/text()").extract()[0].strip()
            paragraph_texts = [text.strip() for text in meeting_item_el.xpath(".//div[contains(@class,'item_content')]/p/text()").extract()]
            summary = paragraph_texts[0]
            for paragraph_text in paragraph_texts:
                if len(paragraph_text) > len(summary):
                    summary = paragraph_text
            link_els = meeting_item_el.xpath(".//div[contains(@class, 'item_content')]//a")
            if len(link_els):
                link_el = link_els[0]
                link = urljoin(response.url, link_el.xpath('./@href').extract()[0])
            else:
                link = None
            bill, created = Bill.objects.get_or_create(number=number, legislative_body=SANDY_SPRINGS_CITY_COUNCIL)
            if created:
                bill.summary = summary
                bill.link = link
            if created or (bill.status != Bill.STATUS_NEEDS_UPDATE and link is not None):
                bill.status = Bill.STATUS_NEEDS_UPDATE
                bill.save()
            if link is None and not Bill.status == Bill.STATUS_UP_TO_DATE:
                bill.status = Bill.STATUS_UP_TO_DATE
                bill.save()
            agenda_item, _ = AgendaItem.objects.get_or_create(meeting=meeting, bill=bill)
