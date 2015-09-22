import mock
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from djutils.testrunner import TearDownTestCaseMixin
from django.test import TestCase
from django.test.client import RequestFactory
from mysql_logs_parser_from_file import BaseLogParser, LogParserError
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

