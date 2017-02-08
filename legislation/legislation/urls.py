"""legislation URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib.auth.views import logout
from django.contrib import admin
from frontend.views import *

urlpatterns = [
    #url(r'^admin/', admin.site.urls),
    url(r'^accounts/logout/$', logout,
     {'next_page': '/legis/'}),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^legis/$', home, name='home'),
    url(r'^legis/contact', contact, name='contact'),
    url(r'^legis/search', search, name='search'),
    url(r'^legis/save-search', save_search, name='save-search'),
    url(r'^legis/saved-searches', searches, name='searches'),
    url(r'^legis/bill/(?P<bill_id>\d+)', bill, name='bill')
]
