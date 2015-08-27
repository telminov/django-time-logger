# coding: utf-8

# coding: utf-8

from django.core.management.base import BaseCommand
from django.db import connection

from time_logger.mysql_slow_logs_parser_from_file import MysqlSlowQueriesParser
from time_logger import mongo_models

class Command(BaseCommand):
    help = 'Improt mysql slow query log from mysql to mongodb'

    def add_arguments(self, parser):
        parser.add_argument('log_path')

    def handle(self, *args, **options):
        logs = mongo_models.MysqlSlowQueriesTimeLog.objects.all()
        latest_start_time = None
        if logs:
            latest_start_time = logs.latest('start_time').start_time
        cursor = connection.cursor()
        cursor.excute("use mysql")

        query = "SELECT * FROM slow_log"
        if latest_start_time:
            query += " WHERE start_time > %s" % latest_start_time.iso_format()
        cursor.excute(query)
        fields = map(lambda x: x[0], cursor.description)
        result = [dict(zip(fields, row)) for row in cursor.fetchall()]

        # write results into mongo
        for r in result:
            mongo_models.MysqlSlowQueriesTimeLog.objects.create(**r)
