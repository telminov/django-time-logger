import datetime
from django.conf import settings
from django.contrib.auth.models import User
from djutils.testrunner import TearDownTestCaseMixin
import mock
from django.test import TestCase
from django.test.client import RequestFactory
import models_mongo
from middleware.view_logger import ViewTimeLogger as ViewTimeLoggerMiddleware
import views

class ViewsTestCase(TestCase):
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

