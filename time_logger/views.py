# coding: utf-8
import datetime
from django.views.generic import TemplateView
from django.views.generic.list import MultipleObjectMixin

from . import forms
from . import mongo_models

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
        qs = mongo_models.ViewTimeLog.objects.filter(**params)
        return qs

    def get_queryset_params(self):
        params = {}

        if self.form.cleaned_data.get('min_duration'):
            params['duration__gte'] = self.form.cleaned_data['min_duration']

        if self.form.cleaned_data.get('view_func_path'):
            params['view_func_path'] = self.form.cleaned_data['view_func_path']

        if self.form.cleaned_data.get('min_dc'):
            params['dc__gte'] = _date_to_datetime(self.form.cleaned_data['min_dc'])

        if self.form.cleaned_data.get('max_dc'):
            params['dc__lte'] = _date_to_datetime_lte(self.form.cleaned_data['max_dc'])

        return params



def _date_to_datetime(date):
    return datetime.datetime(*(date.timetuple()[:6]))

def _date_to_datetime_lte(date):
    return datetime.datetime.combine(date, datetime.time(23, 59, 59))
