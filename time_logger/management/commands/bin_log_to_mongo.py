# coding: utf-8
import os
import datetime

from django.core.management.base import BaseCommand
import subprocess
from time_logger.mysql_logs_parser_from_file import MysqlBinLogParser
from time_logger import models_mongo

PATH_TO_BINLOGS = '/var/log/mysql/'
PATH_TO_READABLE_BINLOGS = '/tmp/binlogs/'


class Command(BaseCommand):
    help = 'Import mysql binlog from file to mongodb'

    def add_arguments(self, parser):
        parser.add_argument('--log_path', default=None)

    def handle(self, *args, **options):
        parsed_log_names = models_mongo.ParsedLogsFiles.objects.values_list('file_name')

        log_path = options.get('log_path')
        if log_path:
            file_name = log_path.split('/')[-1]
            if file_name in parsed_log_names:
                raise Exception('file already parsed')

            new_binlog_file_paths = _create_readable_binlog([file_name, ])

        else:
            new_binlog_file_names = [
                name for name in os.listdir(PATH_TO_BINLOGS)
                if name not in parsed_log_names and name.startswith('mysql-bin') and name != 'mysql-bin.index'
                ]

            # cutoff last log. Mysql writes binlogs in it
            new_binlog_file_names = sorted(new_binlog_file_names)[:-1]

            new_binlog_file_paths = _create_readable_binlog(new_binlog_file_names)

        for log_path in new_binlog_file_paths:
            for entry in MysqlBinLogParser(log_path):
                if entry['query_type'] in models_mongo.MysqlBinLogTimeLog.LOGGED_QUERY_TYPES:
                    # remove not interested stats
                    del entry['server_id']
                    del entry['end_log_pos']
                    del entry['thread_id']
                    del entry['db']

                    entry['end_time'] = entry['start_time'] + datetime.timedelta(seconds=entry['exec_time'])
                    models_mongo.MysqlBinLogTimeLog.objects.create(**entry)
            models_mongo.ParsedLogsFiles.objects.create(file_name=log_path.split('/')[-1])

            # remove parsed_log
            os.remove(log_path)


def _create_readable_binlog(new_binlog_file_names):
    new_binlog_file_paths = []

    # create dir for readable logs
    if not os.path.exists(PATH_TO_READABLE_BINLOGS):
        os.mkdir(PATH_TO_READABLE_BINLOGS)
    # make binlogs readable
    for file_name in new_binlog_file_names:
        # command mysqlbinlog --verbose --base64-output=NEVER  mysql-bin.002491 > bin_logs.sql
        subprocess.call('mysqlbinlog --verbose %s%s > %s%s' %
                        (PATH_TO_BINLOGS, file_name, PATH_TO_READABLE_BINLOGS, file_name), shell=True)

        new_binlog_file_paths.append('%s%s' % (PATH_TO_READABLE_BINLOGS, file_name))
    return new_binlog_file_paths
