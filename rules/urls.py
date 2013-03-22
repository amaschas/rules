from django.conf.urls import patterns, include, url

from views import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^user/(?P<user_id>\d+)$', UserView.as_view()),
    url(r'^create-rule/$', RuleCreateView.as_view()),
    url(r'^update-rule/(?P<id>\d+)/$', RuleUpdateView.as_view()),
    url(r'^channel-create-form/$', ChannelCreateView.as_view()),
    url(r'^score/$', ScoreView.as_view()),
)
