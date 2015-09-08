# coding: utf-8

from django.core.management.base import BaseCommand
from django.db import connection

from time_logger import models_mongo


class Command(BaseCommand):
    help = 'Improt mysql slow query log from mysql to mongodb'

    def handle(self, *args, **options):
        logs = models_mongo.MysqlSlowQueriesTimeLog.objects.all()
        latest_start_time = None
        if logs:
            latest_start_time = logs.order_by('-start_time')[0].start_time
        cursor = connection.cursor()
        cursor.execute("use mysql")

        query = "SELECT * FROM slow_log"
        if latest_start_time:
            query += " WHERE start_time > '%s'" % latest_start_time.isoformat()
        cursor.execute(query)
        fields = map(lambda x: x[0], cursor.description)
        results = [dict(zip(fields, row)) for row in cursor.fetchall()]

        # write results into mongo
        for row in results:
            row['query_time'] = row['query_time'].second
            row['lock_time'] = row['lock_time'].second
            models_mongo.MysqlSlowQueriesTimeLog.objects.create(**row)
