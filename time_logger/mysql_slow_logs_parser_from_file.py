# coding: utf-8
import re
import datetime
import decimal

_DATE_PAT = r"\d{6}\s+\d{1,2}:\d{2}:\d{2}"

_HEADER_VERSION = re.compile(r"(.+), Version: (\d+)\.(\d+)\.(\d+)(?:-(\S+))?")
_HEADER_SERVER = re.compile(r"Tcp port:\s*(\d+)\s+Unix socket:\s+(.*)")

_TIMESTAMP = re.compile(r"#\s+Time:\s+(" + _DATE_PAT + r")")
_USERHOST = re.compile(r"#\s+User@Host:\s+"
                            r"(?:([\w\d]+))?\s*"
                            r"\[\s*([\w\d]+)\s*\]\s*"
                            r"@\s*"
                            r"([\w\d]*)\s*"
                            r"\[\s*([\d.]*)\s*\]")
_STATS = re.compile(r"#\sQuery_time:\s(\d*\.\d{1,6})\s*"
                         r"Lock_time:\s(\d*\.\d{1,6})\s*"
                         r"Rows_sent:\s(\d*)\s*"
                         r"Rows_examined:\s(\d*)")


class LogParserError(Exception):
    pass


class MysqlSlowQueriesParser(object):
    def __init__(self, log_path):
        self._stream = open(log_path, 'r')

        line = self._get_next_line()
        if line is not None and line.endswith('started with:'):
            self._parse_headers()

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
        return line.rstrip('\r\n')

    def _parse_headers(self):
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

    @staticmethod
    def _parse_line(regex, line):
        info = regex.match(line)
        if info is None:
            raise LogParserError('Failed parsing Slow Query line: %s' %
                                 line[:30])
        return info.groups()

    def _parse_time(self, line):
        info = self._parse_line(_TIMESTAMP, line)
        return datetime.datetime.strptime(info[0], "%y%m%d %H:%M:%S")

    def _parse_connection_info(self, line):
        try:
            info = self._parse_line(_USERHOST, line)
        except:
            info = ('', '', '', '0.0.0.0')
        return info

    def _parse_statistics(self, line):
        return self._parse_line(_STATS, line)

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
#     for log in MysqlSlowQueriesParser('mysql-slow.log.1'):
#         print log