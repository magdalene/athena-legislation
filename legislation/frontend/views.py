import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from dateutil.parser import parse as parsedate

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q

from legislation_models.models import Bill

ES_CONNECTION = Elasticsearch([{'host': 'localhost', 'port': '9200'}])

INDEX_PATTERN = 'bills'

@login_required
def search(request):
    if request.method == 'POST':
        query = request.POST
    else:
        query = request.GET
    print(query)
    page = int(query.get('page', 0))
    search_string = query.get('search')
    city = query.get('city')
    state = query.get('state')
    sponsor_name = query.get('sponsor_name')
    sponsor_district = query.get('sponsor_district')
    meeting_date_gt = query.get('meeting_date_gt')
    meeting_date_lt = query.get('meeting_date_lt')
    bill_types = [query.get(key) for key in query.keys() if key.startswith('bill_type')]
    s = Search(using=ES_CONNECTION, index=INDEX_PATTERN)
    if search_string:
        s = s.query('query_string', query=search_string, fields=['number', 'title', 'text', 'summary'])
    if bill_types:
        bill_type_query = Q('match', bill_type=bill_types[0])
        for bill_type in bill_types[1:]:
            bill_type_query = bill_type_query | Q('match', bill_type=bill_type)
        s = s.filter(bill_type_query)
    if city:
        s = s.filter('match', {'legislative_body.city': city})
    if state:
        s = s.filter('match', {'legislative_body.state': state})
    if sponsor_name:
        s = s.filter('match', {'sponsor.name': sponsor_name})
    if sponsor_district:
        s = s.filter('match', {'sponsor.district': sponsor_district})
    if meeting_date_gt or meeting_date_lt:
        r = {}
        if meeting_date_gt:
            r['gte'] = parsedate(meeting_date_gt)
        if meeting_date_lt:
            r['lt'] = parsedate(meeting_date_lt)
        s = s.filter('range', **{'meetings.time': r})
    print(s.to_dict())
    hits = [hit for hit in s[page * 10:(page+1)* 10].execute()]

    query = query.copy()
    if 'csrfmiddlewaretoken' in query:
        del query['csrfmiddlewaretoken']

    more_pages = s.count() > page * 10 + 10

    return render(request, 'frontend/search_results.html', {
        'hits': hits,
        'query': query.urlencode(),
        'page': page,
        'more_pages': more_pages
    })

@login_required
def home(request):
    bill_types = [bill.bill_type if bill.bill_type is not None else 'Other/Missing' for bill in Bill.objects.distinct('bill_type')]
    return render(request, 'frontend/index.html', {'bill_types': bill_types})

@login_required
def bill(request, bill_id):
    s = Search(using=ES_CONNECTION, index=INDEX_PATTERN).query('match', id=bill_id)
    hits = [hit for hit in s[0:1].execute()]
    hit = hits[0]
    hit.text = '<p>%s</p>' % '</p><p>'.join(hit.text.split('\n\n') if hit.text else '')
    return render(request, 'frontend/bill.html', {'bill': hit})