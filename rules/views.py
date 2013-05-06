import re, redis, json, time
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Sum, Count

from django.core.serializers.json import DjangoJSONEncoder

# from django.utils import simplejson

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.exceptions import ObjectDoesNotExist
from django.core import serializers

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view

from models import *
from forms import *
from tasks import *
from lock import check_lock

#TODO:
  # Nick choosing
  # User page (see user rules and maybe scores?)
  # Home page, top 25 rules and scores per user

class RulesView(TemplateView):
  def BuildContext(self, request, args, kwargs):
    return

  def get(self, request, *args, **kwargs):
    return self.render_to_response(self.BuildContext(request, args, kwargs))

  def post(self, request, *args, **kwargs):
    return self.render_to_response(self.BuildContext(request, args, kwargs))


class RuleView(RulesView):
  template_name = 'rule.html'

  def BuildContext(self, request, args, kwargs):
    rule = Rule.objects.get(id=kwargs['rule_id'])
    score = Score.objects.filter(rule=kwargs['rule_id']).aggregate(Sum('score'))
    count = Score.objects.filter(rule=kwargs['rule_id']).count()
    return {'rule' : rule, 'score' : score['score__sum'], 'count' : count }


# Checks whether rules is currently scoring by channel, how many lines complete out of total, latest date scored
class RuleStatusView(View):
  def get(self, request, *args, **kwargs):
    data = []
    for score_meta in ScoreMeta.objects.filter(rule=kwargs['rule_id']):
      locked = check_lock('rule-%s-scoring' % score_meta.rule.id)
      data.append({'locked' : locked, 'channel_title' : score_meta.channel.title, 'lines_scored' : score_meta.line_index, 'date_scored' : score_meta.date.strftime('%h, %d %Y'), 'line_total' : score_meta.channel.line_count})
    json_data = json.dumps(data)
    return HttpResponse(json_data, mimetype='application/json')


class RuleScoresView(View):
  def get(self, request, *args, **kwargs):
    data = []
    limit = 100

    pool = redis.ConnectionPool(host='localhost', port=6379, db=1)
    r = redis.Redis(connection_pool=pool)
    pipe = r.pipeline()

    rule = Rule.objects.get(id=kwargs['rule_id'])

    for score in Score.objects.filter(rule=kwargs['rule_id']).order_by('date')[:limit]:
      pipe.hgetall('-'.join([score.channel.slug, str(score.line_index)]))
    line_data = pipe.execute()
    for line in line_data:
      data.append({'nick' : line['nick'], 'line' : line['line'], 'rule' : rule.rule})
    json_data = json.dumps(data)
    return HttpResponse(json_data, mimetype='application/json')


class ScorePlotValues(View):
  def get(self, request, *args, **kwargs):
    data = []
    channels = Channel.objects.all()
    for channel in channels:
      plot_list = list()
      start_date = int(channel.start_date.strftime("%s")) * 1000
      latest_score = Score.objects.filter(channel=channel).latest('date')
      end_date = int(latest_score.date.strftime("%s")) * 1000
      plot_values = Score.objects.extra({'date':"date(date)"}).values('date').annotate(score=Count('score')).order_by('date')
      for plot in plot_values:
        timestamp = int(plot['date'].strftime("%s")) * 1000
        print timestamp
        plot_list.append([timestamp, plot['score']])
      data.append({'start_date' : start_date, 'end_date' : end_date, 'plot_values' : plot_list})
    json_data = json.dumps(data, cls=DjangoJSONEncoder)
    return HttpResponse(json_data, mimetype='application/json')


class UserView(RulesView):
  template_name = 'user.html'

  def BuildContext(self, request, args, kwargs):
    nicks = Nick.objects.filter(user=kwargs['user_id'])
    rules = Rule.objects.filter(creator=kwargs['user_id'])
    return {'nicks' : nicks, 'rules' : rules}


class RuleCreateView(CreateView):
  model = Rule
  form_class = RuleForm
  template_name = 'rule-form.html'
  def get_initial(self):
    initial = super(RuleCreateView, self).get_initial()
    initial = initial.copy()
    initial['creator'] = self.request.user
    return initial

# TODO: I think this is going to need a custom view and form
class RuleUpdateView(UpdateView):
  model = Rule
  form_class = RuleUpdateForm
  template_name = 'rule-form.html'

  def get_object(self, queryset=None):
      obj = Rule.objects.get(id=self.kwargs['id'])
      return obj


class ChannelCreateView(CreateView):
  model = Channel
  form_class = ChannelForm
  template_name = 'channel-form.html'
  # def get_initial(self):
  #   initial = super(RuleCreateView, self).get_initial()
  #   initial = initial.copy()
  #   initial['creator'] = self.request.user
  #   return initial


# Receives a score request for a channel, gets the next line, starts the scoring process
class ScoreView(APIView):
  def post(self, request):
    # print request.DATA
    try:
      channel = Channel.objects.get(slug=request.DATA['channel'])
      update_channel.delay(channel)
      return HttpResponse(status=201)
    except ObjectDoesNotExist:
      return HttpResponse(status=404)
