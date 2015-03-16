from django.conf.urls import patterns, include, url
from .views import eval


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'evaler.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^eval$', eval, name='eval'),
)
