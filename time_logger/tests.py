import mock
from mock import sentinel
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from djutils.testrunner import TearDownTestCaseMixin
from django.test import TestCase
from django.test.client import RequestFactory
from mysql_logs_parser_from_file import BaseLogParser, LogParserError, MysqlBinLogParser, BIN_LOG_END, _BIN_LOG_DB, \
    _BIN_LOG_QUERY_STATS, _BING_LOG_TIMESTAMP, MysqlSlowQueriesParser, _SLOW_TIMESTAMP, _SLOW_USERHOST, _SLOW_STATS
import models_mongo
from middleware.view_logger import ViewTimeLogger as ViewTimeLoggerMiddleware
import views


class ViewsLogTestCase(TestCase):
    def setUp(self):
        self.url = '/views_log/'

    def generate_data(self):
        models_mongo.ViewTimeLog.objects.create(
            duration=2,
            view_func_path='time_logger.views.test_view',
            view_args=[1, 2, 3],
            view_kwargs={'a': 1, 'b': 2, 'c': 3},
            username='tester',
            request_get={'q': 'test query'},
            request_post={},
        )

    def test_without_params(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_filter_duration(self):
        self.generate_data()

        params = {'min_duration': 1}
        self._assert_exists(params)

        params['min_duration'] = 3
        self._assert_not_exists(params)

    def test_filter_view_func_path(self):
        self.generate_data()
        log = models_mongo.ViewTimeLog.objects.all()[0]

        params = {'view_func_path': log.view_func_path}
        self._assert_exists(params)

        params['view_func_path'] += '123'
        self._assert_not_exists(params)

    def test_filter_dc(self):
        self.generate_data()
        log = models_mongo.ViewTimeLog.objects.all()[0]

        dc_iso = log.dc.isoformat(sep=' ')[:19]
        params = {'min_dc': dc_iso, 'max_dc': dc_iso}
        self._assert_exists(params)

        dc_iso = (log.dc + datetime.timedelta(days=1)).isoformat(sep=' ')[:19]
        params = {'min_dc': dc_iso, 'max_dc': dc_iso}
        self._assert_not_exists(params)

    def _assert_exists(self, params):
        response = self.client.get(self.url, params)
        self.assertTrue(
            len(response.context['page_obj'].object_list)
        )

    def _assert_not_exists(self, params):
        response = self.client.get(self.url, params)
        self.assertFalse(
            len(response.context['page_obj'].object_list)
        )


class ViewsLogDetail(TestCase):
    def test_page(self):
        log = models_mongo.ViewTimeLog.objects.create(
            duration=2,
            view_func_path='time_logger.views.test_view',
            view_args=[1, 2, 3],
            view_kwargs={'a': 1, 'b': 2, 'c': 3},
            username='tester',
            request_get={'q': 'test query'},
            request_post={},
        )

        response = self.client.get('/views_log/%s/' % log.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], log)


