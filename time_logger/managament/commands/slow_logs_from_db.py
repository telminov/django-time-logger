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
        cursor = connection.cursor()
        cursor.excute("use mysql")
        cursor.excute("SELECT * FROM slow_log")
        fields = map(lambda x: x[0], cursor.description)
        result = [dict(zip(fields, row)) for row in cursor.fetchall()]

        # write results into mongo
        for r in result:
            mongo_models.MysqlSlowQueriesTimeLog.objects.create(**r)
