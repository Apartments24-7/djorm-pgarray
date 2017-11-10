# -*- coding: utf-8 -*-

from django import VERSION as DJANGO_VERSION

from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

admin.autodiscover()

if DJANGO_VERSION >= (1, 8):
    urlpatterns =  [
         url(r'^', include(admin.site.urls))
    ]

    urlpatterns += staticfiles_urlpatterns()
else:
    from django.conf.urls import patterns

    urlpatterns = patterns('',
        url(r'^', include(admin.site.urls)),
    )

    urlpatterns += staticfiles_urlpatterns()
