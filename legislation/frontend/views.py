import json
import smtplib
import string
from datetime import timedelta
from email.mime.text import MIMEText
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect

from dateutil.parser import parse as parsedate

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search as EsSearch

from legislation_models.models import Bill, Search, Place
from legislation.settings import EMAIL_SERVER

ES_CONNECTION = Elasticsearch([{'host': 'localhost', 'port': '9200'}])

INDEX_PATTERN = 'bills'

# TODO: load values from config
logging.basicConfig(filename='/var/log/legislation/application.log', level=logging.DEBUG)


def _format(s):
    # This is pretty dumb. Probably do something less dumb.
    s = s.replace('<em>', 'SSSSSSSSSSSSSSSSSSS')
    s = s.replace('</em>', 'EEEEEEEEEEEEEEEEEE')
    s = s.strip(string.punctuation).strip()
    s = s.replace('SSSSSSSSSSSSSSSSSSS', '<em>')
    s = s.replace('EEEEEEEEEEEEEEEEEE', '</em>')
    return s


@login_required
def search(request):
    if request.method == 'POST':
        query = request.POST
    else:
        query = request.GET
    query = query.copy()
    if 'csrfmiddlewaretoken' in query:
        del query['csrfmiddlewaretoken']
    if request.method == 'POST':
        return redirect('/legis/search?%s' % query.urlencode())
    print(query)
    page = int(query.get('page', 0))
    search_string = query.get('search')
    place = query.getlist('place[]')
    place = ','.join(place)
    sponsor_name = query.get('sponsor_name')
    sponsor_district = query.get('sponsor_district')
    meeting_date_gt = query.get('meeting_date_gt')
    meeting_date_lt = query.get('meeting_date_lt')
    bill_types = ','.join([query.get(key) for key in query.keys() if key.startswith('bill_type')])
    s = Search(search_string=search_string,
               place=place,
               sponsor_name=sponsor_name,
               sponsor_district=sponsor_district,
               bill_types=bill_types)
    es_search = s.get_elasticsearch_query().using(ES_CONNECTION).index(INDEX_PATTERN)

    if meeting_date_gt or meeting_date_lt:
        r = {}
        if meeting_date_gt:
            r['gte'] = parsedate(meeting_date_gt)
        if meeting_date_lt:
            r['lt'] = parsedate(meeting_date_lt) + timedelta(days=1)
        es_search = es_search.filter('range', **{'meetings.time': r})
    print(es_search.to_dict())
    hits = [hit for hit in es_search[page * 10:(page+1)* 10].execute()]

    query = query.copy()
    if 'csrfmiddlewaretoken' in query:
        del query['csrfmiddlewaretoken']


    total = es_search.count()

    more_pages = total > page * 10 + 10

    highlights = [hit.meta.highlight.to_dict() if hasattr(hit.meta, 'highlight') else {} for hit in hits]
    hits = [hit.to_dict() for hit in hits]
    for hit, highlight in zip(hits, highlights):
        if highlight.get('summary'):
            hit['highlight'] = '...%s...' % _format(highlight['summary'][0])
        elif highlight.get('text'):
            hit['highlight'] = '...%s...' % _format(highlight['text'][0])
        elif highlight.get('title'):
            hit['highlight'] = '...%s...' % _format(highlight['title'][0])
        elif hit['summary']:
            hit['highlight'] = '%s...' % _format(hit['summary'][0:250])
        elif hit['text']:
            hit['highlight'] = '%s...' % _format(hit['text'][0:250])
        elif hit['title']:
            hit['highlight'] = '%s...' % _format(hit['title'][0:250])
        else:
            hit['highlight'] = ''

    return render(request, 'frontend/search_results.html', {
        'hits': hits,
        'query': query.urlencode(),
        'page': page,
        'more_pages': more_pages,
        'start_index': page * 10 + 1,
        'end_index': page * 10 + 10,
        'total': total
    })


@login_required
def save_search(request):
    query = request.GET
    name = query.get('name')
    search_string = query.get('search')
    place = query.get('place')
    sponsor_name = query.get('sponsor_name')
    sponsor_district = query.get('sponsor_district')
    bill_types = ','.join([query.get(key) for key in query.keys() if key.startswith('bill_type')])
    query = request.GET.copy()
    if 'meeting_date_gt' in query:
        del query['meeting_date_gt']
    if 'meeting_date_lt' in query:
        del query['meeting_date_lt']
    # TODO: check bill_type saving actually works correctly
    query = query.copy()
    del query['name']
    s = Search(search_string=search_string,
               place=place,
               sponsor_name=sponsor_name,
               sponsor_district=sponsor_district,
               bill_types=bill_types,
               name=name,
               query_params=query.urlencode(),
               owner=request.user)
    s.save()
    return redirect('/legis/saved-searches')

@login_required
def searches(request):
    searches = {str(search.id): search for search in Search.objects.filter(owner=request.user)}
    if request.method == 'POST':
        notify_updates = []
        for key, value in request.POST.items():
            if key.startswith('notification-search'):
                search = searches.get(key.replace('notification-search-', ''))
                if search is not None and search.notification != value:
                    search.notification = value
                    search.save()
            if key.startswith('delete'):
                search_id = key.replace('delete-', '')
                search = searches.get(search_id)
                search.delete()
                del searches[search_id]
            if key.startswith('notify-updates'):
                notify_updates.append(key.replace('notify-updates-', ''))
        for key, search in searches.items():
            if key in notify_updates and not search.notify_on_update:
                search.notify_on_update = True
                search.save()
            elif search.notify_on_update:
                search.notify_on_update = False
                search.save()

    return render(request, 'frontend/searches.html', {
        'searches': searches.values(),
        'notification_options': Search.NOTIFICATION_CHOICES,
        'save_success': request.method == 'POST'
    })

@login_required
def home(request):
    bill_types = [bill.bill_type if bill.bill_type is not None else 'Other/Missing' for bill in Bill.objects.distinct('bill_type')]
    places_json = json.dumps([place.name for place in Place.objects.all()])
    return render(request, 'frontend/index.html', {'bill_types': bill_types, 'places_json': places_json})

@login_required
def contact(request):
    done = False
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            email = ''
        comment = request.POST.get('comment')
        subject = 'Athena feedback from %s' % request.user.username
        msg_text = 'From: %s\n\nComment:\n\n%s' % (email, comment)
        logging.debug('Sending message (%s): %s' % (email, msg_text))
        msg = MIMEText(msg_text)
        msg['Subject'] = subject
        msg['From'] = 'athena@zolnetwork.com'
        msg['To'] = 'shockley@dshockley.com'
        s = smtplib.SMTP(EMAIL_SERVER)
        s.send_message(msg)
        s.quit()
        done = True
    return render(request, 'frontend/contact.html', {'done': done})

@login_required
def bill(request, bill_id):
    s = EsSearch(using=ES_CONNECTION, index=INDEX_PATTERN).query('match', id=bill_id)
    hits = [hit for hit in s[0:1].execute()]
    hit = hits[0]
    hit.text = '<p>%s</p>' % '</p><p>'.join(hit.text.split('\n\n') if hit.text else '')
    return render(request, 'frontend/bill.html', {'bill': hit})