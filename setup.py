# coding: utf-8
# python setup.py sdist register upload
# from distutils.core import setup
from setuptools import setup

setup(
    name='django-time-logger',
    version='0.0.5',
    description='Time logger for django',
    author='Telminov Sergey',
    url='https://github.com/telminov/django-time-logger',
    packages=[
        'time_logger',
        'time_logger/middleware',
    ],
    include_package_data=True,
    license='The MIT License',
    test_suite='runtests.runtests',
    install_requires=[
        'django',
        'sw-django-utils',
    ],
)
