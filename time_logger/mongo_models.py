# coding: utf-8
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