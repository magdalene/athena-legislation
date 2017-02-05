import smtplib
from email.mime.text import MIMEText

from datetime import datetime

from elasticsearch import Elasticsearch

INDEX = 'bills'

from legislation.settings import EMAIL_SERVER
from legislation_models.models import Search

es = Elasticsearch('localhost:9200')

def send_notification(search_name, updates, to_address, hits, total):
    subject = 'New Legislation - %s' % search_name
    msg_lines = ['New%s legislation for your saved search %s (showing %s/%s)' %
                 ('/updated' if updates else '', search_name, len(hits), total)]
    for hit in hits:
        msg_lines.append(
            '<a href="https://godsigma.zolnetwork.com/legis/bill/%(bill_id)s">%(number)s - %(summary)s</a>' % {
                'bill_id': hit.id,
                'number': hit.number,
                'summary': hit.summary
            })
    msg_text = '\n\n'.join(msg_lines)
    msg = MIMEText(msg_text)
    msg['Subject'] = subject
    msg['From'] = 'athena@zolnetwork.com'
    msg['To'] = to_address

    s = smtplib.SMTP(EMAIL_SERVER)
    s.send_message(msg)
    s.quit()


def _send_notifications(notification_period):
    now = datetime.now()
    saved_searches = Search.objects.filter(notification=notification_period)
    for saved_search in saved_searches:
        es_search = saved_search.get_elasticsearch_query().using(es).index(INDEX)
        if saved_search.notify_on_update:
            range_field = 'modified_date'
        else:
            range_field = 'index_date'
        es_search = es_search.query('range', **{range_field: {'gte': saved_search.last_notify_date}})
        total = es_search.count()
        send_notification(saved_search.name,
                          saved_search.notify_on_update,
                          saved_search.owner.email,
                          es_search.size(10),
                          total)
        saved_search.last_notify_date = now
        saved_search.save()


def send_daily_notifications():
    _send_notifications(Search.NOTIFICATION_DAILY)


def send_weekly_notifications():
    _send_notifications(Search.NOTIFICATION_WEEKLY)


if __name__ == '__main__':
    send_daily_notifications()
    send_weekly_notifications()