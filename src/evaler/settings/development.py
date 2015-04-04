from .base import *

SECRET_KEY = 'txf!bliqz7x2_2(5cq8v1v9-1b31$dz4m$)m5cxtdfiwvnp1%0'

DEBUG = True
TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['*']


class AllIps(object):
    def __contains__(self, item):
        return True

INTERNAL_IPS = AllIps()