class SlowQueriesLogTestCase(TestCase):
    def setUp(self):
        self.url = '/slow_queries_log/'

    def generate_data(self):
        now = datetime.datetime.now()
        start_time = now - datetime.timedelta(seconds=30)
        end_time = now + datetime.timedelta(seconds=10)
        log1 = models_mongo.MysqlSlowQueriesTimeLog.objects.create(
            start_time=start_time,
            end_time=end_time,
            user_host='test_host',
            query_time=(end_time - start_time).seconds,
            lock_time=20,
            rows_sent=5,
            rows_examined=3,
            sql_text='select * from test',
            db='test_mis_mm',
            last_insert_id=1,
            insert_id=2,
            server_id=1,
        )
        log2 = models_mongo.MysqlSlowQueriesTimeLog.objects.create(
            start_time=now,
            end_time=now,
            user_host='test_host',
            query_time=0,
            lock_time=20,
            rows_sent=5,
            rows_examined=3,
            sql_text='select * from test',
            db='test_mis_mm',
            last_insert_id=1,
            insert_id=2,
            server_id=1,
        )
        return log1, log2

    def test_without_params(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_filter_min_query_time(self):
        log1, log2 = self.generate_data()
        response = self.client.get(self.url, {'min_query_time': log1.query_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertNotIn(log2, response.context['page_obj'].object_list)

        response = self.client.get(self.url, {'min_query_time': log2.query_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)

    def test_filter_min_dc(self):
        log1, log2 = self.generate_data()
        response = self.client.get(self.url, {'min_dc': log1.start_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)

        response = self.client.get(self.url, {'min_dc': log2.start_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertNotIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)

    def test_filter_max_dc(self):
        log1, log2 = self.generate_data()
        response = self.client.get(self.url, {'max_dc': log1.start_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)


class BinLogTestCase(TestCase):
    def setUp(self):
        self.url = '/bin_log/'

    def generate_data(self):
        now = datetime.datetime.now()
        start_time = now - datetime.timedelta(seconds=30)
        end_time = now + datetime.timedelta(seconds=10)

        log1 = models_mongo.MysqlBinLogTimeLog.objects.create(
            start_time=start_time,
            end_time=end_time,
            exec_time=(start_time - end_time).seconds,
            timestamp=start_time,
            error_code=0,
            query='insert blablabla',
            query_type=models_mongo.MysqlBinLogTimeLog.INSERT_QUERY_TYPE,
        )

        log2 = models_mongo.MysqlBinLogTimeLog.objects.create(
            start_time=now,
            end_time=now,
            exec_time=0,
            timestamp=start_time,
            error_code=0,
            query='insert blablabla',
            query_type=models_mongo.MysqlBinLogTimeLog.INSERT_QUERY_TYPE,
        )

        return log1, log2

    def test_without_params(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_filter_min_query_time(self):
        log1, log2 = self.generate_data()
        response = self.client.get(self.url, {'min_exec_time': log1.exec_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertNotIn(log2, response.context['page_obj'].object_list)

        response = self.client.get(self.url, {'min_exec_time': log2.exec_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)

    def test_filter_min_dc(self):
        log1, log2 = self.generate_data()
        response = self.client.get(self.url, {'min_dc': log1.start_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)

        response = self.client.get(self.url, {'min_dc': log2.start_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertNotIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)

    def test_filter_max_dc(self):
        log1, log2 = self.generate_data()
        response = self.client.get(self.url, {'max_dc': log1.start_time})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].errors)
        self.assertIn(log1, response.context['page_obj'].object_list)
        self.assertIn(log2, response.context['page_obj'].object_list)


class ViewMiddlewareTestCase(TestCase, TearDownTestCaseMixin):
    def setUp(self):
        url = '/views_log/'
        factory = RequestFactory()
        self.request = factory.get(url)
        self.middleware = ViewTimeLoggerMiddleware()

    def tearDown(self):
        self.tearDownMongo()

    def test_process_request(self):
        self.middleware.process_request(self.request)

        self.assertTrue(
            hasattr(self.request, 'time_logger')
        )

        self.assertAlmostEqual(
            self.request.time_logger['start_dt'],
            datetime.datetime.now(),
            delta=datetime.timedelta(seconds=1),
        )

    def test_process_view(self):
        view = views.ViewsLog.as_view()
        args = [1, 2, 3]
        kwargs = {'a': 1, 'b': 2, 'c': 3}

        self.middleware.process_request(self.request)
        self.middleware.process_view(self.request, view, args, kwargs)

        self.assertEqual(self.request.time_logger['view_func'], view)
        self.assertEqual(self.request.time_logger['view_args'], args)
        self.assertEqual(self.request.time_logger['view_kwargs'], kwargs)

    @mock.patch('time_logger.middleware.view_logger.ViewTimeLogger._log_view')
    def test_process_response(self, log_view_mock):
        self.middleware.process_response(self.request, None)
        self.assertTrue(log_view_mock.called)

    @mock.patch('time_logger.middleware.view_logger.ViewTimeLogger._log_view')
    def test_process_exception(self, log_view_mock):
        self.middleware.process_exception(self.request, None)
        self.assertTrue(log_view_mock.called)


class LogViewFuncViewMiddlewareTestCase(TestCase, TearDownTestCaseMixin):
    def setUp(self):
        url = '/views_log/'
        factory = RequestFactory()
        self.request = factory.get(url)
        self.middleware = ViewTimeLoggerMiddleware()
        self.request.time_logger = {
            'start_dt': datetime.datetime.now(),
            'view_func': views.ViewsLog.as_view(),
            'view_args': [1, 2, 3],
            'view_kwargs': {'a': 1, 'b': 2, 'c': 3},
        }
        user = User.objects.create(username='tester')
        self.request.user = user

    def tearDown(self):
        self.tearDownMongo()

    def test_no_logging_without_settings(self):
        with self.settings(LOG_VIEW_TIME=None):
            self.middleware._log_view(self.request)
            self.assertFalse(
                models_mongo.ViewTimeLog.objects.all().count()
            )

    def test_no_logging_with_small_duration(self):
        small_delta = datetime.timedelta(seconds=settings.LOG_VIEW_TIME - 2)
        self.request.time_logger['start_dt'] = self.request.time_logger['start_dt'] - small_delta

        self.middleware._log_view(self.request)
        self.assertFalse(
            models_mongo.ViewTimeLog.objects.all().count()
        )

    def test_no_logging_with_big_duration(self):
        big_duration = settings.LOG_VIEW_TIME + 2
        big_delta = datetime.timedelta(seconds=big_duration)
        self.request.time_logger['start_dt'] = self.request.time_logger['start_dt'] - big_delta

        self.middleware._log_view(self.request)
        self.assertTrue(
            models_mongo.ViewTimeLog.objects.all().count()
        )

        log = models_mongo.ViewTimeLog.objects.get()
        self.assertEqual(log.duration, big_duration)
        self.assertEqual(log.view_func_path, 'time_logger.views.ViewsLog')
        self.assertEqual(log.view_args, self.request.time_logger['view_args'])
        self.assertEqual(log.view_kwargs, self.request.time_logger['view_kwargs'])
        self.assertEqual(log.request_get, {})
        self.assertEqual(log.request_post, {})
        self.assertAlmostEqual(log.dc, datetime.datetime.now(), delta=datetime.timedelta(seconds=1))


class BaseLogParserTestCase(TestCase):
    def test_iter(self):
        parser = BaseLogParser()
        self.assertEqual(parser.__iter__(), parser)

    @mock.patch.object(BaseLogParser, '_parse_entry')
    def test_next(self, mocked_parse_entry):
        mocked_parse_entry.return_value = None
        parser = BaseLogParser()
        self.assertRaises(StopIteration, parser.next)
        self.assertTrue(mocked_parse_entry.called)

        mocked_parse_entry.reset_mock()
        mocked_parse_entry.return_value = 'test'
        self.assertEqual(parser.next(), mocked_parse_entry.return_value)

    def test_get_next_line(self):
        parser = BaseLogParser()
        parser._stream = mock.Mock()
        parser._stream.readline = mock.Mock(return_value=None)

        self.assertIsNone(parser._get_next_line())
        self.assertTrue(parser._stream.readline.called)

        parser._stream.readline.reset_mock()
        parser.delimiter = 'DELIMITER'
        line = 'test_line'
        parser._stream.readline.return_value = '{}{}\r\n'.format(line, parser.delimiter)
        self.assertEqual(parser._get_next_line(), line)
        self.assertTrue(parser._stream.readline.called)

    def test_parse_line(self):
        mocked_regex = mock.Mock()
        mocked_regex.match = mock.Mock(return_value=None)
        line = 'test_line'
        self.assertRaises(
            LogParserError,
            BaseLogParser._parse_line, mocked_regex, line
        )

        mocked_regex.match.reset_mock()
        mocked_regex.match.return_value = mock.Mock()
        result = BaseLogParser._parse_line(mocked_regex, line)
        self.assertTrue(mocked_regex.match.called)
        self.assertTrue(mocked_regex.match.return_value.groups.called)

    def test_parse_headers(self):
        parser = BaseLogParser()
        self.assertRaises(NotImplementedError, parser._parse_headers, '')

    def test_parse_entry(self):
        parser = BaseLogParser()
        self.assertRaises(NotImplementedError, parser._parse_entry)


class MysqlBinLogParserTestCase(TestCase):
    @mock.patch.object(MysqlBinLogParser, '_parse_headers')
    @mock.patch.object(MysqlBinLogParser, '_get_next_line')
    @mock.patch('__builtin__.open')
    def test__init__(self, open_mock, _get_next_line_mock, _parse_headers_mock):
        _get_next_line_mock.return_value = None
        MysqlBinLogParser('test_file')
        self.assertTrue(open_mock.called)
        self.assertTrue(_get_next_line_mock.called)
        self.assertFalse(_parse_headers_mock.called)

        open_mock.reset_mock()
        _get_next_line_mock.reset_mock()
        _get_next_line_mock.return_value = 'test_line'
        MysqlBinLogParser('test_file')
        self.assertTrue(open_mock.called)
        self.assertTrue(_get_next_line_mock.called)
        _parse_headers_mock.assert_called_with(_get_next_line_mock.return_value)

    @mock.patch.object(MysqlBinLogParser, '_parse_line')
    @mock.patch.object(MysqlBinLogParser, '_get_next_line')
    @mock.patch.object(MysqlBinLogParser, '__init__')
    def test_parse_headers(self, __init__mock, _get_next_line_mock, _parse_line_mock):
        query_line = '#150822 13:01:45 server id 192168352  end_log_pos 519   Query   thread_id=3552  exec_time=0 ' \
                     'error_code=0'

        # return None because there is no line 'BEGIN'
        __init__mock.return_value = None
        parser = MysqlBinLogParser('test_file')
        parser._cached_line = None
        _parse_line_mock.side_effect = ['DELIMITER', ]
        _get_next_line_mock.side_effect = [
            'some_line',
            'some_line',
            query_line,
            None,
        ]
        self.assertIsNone(parser._parse_headers('DELIMITER;'))
        self.assertIsNone(parser._cached_line)

        _parse_line_mock.reset_mock()
        _parse_line_mock.side_effect = ['DELIMITER', ]
        _get_next_line_mock.reset_mock()
        # return None because there is no line contains QUERY
        _get_next_line_mock.side_effect = [
            'some_line',
            'some_line',
            'BEGIN',
            None,
        ]
        self.assertIsNone(parser._parse_headers('DELIMITER;'))
        self.assertIsNone(parser._cached_line)

        _parse_line_mock.reset_mock()
        _parse_line_mock.side_effect = ['DELIMITER', ]
        _get_next_line_mock.reset_mock()
        # return None because there is no line contains QUERY
        _get_next_line_mock.side_effect = [
            'some_line',
            'some_line',
            'BEGIN',
            query_line,
        ]
        self.assertIsNone(parser._parse_headers('DELIMITER;'))
        self.assertEqual(parser._cached_line, query_line)

    @mock.patch.object(MysqlBinLogParser, '_parse_timestamp')
    @mock.patch.object(MysqlBinLogParser, '_parse_line')
    @mock.patch.object(MysqlBinLogParser, '_get_next_line')
    @mock.patch.object(MysqlBinLogParser, '__init__')
    def test_parse_entry(self, __init__mock, _get_next_line_mock, _parse_line_mock, _parse_timestamp_mock):
        start_time, server_id, end_log_pos, thread_id, exec_time, error_code = \
            '150822 13:01:45', '192168352', '519', 3552, 0, 0
        query_line = '#{0} server id {1}  end_log_pos {2}   Query   thread_id={3}  exec_time={4} ' \
                     'error_code={5}'.format(start_time, server_id, end_log_pos, thread_id, exec_time, error_code)

        __init__mock.return_value = None

        parser = MysqlBinLogParser('')
        parser._cached_line = None

        # check None line
        _get_next_line_mock.return_value = None
        self.assertIsNone(parser._parse_entry())

        parser._cached_line = query_line
        query_type = 'INSERT'
        query = 'blablabla'
        db = 'test'
        db_line = 'use {}'.format(db)
        _get_next_line_mock.side_effect = [
            db_line,
            'SET TIMESTAMP=1440237705/*!*/;',
            '{} {}'.format(query_type, query),
            BIN_LOG_END,
        ]

        parse_line_side_effects = [(start_time, server_id, end_log_pos, thread_id, exec_time, error_code),
                                   [db, ], ]
        side_effect = lambda *args, **kwargs: parse_line_side_effects.pop(0)
        _parse_line_mock.side_effect = side_effect
        timestamp = 'test_timestamp'
        _parse_timestamp_mock.return_value = timestamp

        # parse entry
        entry = parser._parse_entry()
        self.assertEqual(entry['start_time'], datetime.datetime.strptime(start_time, "%y%m%d %H:%M:%S"))
        self.assertEqual(entry['server_id'], server_id)
        self.assertEqual(entry['end_log_pos'], end_log_pos)
        self.assertEqual(entry['thread_id'], thread_id)
        self.assertEqual(entry['error_code'], error_code)
        self.assertEqual(entry['db'], db)
        self.assertEqual(entry['timestamp'], timestamp)
        self.assertEqual(entry['query'], '{} {}'.format(query_type, query))
        self.assertEqual(entry['query_type'], query_type)
        self.assertTrue(_parse_timestamp_mock.called)
        self.assertEqual(_get_next_line_mock.call_count, 5)
        self.assertEqual(parser._cached_line, BIN_LOG_END)
        # check parse_line args
        expected = [
            mock.call(
                _BIN_LOG_QUERY_STATS,
                '#{0} server id {1}  end_log_pos {2}   Query   thread_id={3}  exec_time={4} error_code={5}'.
                    format(start_time, server_id, end_log_pos, thread_id, exec_time, error_code)
            ),
            mock.call(_BIN_LOG_DB, db_line)
        ]
        self.assertEqual(_parse_line_mock.call_args_list, expected)
        # end of log file
        self.assertIsNone(parser._parse_entry())

    @mock.patch.object(MysqlBinLogParser, '_parse_line')
    @mock.patch.object(MysqlBinLogParser, '__init__')
    def test_parse_timestamp(self, __init__mock, _parse_line_mock):
        __init__mock.return_value = None
        parser = MysqlBinLogParser('')
        line = 'SET TIMESTAMP=1440237705/*!*/;'
        _parse_line_mock.return_value = ['1440237705', ]
        timestamp = parser._parse_timestamp(line)
        self.assertEqual(
            timestamp,
            datetime.datetime.fromtimestamp(float(_parse_line_mock.return_value[0])))
        _parse_line_mock.assert_called_with(_BING_LOG_TIMESTAMP, line)


class MysqlSlowQueriesParserTestCase(TestCase):
    @mock.patch.object(MysqlSlowQueriesParser, '_get_next_line')
    @mock.patch.object(MysqlSlowQueriesParser, '_parse_headers')
    @mock.patch('__builtin__.open')
    def test__init__(self, open_mock, _parse_headers_mock, _get_next_line_mock):
        _get_next_line_mock.return_value = None
        file_path = 'test_file'
        MysqlSlowQueriesParser(file_path)
        open_mock.assert_called_with(file_path, 'r')
        self.assertTrue(_get_next_line_mock.called)
        self.assertFalse(_parse_headers_mock.called)

        _get_next_line_mock.reset_mock()
        open_mock.reset_mock()
        open_mock.reset_mock()
        _get_next_line_mock.return_value = 'blablabla started with:'
        file_path = 'test_file'
        MysqlSlowQueriesParser(file_path)
        open_mock.assert_called_with(file_path, 'r')
        self.assertTrue(_get_next_line_mock.called)
        self.assertTrue(_parse_headers_mock.called)
        _parse_headers_mock.assert_called_with(_get_next_line_mock.return_value)

    @mock.patch.object(MysqlSlowQueriesParser, '_get_next_line')
    @mock.patch.object(MysqlSlowQueriesParser, '__init__')
    def test_parse_headers(self, __init__mock, _get_next_line_mock):
        __init__mock.return_value = None
        line = '/usr/sbin/mysqld, Version: 5.5.40-0ubuntu0.14.04.1-log ((Ubuntu)). started with:'
        side_effects = [
            'Tcp port: 3306  Unix socket: /var/run/mysqld/mysqld.sock',
            'Time                 Id Command    Argument',
        ]
        _get_next_line_mock.side_effect = side_effects
        parser = MysqlSlowQueriesParser('')
        result = parser._parse_headers(line)
        self.assertEqual(result, side_effects[-1])
        self.assertEqual(_get_next_line_mock.call_count, 2)

    @mock.patch.object(MysqlSlowQueriesParser, '_parse_queries')
    @mock.patch.object(MysqlSlowQueriesParser, '_parse_statistics')
    @mock.patch.object(MysqlSlowQueriesParser, '_parse_connection_info')
    @mock.patch.object(MysqlSlowQueriesParser, '_parse_time')
    @mock.patch.object(MysqlSlowQueriesParser, '_get_next_line')
    @mock.patch.object(MysqlSlowQueriesParser, '__init__')
    def test_parse_entry(self, __init__mock, _get_next_line_mock, _parse_time_mock,
                         _parse_connection_info_mock, _parse_statistics_mock, _parse_queries_mock):
        __init__mock.return_value = None
        _get_next_line_mock.return_value = None
        parser = MysqlSlowQueriesParser('')
        parser._cached_line = None
        self.assertIsNone(parser._parse_entry())

        _get_next_line_mock.reset_mock()
        private_user, unprivate_user, host, ip = 'test', 'test2', 'localhost', '127.0.0.1'
        query_time, lock_time, rows_sent, rows_examined = '30', '1', '3', '131758'
        queries = 'use test; set timestamp=123; select blablabla;'
        get_next_line_side_effect = [
            '# User@Host: {0}[{1}] @ {2} {3}'.format(private_user, unprivate_user, host, ip),
            '# Query_time: {0}  Lock_time: {1} Rows_sent: {2}  Rows_examined: {3}'.
                format(query_time, lock_time, rows_sent, rows_examined),
            queries,
        ]
        _get_next_line_mock.side_effect = get_next_line_side_effect

        timestamp = '150825  3:31:06'
        parser._cached_line = '# Time: {}'.format(timestamp)
        _parse_time_mock.return_value = datetime.datetime.strptime(timestamp, "%y%m%d %H:%M:%S")
        _parse_connection_info_mock.return_value = (private_user, unprivate_user, host, ip)
        _parse_statistics_mock.return_value = (query_time, lock_time, rows_sent, rows_examined)
        _parse_queries_mock.return_value = queries

        entry = parser._parse_entry()
        self.assertTrue(__init__mock.called)
        self.assertEqual(_get_next_line_mock.call_count, 3)
        _parse_time_mock.assert_called_with('# Time: {}'.format(timestamp))
        _parse_connection_info_mock.assert_called_with(get_next_line_side_effect[0])
        _parse_statistics_mock.assert_called_with(get_next_line_side_effect[1])
        _parse_queries_mock.assert_called_with(get_next_line_side_effect[2])
        self.assertEqual(entry['start_time'], _parse_time_mock.return_value)
        self.assertEqual(entry['user'], private_user)
        self.assertEqual(entry['host'], host)
        self.assertEqual(entry['query_time'], float(query_time))
        self.assertEqual(entry['lock_time'], float(lock_time))
        self.assertEqual(entry['rows_sent'], float(rows_sent))
        self.assertEqual(entry['rows_examined'], int(rows_examined))
        self.assertEqual(entry['queries_list'], queries)

    @mock.patch.object(MysqlSlowQueriesParser, '__init__')
    def test_parse_time(self, __init__mock):
        __init__mock.return_value = None
        parser = MysqlSlowQueriesParser('')

        time_str = '150825  3:31:06'
        line = '# Time: {}'.format(time_str)
        result = parser._parse_time(line)
        self.assertEqual(result, datetime.datetime.strptime(time_str, "%y%m%d %H:%M:%S"))

    @mock.patch.object(MysqlSlowQueriesParser, '__init__')
    def test_parse_connection_info(self, __init__mock):
        __init__mock.return_value = None
        parser = MysqlSlowQueriesParser('')

        private_user, unprivate_user, host, ip = 'test', 'test2', 'localhost', '127.0.0.1'
        line = '# User@Host: {0}[{1}] @ {2} [{3}]'.format(private_user, unprivate_user, host, ip)
        result = parser._parse_connection_info(line)
        self.assertEqual(result, (private_user, unprivate_user, host, ip))

    @mock.patch.object(MysqlSlowQueriesParser, '__init__')
    def test_parse_statistics(self, __init__mock):
        __init__mock.return_value = None
        parser = MysqlSlowQueriesParser('')

        query_time, lock_time, rows_sent, rows_examined = '30.3', '1.2', '3', '131758'
        line = '# Query_time: {0}  Lock_time: {1} Rows_sent: {2}  Rows_examined: {3}'.\
            format(query_time, lock_time, rows_sent, rows_examined)
        result = parser._parse_statistics(line)
        self.assertEqual(result, (query_time, lock_time, rows_sent, rows_examined))

    @mock.patch.object(MysqlSlowQueriesParser, '_get_next_line')
    @mock.patch.object(MysqlSlowQueriesParser, '__init__')
    def test_parse_queries(self, __init__mock, _get_next_line_mock):
        __init__mock.return_value = None
        _get_next_line_mock.return_value = '# Time: blablabla'
        parser = MysqlSlowQueriesParser('')

        line = 'use test; set timestamp=123; select blablabla;'
        result = parser._parse_queries(line)
        self.assertEqual(parser._cached_line, _get_next_line_mock.return_value)
        self.assertTrue(_get_next_line_mock.called)
        self.assertEqual(result, [line, ])
