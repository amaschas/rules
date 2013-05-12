import re, redis, json, time
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Sum, Count
from django.core.paginator import Paginator

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
    # score = Score.objects.filter(rule=kwargs['rule_id']).aggregate(Sum('score'))
    # count = Score.objects.filter(rule=kwargs['rule_id']).count()
    return {'rule' : rule }


# Checks whether rules is currently scoring by channel, how many lines complete out of total, latest date scored
class RuleStatusView(View):
  def get(self, request, *args, **kwargs):
    data = dict()
    data['channels'] = list()
    data['score'] = Score.objects.filter(rule=kwargs['rule_id']).aggregate(Sum('score'))
    data['count'] = Score.objects.filter(rule=kwargs['rule_id']).count()
    for score_meta in ScoreMeta.objects.filter(rule=kwargs['rule_id']):
      locked = check_lock('rule-%s-scoring' % score_meta.rule.id)
      percent_complete = 0
      if score_meta.line_index > 0 and score_meta.line_index > 0:
        percent_complete = score_meta.line_index * 100 / score_meta.channel.line_count
      data['channels'].append({'locked' : locked, 'channel_title' : score_meta.channel.title, 'lines_scored' : score_meta.line_index, 'date_scored' : score_meta.channel.get_latest_date().strftime('%h, %d %Y'), 'line_total' : score_meta.channel.line_count, 'percent_complete' : percent_complete})
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

    for score in Score.objects.filter(rule=kwargs['rule_id']).order_by('line_index').reverse()[:limit]:
      pipe.hgetall('-'.join([score.channel.slug, str(score.line_index)]))
    line_data = pipe.execute()
    for line in line_data:
      data.append({'nick' : line['nick'], 'line' : line['line'], 'rule' : rule.rule})
    json_data = json.dumps(data)
    return HttpResponse(json_data, mimetype='application/json')


class ScorePlotValues(View):
  def get(self, request, *args, **kwargs):
    data = []
    try:
      channels = Channel.objects.all()
      for channel in channels:
        plot_list = list()
        start_date = int(channel.start_date.strftime("%s")) * 1000
        latest_score = Score.objects.filter(channel=channel).latest('date')
        end_date = int(latest_score.date.strftime("%s")) * 1000
        plot_values = Score.objects.filter(rule=kwargs['rule_id']).extra({'date':"date(date)"}).values('date').annotate(score=Count('score')).order_by('date')
        for plot in plot_values:
          timestamp = int(plot['date'].strftime("%s")) * 1000
          plot_list.append([timestamp, plot['score']])
          print '%s %s' % (plot['date'], plot['score'])
        data.append({'start_date' : start_date, 'end_date' : end_date, 'plot_values' : plot_list})
      json_data = json.dumps(data, cls=DjangoJSONEncoder)
      return HttpResponse(json_data, mimetype='application/json')
    except ObjectDoesNotExist:
      return HttpResponse(status=404)

class NickAssignmentView(RulesView):
  template_name = 'nick-assignment.html'

  def BuildContext(self, request, args, kwargs):
    try:
      try:
        if request.GET['order_by'] in {'name', 'first_seen'}:
          order_by = request.GET['order_by']
        else:
          order_by = 'name'
      except:
        order_by = 'name'
      nicks = Nick.objects.filter(user__isnull=True).order_by(order_by)
      # if 'paged' in request.GET and request.GET['paged'] == False:
      #   return {'nicks' : nicks }
      # else:
      try:
        per_page = int(request.GET['per_page'])
      except:
        per_page = 10
      try:
        page = int(request.GET['page'])
      except:
        page = 1
      paged_nicks = Paginator(nicks, per_page)
      return {'nicks' : paged_nicks.page(page), 'pages' : paged_nicks.page_range, 'per_page' : per_page }
    except ObjectDoesNotExist:
      return

