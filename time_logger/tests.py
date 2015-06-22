import datetime
from django.test import TestCase
import mongo_models


class ViewsTestCase(TestCase):
    def setUp(self):
        self.url = '/views_log/'

    def generate_data(self):
        mongo_models.ViewTimeLog.objects.create(
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
        log = mongo_models.ViewTimeLog.objects.all()[0]

        params = {'view_func_path': log.view_func_path}
        self._assert_exists(params)

        params['view_func_path'] += '123'
        self._assert_not_exists(params)

    def test_filter_dc(self):
        self.generate_data()
        log = mongo_models.ViewTimeLog.objects.all()[0]

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
