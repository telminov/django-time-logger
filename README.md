# django-time-logger
[![Build Status](https://travis-ci.org/telminov/django-time-logger.svg?branch=master)](https://travis-ci.org/telminov/django-time-logger)
[![Coverage Status](https://coveralls.io/repos/telminov/django-time-logger/badge.svg?branch=master)](https://coveralls.io/r/telminov/django-time-logger?branch=master)

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

Optional can be set mongo database for logging
```
mongoengine.connect(...)
mongoengine.register_connection('local', ...)
...
LOG_VIEW_TIME_DB_ALIAS = 'local'
```
