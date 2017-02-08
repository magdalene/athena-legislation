import os
from copy import deepcopy
from datetime import datetime

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legislation.settings")
django.setup()
from legislation_models.models import Bill, Place, City, State

from elasticsearch import Elasticsearch, helpers

ES_HOST = 'localhost'
ES_PORT = '9200'

INDEX_NAME = 'bills'

DOC_TYPE = 'bill'

INDEX_MAPPING = {
    DOC_TYPE: {
        'properties': {
            'id': {'type': 'integer'},
            'index_date': {'type': 'date'},
            'modified_date': {'type': 'date'},
            'number': {'type': 'string', 'index': 'not_analyzed'},
            'legislative_body': {
                'properties': {
                    'name': {'type': 'text', 'analyzer': 'english'},
                    'city': {'type': 'string'},
                    'state': {'type': 'string'},
                    'place': {'type': 'string', 'index': 'not_analyzed'}
                },
            },
            'sponsors': {
                'properties': {
                    'name': {'type': 'text', 'analyzer': 'english'},
                    'district': {'type': 'string'},
                    'sponsor_type': {'type': 'string', 'index': 'not_analyzed'},
                    'link': {'type': 'string', 'index': 'not_analyzed'}
                }
            },
            'bill_type': {'type': 'string', 'index': 'not_analyzed'},
            'title': {'type': 'text', 'analyzer': 'english'},
            'text': {'type': 'text', 'analyzer': 'english'},
            'summary': {'type': 'text', 'analyzer': 'english'},
            'link': {'type': 'string', 'index': 'not_analyzed'},
            'meetings': {
                'properties': {
                    'time': {'type': 'date'},
                    'address': {'type': 'text', 'analyzer': 'english'},
                    'name': {'type': 'text', 'analyzer': 'english'},
                    'link': {'type': 'string', 'index': 'not_analyzed'}
                }
            }
        }
    }
}

INDEX_SETTINGS = {
    "settings": {
        "analyzer": {
            "my_english": {
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "porter_stem"
                ]
            }
        }
    }
}

ES_CONNECTION = Elasticsearch([{'host': ES_HOST, 'port': ES_PORT}])


def index_actions():
    bills = Bill.objects.filter(status=Bill.STATUS_UP_TO_DATE)
    for bill in bills:
        city = None
        cities = City.objects.filter(place=bill.legislative_body.place)
        if len(cities):
            city = cities[0]
            state = city.state
            place_name = city.place.name
        else:
            state = State.objects.get(place=bill.legislative_body.place)
            place_name = state.place.name
        doc = {
            'id': bill.id,
            'modified_date': datetime.now(),
            'number': bill.number,
            'bill_type': bill.bill_type if bill.bill_type else 'Other/Missing',
            'title': bill.title,
            'text': bill.text,
            'summary': bill.summary,
            'link': bill.link,
            'legislative_body': {
                'name': bill.legislative_body.name,
                'city': city.place.name if city else None,
                'place': place_name,
                'state': state.place.name
            },
            'sponsors': [{
                             'name': '%s %s' % (sponsor.legislator.first_name,
                                                sponsor.legislator.last_name) if sponsor.legislator else sponsor.name_string,
                             'district': sponsor.legislator.district if sponsor.legislator else None,
                             'sponsor_type': sponsor.sponsor_type,
                             'link': sponsor.legislator.link if sponsor.legislator else None
                         } for sponsor in bill.sponsor_set.all()],
            'meetings': [{
                             'time': agenda_item.meeting.date,
                             'address': agenda_item.meeting.address,
                             'name': agenda_item.meeting.name,
                             'link': agenda_item.meeting.link
                         } for agenda_item in bill.agendaitem_set.all()]
        }
        upsert = deepcopy(doc)
        upsert['index_date'] = datetime.now()

        yield {
            '_op_type': 'update',
            '_id': bill.id,
            '_index': INDEX_NAME,
            '_type': DOC_TYPE,
            'doc': doc,
            'upsert': upsert
        }


def create_index_if_missing():
    if ES_CONNECTION.indices.exists(INDEX_NAME):
        return
    ES_CONNECTION.indices.create(INDEX_NAME, body={
        'mappings': INDEX_MAPPING,
    })


def index():
    results = helpers.bulk(ES_CONNECTION, index_actions(), stats_only=True)
    return results


if __name__ == '__main__':
    create_index_if_missing()
    print(index())
