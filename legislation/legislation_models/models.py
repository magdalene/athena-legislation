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
from django.db import models
from django.contrib.auth.models import User

from elasticsearch_dsl import Search as EsSearch, Q


class Place(models.Model):
    name = models.CharField(max_length=256, null=False)
    link = models.CharField(max_length=1024, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'place'


class State(models.Model):
    place = models.ForeignKey('Place', null=False)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'state'


class City(models.Model):
    place = models.ForeignKey('Place', null=False)
    state = models.ForeignKey('State', null=False)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'city'


class LegislativeBody(models.Model):
    place = models.ForeignKey('Place', null=False)
    name = models.CharField(max_length=256, null=False)
    link = models.CharField(max_length=1024, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'legislative_body'

class Legislator(models.Model):
    legislative_body = models.ForeignKey('LegislativeBody', null=False)
    last_name = models.CharField(max_length=256, null=False)
    first_name = models.CharField(max_length=256, null=True)
    district = models.CharField(max_length=256, null=True)
    link = models.CharField(max_length=1024, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'legislator'


class Sponsor(models.Model):
    SPONSOR = 'SP'
    COSPONSOR = 'CO'
    legislator = models.ForeignKey('Legislator', null=True)
    name_string = models.CharField(max_length=256, null=False)
    bill = models.ForeignKey('Bill', null=False)
    sponsor_type = models.CharField(max_length=2, choices=((SPONSOR, 'Sponsor'), (COSPONSOR, 'Co-sponsor')), null=False)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sponsor'


class Bill(models.Model):
    STATUS_NEEDS_UPDATE = 'NU'
    STATUS_UP_TO_DATE = 'UTD'
    number = models.CharField(max_length=256, null=False)
    legislative_body = models.ForeignKey('LegislativeBody', null=False)
    bill_type = models.CharField(max_length=1024, null=True)
    title = models.CharField(max_length=1024, null=True)
    text = models.TextField(null=True)
    summary = models.TextField(null=True)
    link = models.CharField(max_length=1024, null=True)
    full_text_link = models.CharField(max_length=1024, null=True)
    status = models.CharField(max_length=3,
                              choices=((STATUS_NEEDS_UPDATE, 'Needs Update'),
                                       (STATUS_UP_TO_DATE, 'Up-to-date')),
                              default=STATUS_NEEDS_UPDATE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bill'


class BillHistoryLine(models.Model):
    bill = models.ForeignKey('Bill', null=False)
    line = models.TextField(null=True)
    date = models.DateField(null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bill_history_line'


class Meeting(models.Model):
    legislative_body = models.ForeignKey('LegislativeBody', null=False)
    date = models.DateTimeField(null=False)
    address = models.CharField(max_length=1024, null=True)
    # TODO: this will be a committee name usually, in the
    # future we may want to consider committees as entities?
    name = models.CharField(max_length=1024, null=True)
    other_info = models.TextField(null=True)
    link = models.CharField(max_length=1024, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meeting'


class AgendaItem(models.Model):
    meeting = models.ForeignKey('Meeting', null=False)
    bill = models.ForeignKey('Bill', null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agenda_item'


class Search(models.Model):
    NOTIFICATION_NONE = 'none'
    NOTIFICATION_DAILY = 'daily'
    NOTIFICATION_WEEKLY = 'weekly'
    NOTIFICATION_CHOICES = ((NOTIFICATION_NONE, 'do not notify me'),
                            (NOTIFICATION_DAILY, 'notify me daily'),
                            (NOTIFICATION_WEEKLY, 'notify me weekly'))
    owner = models.ForeignKey(User)
    query_params = models.TextField()
    name = models.TextField()
    notification = models.CharField(max_length=24,
                                    choices=NOTIFICATION_CHOICES,
                                    default=NOTIFICATION_NONE)
    last_notify_date = models.DateTimeField(auto_now_add=True)
    notify_on_update = models.BooleanField(default=False, null=False)
    search_string = models.TextField(null=True)
    place = models.TextField(null=True)
    sponsor_name = models.CharField(max_length=256, null=True)
    sponsor_district = models.CharField(max_length=256, null=True)
    bill_types = models.TextField(null=True)

    def get_elasticsearch_query(self):
        bill_types = self.bill_types.split(',') if self.bill_types else None
        places = self.place.split(',') if self.place else None
        s = EsSearch()
        if self.search_string:
            s = s.query('query_string',
                        query=self.search_string,
                        fields=['number', 'title', 'text', 'summary'])
            s = s.highlight('title', fragment_size=250, number_of_fragments=1)
            s = s.highlight('text', fragment_size=250, number_of_fragments=1)
            s = s.highlight('summary', fragment_size=250, number_of_fragments=1)
        if bill_types:
            bill_type_query = Q('match', bill_type=bill_types[0])
            for bill_type in bill_types[1:]:
                bill_type_query = bill_type_query | Q('match', bill_type=bill_type)
            s = s.filter(bill_type_query)
        if places:
            place_query = Q('match', **{'legislative_body.place': places[0]})
            for place in places[1:]:
                place_query = place_query | Q('match', **{'legislative_body.place': place})
            s = s.filter(place_query)
        if self.sponsor_name:
            s = s.filter('match', {'sponsor.name': self.sponsor_name})
        if self.sponsor_district:
            s = s.filter('match', {'sponsor.district': self.sponsor_district})
        return s


    class Meta:
        db_table = 'search'






