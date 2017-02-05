import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from dateutil.parser import parse as parsedate

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search as EsSearch

from legislation_models.models import Bill, Search

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
    bill_types = ','.join([query.get(key) for key in query.keys() if key.startswith('bill_type')])
    s = Search(search_string=search_string,
               city=city,
               state=state,
               sponsor_name=sponsor_name,
               sponsor_district=sponsor_district,
               bill_types=bill_types)
    es_search = s.get_elasticsearch_query().using(ES_CONNECTION).index(INDEX_PATTERN)

    if meeting_date_gt or meeting_date_lt:
        r = {}
        if meeting_date_gt:
            r['gte'] = parsedate(meeting_date_gt)
        if meeting_date_lt:
            r['lt'] = parsedate(meeting_date_lt)
        es_search = es_search.filter('range', **{'meetings.time': r})
    print(es_search.to_dict())
    hits = [hit for hit in es_search[page * 10:(page+1)* 10].execute()]

    query = query.copy()
    if 'csrfmiddlewaretoken' in query:
        del query['csrfmiddlewaretoken']

    more_pages = es_search.count() > page * 10 + 10

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
    s = EsSearch(using=ES_CONNECTION, index=INDEX_PATTERN).query('match', id=bill_id)
    hits = [hit for hit in s[0:1].execute()]
    hit = hits[0]
    hit.text = '<p>%s</p>' % '</p><p>'.join(hit.text.split('\n\n') if hit.text else '')
    return render(request, 'frontend/bill.html', {'bill': hit})