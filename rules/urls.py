from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from views import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    # url(r'^user/(?P<user_id>\d+)$', UserView.as_view()),
    url(r'^rule/(?P<rule_id>\d+)$', RuleView.as_view()),
    url(r'^rule/status/(?P<rule_id>\d+)$', RuleStatusView.as_view()),
    url(r'^rule/scores/(?P<rule_id>\d+)$', RuleScoresView.as_view()),
    url(r'^rule/plot/(?P<rule_id>\d+)$', ScorePlotValues.as_view()),
    url(r'^rule/scores/test/(?P<rule_id>\d+)$', RuleScoresView.as_view()),
    # url(r'^create-rule/$', RuleCreateView.as_view()),
    # url(r'^update-rule/(?P<id>\d+)/$', RuleUpdateView.as_view()),
    # url(r'^channel-create-form/$', ChannelCreateView.as_view()),
    # url(r'^score/$', ScoreView.as_view()),
)

urlpatterns += staticfiles_urlpatterns()

# urlpatterns += patterns('',
#   url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
#       'document_root': settings.MEDIA_ROOT,
#   }),
# )