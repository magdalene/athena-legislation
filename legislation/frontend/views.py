import json

from django.http import JsonResponse
from django.shortcuts import render

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

ES_CONNECTION = Elasticsearch([{'host': 'localhost', 'port': '9200'}])

INDEX_PATTERN = 'bills'


def search(request, page=0):
    search_string = request.POST.get('search')
    bill_type = request.POST.get('bill_type')
    city = request.POST.get('city')
    state = request.POST.get('state')
    sponsor_name = request.POST.get('sponsor_name')
    sponsor_district = request.POST.get('sponsor_district')
    meeting_date_gt = request.POST.get('meeting_date_gt')
    meeting_date_lt = request.POST.get('meeting_date_lt')
    s = Search(using=ES_CONNECTION, index=INDEX_PATTERN)
    if search_string:
        s = s.query('query_string', query=search_string, fields=['number', 'title', 'text', 'summary'])
    if bill_type:
        s = s.filter('match', bill_type=bill_type)
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
            r['gte'] = meeting_date_gt
        if meeting_date_lt:
            r['lt'] = meeting_date_lt
        s = s.filter('range', {'meetings.time': r})
    hits = [hit for hit in s[page * 10:(page+1)* 10].execute()]
    return render(request, 'frontend/search_results.html', {'hits': [hit.to_dict() for hit in hits]})


def home(request):
    return render(request, 'frontend/index.html', {})


def bill(request, bill_id):
    s = Search(using=ES_CONNECTION, index=INDEX_PATTERN).query('match', id=bill_id)
    hits = [hit for hit in s[0:1].execute()]
    hit = hits[0]
    hit.text = '<p>%s</p>' % '</p><p>'.join(hit.text.split('\n\n'))
    return render(request, 'frontend/bill.html', {'bill': hit})