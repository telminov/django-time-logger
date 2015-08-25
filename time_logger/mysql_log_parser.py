# coding: utf-8
import re
import datetime
import decimal

_DATE_PAT = r"\d{6}\s+\d{1,2}:\d{2}:\d{2}"
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


class LogParserError(Exception):
    pass


class MysqlSlowQueriesParser(object):
    def __init__(self, log_path):
        self.log_path = log_path

    @staticmethod
    def _parse_line(regex, line):
        """Parses a log line using given regular expression
        regex[in]   a SRE_Match-object
        line[in]    a string
        This function takes a log line and matches the regular expresion given
        with the regex argument. It returns the result of
        re.MatchObject.groups(), which is a tuple.
        Raises LogParserError on errors.
        Returns a tuple.
        """
        info = regex.match(line)
        if info is None:
            raise LogParserError('Failed parsing Slow Query line: %s' %
                                 line[:30])
        return info.groups()

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

    def parse(self):
        with open(self.log_path) as f:
            all_queries = []
            query_info = {}
            for line in f.readlines():
                if line.startswith('# Time:'):
                    timestamp = self._parse_time(line)
                    query_info = {'time': timestamp}
                    all_queries.append(query_info)

                elif line.startswith('# User@Host:'):
                    private_user, unprivate_user, host, ip = self._parse_connection_info(line)
                    query_info['user'] = private_user if private_user else unprivate_user
                    query_info['host'] = host if host else ip

                elif line.startswith('# Query_time:'):
                    query_time, lock_time, rows_sent, rows_examined = self._parse_statistics(line)
                    query_info['query_time'] = decimal.Decimal(query_time)
                    query_info['lock_time'] = decimal.Decimal(lock_time)
                    query_info['rows_sent'] = int(rows_sent)
                    query_info['rows_examined'] = int(rows_examined)
                else:
                    if 'time' in query_info:
                        query_info.setdefault('query_string', []).append(line)
            return all_queries
