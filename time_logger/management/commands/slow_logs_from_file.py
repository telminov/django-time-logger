# coding: utf-8
import datetime

from django.core.management.base import BaseCommand
from time_logger.mysql_logs_parser_from_file import MysqlSlowQueriesParser
from time_logger import models_mongo


class Command(BaseCommand):
    help = 'Improt mysql slow query log from file to mongodb'

    def add_arguments(self, parser):
        parser.add_argument('--log_path')

    def handle(self, *args, **options):
        for entry in MysqlSlowQueriesParser(options['log_path']):
            data = {
                'start_time': entry['start_time'],
                'end_time': entry['start_time'] - datetime.timedelta(seconds=entry['query_time']),
                'user_host': u'%s@%s' % (entry['user'], entry['host']),
                'query_time': entry['query_time'],
                'lock_time': entry['lock_time'],
                'rows_sent': entry['rows_sent'],
                'sql_text': ' ;'.join(entry['queries_list']),
            }

            if not models_mongo.MysqlSlowQueriesTimeLog.objects.filter(**data).count():
                models_mongo.MysqlSlowQueriesTimeLog.objects.create(**data)
