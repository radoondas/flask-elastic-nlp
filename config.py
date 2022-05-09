import os
from app.utils import str_to_bool


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    ELASTICSEARCH_HOST = os.environ.get('ES_HOST') or 'http://localhost:9200'
    ELASTICSEARCH_USER = os.environ.get('ES_USER') or 'elastic'
    ELASTICSEARCH_PASSWORD = os.environ.get('ES_PWD') or 'changeit'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH')) or 1048576
    VERIFY_TLS = str_to_bool(os.environ.get('VERIFY_TLS', True))
