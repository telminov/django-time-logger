# # coding: utf-8
import os
import datetime

from django.core.management.base import BaseCommand
import subprocess
from time_logger.mysql_logs_parser_from_file import MysqlBinLogParser
from time_logger import models_mongo

PATH_TO_BINLOGS = '/var/log/mysql/'
PATH_TO_READABLE_BINLOGS = '/tmp/binlogs/'


class Command(BaseCommand):
    help = 'Remove old logs from MysqlBinLogTimeLog, MysqlSlowQueriesTimeLog, ViewTimeLog'

    def add_arguments(self, parser):
        parser.add_argument('--expire_day', required=True, help='Day after which remove logs')

    def handle(self, *args, **options):
        expire_day = int(options.get('expire_day'))
        expire_date = datetime.datetime.now() - datetime.timedelta(days=expire_day)

        models_mongo.MysqlBinLogTimeLog.objects.filter(start_time__lt=expire_date).delete()
        models_mongo.MysqlSlowQueriesTimeLog.objects.filter(start_time__lt=expire_date).delete()
        models_mongo.ViewTimeLog.objects.filter(dc__lt=expire_date).delete()
