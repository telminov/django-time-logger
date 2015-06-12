# coding: utf-8

from django import forms

class ViewsLoggerForm(forms.Form):
    min_duration = forms.IntegerField(required=False)
    view_func_path = forms.CharField(required=False)
    min_dc = forms.DateTimeField(required=False)
    max_dc = forms.DateTimeField(required=False)
