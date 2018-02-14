import logging

from django.conf import settings

from raven import Client
from celery import signature

from omaha_server.utils import add_extra_to_log_message


class BaseSender(object):
    name = None
    client = None

    def send(self, message, extra={}, tags={}, sentry_data={}, crash_obj=None):
        pass


class SentrySender(BaseSender):
    name="Sentry"

    def __init__(self):
        self.client = Client(
            getattr(settings, 'RAVEN_DSN_STACKTRACE', None),
            name=getattr(settings, 'HOST_NAME', None),
            release=getattr(settings, 'APP_VERSION', None)
        )

    def send(self, message, extra={}, tags={}, sentry_data={}, crash_obj=None):
        event_id = self.client.capture(
            'raven.events.Message',
            message=message,
            extra=extra,
            tags=tags,
            data=data
        )
        signature("tasks.get_sentry_link", args=(crash_obj.pk, event_id)).apply_async(queue='private', countdown=1)


class ELKSender(BaseSender):
    name="ELK"
    handler = None

    def send(self, message, extra={}, tags={}, sentry_data={}, crash_obj=None):
            logger = logging.getLogger('crashes')

            extra.update(tags)
            extra['app_version'] = tags['ver'] if 'ver' in tags else 'unknown'

            # We don't want "sentry.interfaces" or other sentry specific things as part of any field name.
            extra['exception'] = str(sentry_data.get('sentry.interfaces.Exception'))
            extra['user'] = sentry_data.get('sentry.interfaces.User') # will be 'None' if no user in sentry_data.
            # User is passed in as "dict(id=crash.userid)". Unpack.
            if type(extra['user']) is dict: 
                extra['user'] = extra['user'].get('id')

            # The "message" is actually a crash signature, not appropriate for the ELK "message" field.
            extra['signature'] = message
            # Include logger_name and bg_state (crash reports are always 'blue').
            extra['logger_name'] = 'omaha_server'
            extra['bg_name'] = 'blue'

            # Send message with logger.
            logger.info(add_extra_to_log_message("Received crash report", extra=extra))

senders_dict = {
    "Sentry": SentrySender,
    "ELK": ELKSender,
}


def get_sender(tracker_name=None):
    if not tracker_name:
        tracker_name = getattr(settings, 'CRASH_TRACKER', 'Sentry')
    try:
        sender_class = senders_dict[tracker_name]
    except KeyError:
        raise KeyError("Unknown tracker, use one of %s" % senders_dict.keys())
    return sender_class()