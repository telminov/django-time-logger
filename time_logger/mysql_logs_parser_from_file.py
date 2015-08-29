# coding: utf-8
import re
import datetime
import decimal

# not shure in names. So in my logs only Query and Intvar
NOT_PARSING_EVENTS = ['Xid', 'User_var', 'Rand', 'Intvar']

_DATE_PAT = r"\d{6}\s+\d{1,2}:\d{2}:\d{2}"

# SLOW LOG EXPRESSIONS
_SLOW_HEADER_VERSION = re.compile(r"(.+), Version: (\d+)\.(\d+)\.(\d+)(?:-(\S+))?")
_SLOW_HEADER_SERVER = re.compile(r"Tcp port:\s*(\d+)\s+Unix socket:\s+(.*)")

_SLOW_TIMESTAMP = re.compile(r"#\s+Time:\s+(" + _DATE_PAT + r")")
_SLOW_USERHOST = re.compile(r"#\s+User@Host:\s+"
                            r"(?:([\w\d]+))?\s*"
                            r"\[\s*([\w\d]+)\s*\]\s*"
                            r"@\s*"
                            r"([\w\d]*)\s*"
                            r"\[\s*([\d.]*)\s*\]")
_SLOW_STATS = re.compile(r"#\sQuery_time:\s(\d*\.\d{1,6})\s*"
                         r"Lock_time:\s(\d*\.\d{1,6})\s*"
                         r"Rows_sent:\s(\d*)\s*"
                         r"Rows_examined:\s(\d*)")

# BIN_LOG EXPRESSIONS
BIN_LOG_END = '# End of log file'
_BIN_LOG_DELIMITER = re.compile(r"DELIMITER\s(.+);")
_BIN_LOG_QUERY_STATS = re.compile(r"#(" + _DATE_PAT + ")\s+"
                            r"server\s+id\s+(\d+)\s+"
                            r"end_log_pos\s+(\d+)\s+"
                            r"Query\s+thread_id=(\d+)\s+"
                            r"exec_time=(\d+)\s+"
                            r"error_code=(\d+)")
_BIN_LOG_DB = re.compile(r"use `(.+)`")
_BING_LOG_TIMESTAMP = re.compile(r"SET TIMESTAMP=(\d+)")

class LogParserError(Exception):
    pass


class BaseLogParser(object):
    def __iter__(self):
        return self

    def next(self):
        entry = self._parse_entry()
        if entry is None:
            raise StopIteration
        return entry

    def _get_next_line(self):
        line = self._stream.readline()
        if not line:
            return None

        delimiter = getattr(self, 'delimiter', '')

        return line.rstrip('%s\r\n' % delimiter)

    @staticmethod
    def _parse_line(regex, line):
        info = regex.match(line)
        if info is None:
            raise LogParserError('Failed parsing line: %s' %
                                 line[:30])
        return info.groups()

    def _parse_headers(self, line):
        raise NotImplementedError()

    def _parse_entry(self):
        raise NotImplementedError()


class MysqlBinLogParser(BaseLogParser):
    def __init__(self, log_path):
        # TODO обкатать парсер на одном файле, затем натравливать только на новые логи
        self._stream = open(log_path, 'r')

        # line which contains query info about new expression
        self._cached_line = None

        line = self._get_next_line()
        if line is not None:
            self._parse_headers(line)

    def _parse_headers(self, line):
        while line and not line.startswith('DELIMITER'):
            line = self._get_next_line()
        self.delimiter = self._parse_line(_BIN_LOG_DELIMITER, line)[0]

        # skip some header info and session
        while not 'BEGIN' in line:
            line = self._get_next_line()
        # get first Query
        while not 'Query' in line:
            line = self._get_next_line()
        self._cached_line = line

    def _parse_entry(self):
        # this line must contains Query stats
        if self._cached_line:
            line = self._cached_line
        else:
            line = self._get_next_line()

        start_time, server_id, end_log_pos, thread_id, exec_time, error_code =\
            self._parse_line(_BIN_LOG_QUERY_STATS, line)

        # str: db
        line = self._get_next_line()
        db = None
        if line.startswith('use'):
            db = self._parse_line(_BIN_LOG_DB, line)[0]
            line = self._get_next_line()

        # str: timestamp
        timestamp = self._parse_line(_BING_LOG_TIMESTAMP, line)[0]

        # str: query
        line = self._get_next_line()
        query_type = line.split(' ')[0]
        query = line

        # skip line to another Query command
        while not 'Query' in line:
            line = self._get_next_line()
            if line == BIN_LOG_END:
                return None
        # cached new query info line
        self._cached_line = line

        return {
            'start_time': start_time,
            'server_id': server_id,
            'end_log_pos': end_log_pos,
            'thread_id': thread_id,
            'exec_time': exec_time,
            'error_code': error_code,
            'db': db,
            'timestamp': timestamp,
            'query': query,
            'query_type': query_type,

        }


class MysqlSlowQueriesParser(BaseLogParser):
    def __init__(self, log_path):
        self._stream = open(log_path, 'r')

        line = self._get_next_line()
        if line is not None and line.endswith('started with:'):
            self._parse_headers(line)

    def _parse_headers(self, line):
        # header strings:
        #   1 run command and version
        #   2 connection info
        #   3 headers
        # we do not need in all this stuff
        self._get_next_line()
        self._get_next_line()
        line = self._get_next_line()
        return line

    def _parse_entry(self):
        entry = {}
        line = self._get_next_line()
        if not line:
            return None
        if line.startswith('# Time:'):
                timestamp = self._parse_time(line)
                entry['start_time'] = timestamp
                line = self._get_next_line()

        if line.startswith('# User@Host:'):
            private_user, unprivate_user, host, ip = self._parse_connection_info(line)
            entry['user'] = private_user if private_user else unprivate_user
            entry['host'] = host if host else ip
            line = self._get_next_line()

        if line.startswith('# Query_time:'):
            query_time, lock_time, rows_sent, rows_examined = self._parse_statistics(line)
            entry['query_time'] = decimal.Decimal(query_time)
            entry['lock_time'] = decimal.Decimal(lock_time)
            entry['rows_sent'] = int(rows_sent)
            entry['rows_examined'] = int(rows_examined)
            line = self._get_next_line()

        queries = self._parse_queries(line)
        entry['queries_list'] = queries

        return entry

    def _parse_time(self, line):
        info = self._parse_line(_SLOW_TIMESTAMP, line)
        return datetime.datetime.strptime(info[0], "%y%m%d %H:%M:%S")

    def _parse_connection_info(self, line):
        try:
            info = self._parse_line(_SLOW_USERHOST, line)
        except:
            info = ('', '', '', '0.0.0.0')
        return info

    def _parse_statistics(self, line):
        return self._parse_line(_SLOW_STATS, line)

    def _parse_queries(self, line):
        query_string = []
        while line:
            if line.startswith('# Time:'):
                break
            query_string.append(line)
            line = self._get_next_line()
        return query_string

# usage example
# if __name__ == '__main__':
#     cnt = 0
#     for log in MysqlBinLogParser('bin_logs.sql'):
#         cnt += 1
#     print cnt
