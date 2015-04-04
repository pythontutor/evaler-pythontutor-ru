from .base import *

with open('/srv/evaler-pythontutor-ru/secret-key') as secretkey_file:
    SECRET_KEY = secretkey_file.read().strip()

DEBUG = False
TEMPLATE_DEBUG = False

ALLOWED_HOSTS = [
    '.pythontutor.ru',
    '.learnpython.ru',
]
