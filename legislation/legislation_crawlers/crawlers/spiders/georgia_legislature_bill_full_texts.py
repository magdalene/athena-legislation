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
from datetime import datetime
import io
import os
from urllib.parse import urljoin

from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

import django
from scrapy.spiders import CrawlSpider


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legislation.settings")
django.setup()
from legislation_models.models import *
GEORGIA = Place.objects.get(name='Georgia')
GEORGIA_LEGISLATURE = LegislativeBody.objects.get(place=GEORGIA)


class GeorgiaLegislatureBillFullTexts(CrawlSpider):
    name = 'georgia_bill_full_texts'
    start_urls = [bill.full_text_link
                  for bill in Bill.objects.filter(status=Bill.STATUS_NEEDS_UPDATE, legislative_body=GEORGIA_LEGISLATURE)
                  if bill.full_text_link is not None]

    def parse(self, response):
        filename = '/tmp/leg_%s.pdf' % datetime.now().strftime('%Y%m%d%H%S%f')
        with open(filename, 'wb') as f:
            f.write(response.body)
        fp = io.open(filename, 'rb')
        out_filename = filename.replace('.pdf', '.txt')
        outfp = io.open(out_filename, 'wt', errors='ignore')
        rsrcmgr = PDFResourceManager(caching=True)
        laparams = LAParams()
        device = TextConverter(rsrcmgr, outfp, laparams=laparams)
        pagenos = set()

        process_pdf(rsrcmgr, device, fp, pagenos, maxpages=10, password='',
                    caching=True, check_extractable=True)

        fp.close()
        outfp.close()
        with open(out_filename) as f:
            text = f.read()

        bill = Bill.objects.get(full_text_link=response.url, legislative_body=GEORGIA_LEGISLATURE)
        bill.text = text
        bill.status = Bill.STATUS_UP_TO_DATE
        bill.save()

