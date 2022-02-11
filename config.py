import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    ELASTICSEARCH_HOST = os.environ.get('ES_HOST') or 'http://localhost:9200'
    ELASTICSEARCH_USER = os.environ.get('ES_USER') or 'elastic'
    ELASTICSEARCH_PASSWORD = os.environ.get('ES_PWD') or 'changeit'
