# django-time-logger

Installation python package:
```
$ pip install django-time-logger
```
  
Add middleware into settings.py:
```
MIDDLEWARE_CLASSES = (
    ...
    'time_logger.middleware.view_logger.ViewTimeLogger',
    ...
)
```

Set threshold time value in seconds into settings.py for logging view
```
LOG_VIEW_TIME = 10
```
