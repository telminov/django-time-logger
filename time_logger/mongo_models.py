# coding: utf-8
from copy import deepcopy
import datetime
import mongoengine
from django.conf import settings

class ViewTimeLog(mongoengine.Document):
    duration = mongoengine.IntField(help_text='View process duration in seconds')
    view_func_path = mongoengine.StringField()
    view_args = mongoengine.ListField()
    view_kwargs = mongoengine.DictField()
    username = mongoengine.StringField()
    request_get = mongoengine.DictField()
    request_post = mongoengine.DictField()
    dc = mongoengine.DateTimeField()

    meta = {
        'indexes': ['-duration', 'dc'],
        'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
    }

    def save(self, *args, **kwargs):
        if not self.dc:
            self.dc = datetime.datetime.now()
        return super(ViewTimeLog, self).save(*args, **kwargs)


class MysqlSlowQueriesTimeLog(mongoengine.Document):
    timestamp = mongoengine.DateTimeField()
    username = mongoengine.StringField()
    query_time = mongoengine.IntField()
    lock_time = mongoengine.IntField()
    rows_sent = mongoengine.IntField()
    rows_examined = mongoengine.IntField()
    queries = mongoengine.IntField()

    meta = {
        'indexes': ['query_time', 'timestamp'],
        'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
    }

    @classmethod
    def create_entry(cls, entry):
        # in case we would modify entry dict
        entry_copy = deepcopy(entry)
        return cls.objects.create(**entry_copy)


