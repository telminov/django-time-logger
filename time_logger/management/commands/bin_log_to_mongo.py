# coding: utf-8

from django.core.management.base import BaseCommand
from time_logger.mysql_logs_parser_from_file import MysqlBinLogParser
from time_logger import mongo_models

class Command(BaseCommand):
    help = 'Import mysql binlog from file to mongodb'

    def add_arguments(self, parser):
        parser.add_argument('log_path')

    def handle(self, *args, **options):
        for entry in MysqlBinLogParser(options['log_path']):
            if entry['query_type'] in mongo_models.MysqlBinLogTimeLog.LOGGED_QUERY_TYPES:
                # remove not interested stats
                del entry['server_id']
                del entry['end_log_pos']
                del entry['thread_id']
                del entry['db']
                mongo_models.MysqlBinLogTimeLog.objects.create(**entry)
