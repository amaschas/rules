from django.conf.urls import patterns, include, url

from views import *
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^user/(?P<user_id>\d+)$', UserView.as_view()),
    url(r'^rule-create-form/$', RuleCreateView.as_view()),
    url(r'^score/(?P<score_string>.*)$', ScoreView.as_view()),
    # url(r'^nick-form/$', NickFormView.as_view()),
)
