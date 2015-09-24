import mongoengine

ROOT_URLCONF = 'time_logger.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'time_logger.middleware.view_logger.ViewTimeLogger',
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.request',
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'time_logger',
]

SECRET_KEY = "123"

LOG_VIEW_TIME = 10

TEST_RUNNER = 'djutils.testrunner.TestRunnerWithMongo'

MONGODB = {
    'NAME': 'time_logger',
    'HOST': 'localhost',
}
mongoengine.connect(MONGODB['NAME'], host='mongodb://%s:27017/%s' % (MONGODB['HOST'], MONGODB['NAME']))
