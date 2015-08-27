# coding: utf-8

from django.core.management.base import BaseCommand, CommandError
from time_logger.mysql_log_parser import MysqlSlowQueriesParser
from time_logger import mongo_models
class Command(BaseCommand):
    help = 'Improt mysql slow query log to mongodb'

    def add_arguments(self, parser):
        parser.add_argument('log_path', required=False)

    def handle(self, *args, **options):
        log_path = 'mysql-slow.log.1'
        if options['log_path']:
            log_path = options['log_path']

        for entry in MysqlSlowQueriesParser(log_path):
            mongo_models.MysqlSlowQueriesTimeLog.create_entry(entry)