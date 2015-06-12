# coding: utf-8
import datetime
from django.conf import settings
import inspect

from time_logger import mongo_models

class ViewTimeLogger(object):

    def process_request(self, request):
        request.time_logger = {
            'start_dt': datetime.datetime.now(),
            'view_func': None,
            'view_args': None,
            'view_kwargs': None,
        }
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.time_logger['view_func'] = view_func
        request.time_logger['view_args'] = view_args
        request.time_logger['view_kwargs'] = view_kwargs

    def process_response(self, request, response):
        self._log_view(request)
        return response

    def process_exception(self, request, exception):
        self._log_view(request)
        return None


    def _log_view(self, request):
        duration = datetime.datetime.now() - request.time_logger['start_dt']

        is_exceed_time = hasattr(settings, 'LOG_VIEW_TIME') and duration > datetime.timedelta(seconds=settings.LOG_VIEW_TIME)
        if is_exceed_time:
            view_func_module = inspect.getmodule(request.time_logger['view_func'])
            view_func_path = '%s.%s' % (view_func_module.__name__, request.time_logger['view_func'].__name__)

            mongo_models.ViewTimeLog.objects.create(
                duration=duration.seconds,
                view_func_path=view_func_path,
                view_args=request.time_logger['view_args'],
                view_kwargs=request.time_logger['view_kwargs'],
                username=request.user.username,
                request_get=self._query_to_dict(request.GET),
                request_post=self._query_to_dict(request.POST),
            )


    def _query_to_dict(self, qd):
        result = {}
        for key in qd:
            values = qd.getlist(key)
            if len(values) > 1:
                result[key] = values
            else:
                result[key] = qd[key]
        return result

