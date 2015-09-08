from django.conf.urls import patterns, url
from time_logger.views import ViewsLog, SlowQueriesLog, BinLog

urlpatterns = patterns('',
   url(r'^views_log/$', ViewsLog.as_view()),
   url(r'^slow_queries_log/$', SlowQueriesLog.as_view()),
   url(r'^bin_log/$', BinLog.as_view()),
)
