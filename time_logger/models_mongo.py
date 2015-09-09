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

    def get_end_time(self):
        return self.dc + datetime.timedelta(seconds=self.duration)

    def get_parallel_slow_queries(self):
        start_dt = self.dc
        end_dt = self.get_end_time()
        slow_queries = MysqlSlowQueriesTimeLog.objects.filter(
            start_time__gte=start_dt,
            start_time__lte=end_dt,
        )
        return slow_queries

    def get_parallel_modify_queries(self):
        start_dt = self.dc
        end_dt = self.get_end_time()
        modify_queries = MysqlBinLogTimeLog.objects.filter(
            start_time__gte=start_dt,
            start_time__lte=end_dt,
        )
        return modify_queries

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
        'indexes': ['query_time', 'start_time'],
        'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
    }


class MysqlBinLogTimeLog(mongoengine.Document):
    UPDATE_QUERY_TYPE = 'UPDATE'
    DELETE_QUERY_TYPE = 'DELETE'
    INSERT_QUERY_TYPE = 'INSERT'
    INSERT_INTO_QUERY_TYPE = 'INSERT_INTO'
    SET_QUERY_TYPE = 'SET'
    QUERY_TYPE_CHOICES = (
        (UPDATE_QUERY_TYPE, UPDATE_QUERY_TYPE),
        (DELETE_QUERY_TYPE, DELETE_QUERY_TYPE),
        (INSERT_QUERY_TYPE, INSERT_QUERY_TYPE),
        (INSERT_INTO_QUERY_TYPE, INSERT_INTO_QUERY_TYPE),
        (SET_QUERY_TYPE, SET_QUERY_TYPE),
    )

    LOGGED_QUERY_TYPES = [
        UPDATE_QUERY_TYPE,
        DELETE_QUERY_TYPE,
        INSERT_INTO_QUERY_TYPE,
        INSERT_QUERY_TYPE
    ]

    start_time = mongoengine.DateTimeField()
    exec_time = mongoengine.IntField()
    timestamp = mongoengine.DateTimeField()
    error_code = mongoengine.IntField()
    query = mongoengine.StringField()
    query_type = mongoengine.StringField(choices=QUERY_TYPE_CHOICES)

    meta = {
        'indexes': ['exec_time', 'query_type'],
        'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
    }

class ParsedLogsFiles(mongoengine.Document):
    file_name = mongoengine.StringField(verbose_name='file_name')

    meta = {
        'indexes': ['file_name', ],
        'db_alias': getattr(settings, 'LOG_VIEW_TIME_DB_ALIAS', 'default')
    }

    def get_all_not_parsed_files(self):
        pass
