# coding: utf-8
import datetime
from django.views.generic import TemplateView, DetailView
from django.views.generic.list import MultipleObjectMixin

from . import forms
from . import models_mongo


class ViewsLog(MultipleObjectMixin, TemplateView):
    form_class = forms.ViewsLoggerForm
    template_name = 'time_logger/views_log.html'
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = {}

        self.form = self.form_class(self.request.GET or None)
        if self.form.is_valid():
            self.object_list = self.get_queryset()
            context = super(ViewsLog, self).get_context_data(**kwargs)

        context['form'] = self.form
        return context

    def get_queryset(self):
        params = self.get_queryset_params()
        qs = models_mongo.ViewTimeLog.objects.filter(**params)
        return qs

    def get_queryset_params(self):
        params = {}

        if self.form.cleaned_data.get('min_duration'):
            params['duration__gte'] = self.form.cleaned_data['min_duration']

        if self.form.cleaned_data.get('view_func_path'):
            params['view_func_path'] = {
                '$regex': '^%s' % self.form.cleaned_data['view_func_path']
            }

        if self.form.cleaned_data.get('min_dc'):
            params['dc__gte'] = _date_to_datetime(self.form.cleaned_data['min_dc'])

        if self.form.cleaned_data.get('max_dc'):
            params['dc__lte'] = _date_to_datetime_lte(self.form.cleaned_data['max_dc'])

        return params

class ViewLogDetail(DetailView):
    model = models_mongo.ViewTimeLog
    template_name = 'time_logger/view_log_detail.html'

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        return models_mongo.ViewTimeLog.objects.get(pk=pk)

class SlowQueriesLog(MultipleObjectMixin, TemplateView):
    form_class = forms.SlowQueriesLog
    template_name = 'time_logger/slow_queries_log.html'
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = {}

        self.form = self.form_class(self.request.GET or None)
        if self.form.is_valid():
            self.object_list = self.get_queryset()
            context = super(SlowQueriesLog, self).get_context_data(**kwargs)

        context['form'] = self.form
        return context

    def get_queryset(self):
        params = self.get_queryset_params()
        qs = models_mongo.MysqlSlowQueriesTimeLog.objects.filter(**params)
        return qs

    def get_queryset_params(self):
        params = {}
        if self.form.cleaned_data.get('min_query_time'):
            params['query_time__gte'] = self.form.cleaned_data['min_query_time']

        if self.form.cleaned_data.get('min_dc'):
            params['start_time__gte'] = _date_to_datetime(self.form.cleaned_data['min_dc'])

        if self.form.cleaned_data.get('max_dc'):
            params['start_time__lte'] = _date_to_datetime_lte(self.form.cleaned_data['max_dc'])

        return params


class BinLog(MultipleObjectMixin, TemplateView):
    form_class = forms.BinLog
    template_name = 'time_logger/bin_log.html'
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = {}

        self.form = self.form_class(self.request.GET or None)
        if self.form.is_valid():
            self.object_list = self.get_queryset()
            context = super(BinLog, self).get_context_data(**kwargs)

        context['form'] = self.form
        return context

    def get_queryset(self):
        params = self.get_queryset_params()
        qs = models_mongo.MysqlBinLogTimeLog.objects.filter(**params)
        return qs

    def get_queryset_params(self):
        params = {}
        if self.form.cleaned_data.get('min_exec_time'):
            params['exec_time__gte'] = self.form.cleaned_data['min_exec_time']

        if self.form.cleaned_data.get('min_dc'):
            params['start_time__gte'] = _date_to_datetime(self.form.cleaned_data['min_dc'])

        if self.form.cleaned_data.get('max_dc'):
            params['start_time__lte'] = _date_to_datetime_lte(self.form.cleaned_data['max_dc'])

        return params


def _date_to_datetime(date):
    return datetime.datetime(*(date.timetuple()[:6]))


def _date_to_datetime_lte(date):
    return datetime.datetime.combine(date, datetime.time(23, 59, 59))
