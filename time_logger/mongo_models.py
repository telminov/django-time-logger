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
    start_time = mongoengine.DateTimeField()
    user_host = mongoengine.StringField()
    query_time = mongoengine.IntField()
    lock_time = mongoengine.IntField()
    rows_sent = mongoengine.IntField()
    rows_examined = mongoengine.IntField()
    sql_text = mongoengine.StringField()
    db = mongoengine.StringField()
    last_insert_id = mongoengine.IntField()
    insert_id = mongoengine.IntField()
    server_id = mongoengine.IntField()

    meta = {
        'indexes': ['query_time', 'timestamp'],
        'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
    }

    # @classmethod
    # def create_entry(cls, entry):
    #     # in case we would modify entry dict
    #     entry_copy = deepcopy(entry)
    #     return cls.objects.create(**entry_copy)

# class ParsedLogs(mongoengine.Document):
#     SLOW_QUERY_TYPE = 'slow_query'
#     TYPE_CHOICES = (
#         (SLOW_QUERY_TYPE, SLOW_QUERY_TYPE),
#     )
#     type = mongoengine.StringField(choices=TYPE_CHOICES)
#     st_ino = mongoengine.StringField(verbose_name='inode number')
#     st_dev = mongoengine.IntField(unique_with='st_ino', verbose_name='id of device containing file')
#
#     meta = {
#         'indexes': [('st_ino', 'st_dev'), ],
#         'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
#     }
#
#     def get_all_not_parsed_files(self):
#         pass



