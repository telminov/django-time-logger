from django.conf.urls import patterns, url
from time_logger.views import ViewsLog

urlpatterns = patterns('',
   url(r'^views_log/$', ViewsLog.as_view()),
)
