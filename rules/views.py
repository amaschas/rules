import re, redis, json
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Sum, Count

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
from tasks import score_rules

class RulesView(TemplateView):
  def BuildContext(self, request, args, kwargs):
    return

  def get(self, request, *args, **kwargs):
    return self.render_to_response(self.BuildContext(request, args, kwargs))

  def post(self, request, *args, **kwargs):
    return self.render_to_response(self.BuildContext(request, args, kwargs))


class TestView(RulesView):
  template_name='test-form.html'

  def BuildContext(self, request, args, kwargs):
    form = TestForm()
    if request.method == 'POST':
      options = request.POST.getlist('choices')
      if 'delete-channels' in options:
        print 'deleting channels'
        Channel.objects.all().delete()
      if 'delete-rules' in options:
        print 'deleting rules'
        Rule.objects.all().delete()
      if 'delete-nicks' in options:
        print 'deleting nicks'
        Nick.objects.all().delete()
      if 'delete-scores' in options:
        print 'deleting scores'
        Score.objects.all().delete()
      if 'score-channels' in options:
        print 'scoring channels'
        channels = Channel.objects.all()
        for channel in channels:
          initial_channel_score.delay(channel)
      if 'score-rules' in options:
        print 'scoring rules'
        rules = Rule.objects.all()
        for rule in rules:
          initial_rule_score.delay(rule)
    return {'form' : form}


class RuleView(RulesView):
  template_name = 'rule.html'

  def BuildContext(self, request, args, kwargs):
    rule = Rule.objects.get(id=kwargs['rule_id'])
    score = Score.objects.filter(rule=kwargs['rule_id']).aggregate(Sum('score'))
    count = Score.objects.filter(rule=kwargs['rule_id']).count()
    print score
    return {'rule' : rule, 'score' : score['score__sum'], 'count' : count }


class RuleScoresView(View):
  def get(self, request, *args, **kwargs):
    # data = serializers.serialize('json', Score.objects.filter(rule=kwargs['rule_id']).order_by('date')[:10])
    data = []
    for score in Score.objects.filter(rule=kwargs['rule_id']).order_by('date')[:100]:
      rule = Rule.objects.get(id=score.rule.id)
      line = score.line()
      # print line
      # match = re.search(rule.rule, line[8:])
      # print match.group(0)
      data.append({'nick' : score.nick.name, 'line' : line, 'rule' : rule.rule})
      json_data = json.dumps(data)
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


# TODO view that shows a single Score (basically the line with the regex match highlighted)
# takes a Score object as an arg - test scoring can just send an unsaved instance - need to release instance afterwards?

# Receives a score request for a channel, gets the next line, starts the scoring process
class ScoreView(APIView):
  def post(self, request):
    print request.DATA
    try:
      channel = Channel.objects.get(slug=request.DATA['channel'])
      r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)

      #TODO should check if channel is active, ignore if it isn't

      # Get the next line
      next_line_index = channel.current_line + 1
      next_line = r.get('%s-%d' % (channel.slug, next_line_index))
      print next_line_index
      print next_line
      # next_line = r.get('avara-2523')
      if next_line:

        # Update the line here, so rule.score() can get the updated line from the channel
        channel.update_current_line(next_line_index)
        # This isn't necessary
        # channel.save()

        # If update_current_date returns false, line is not a date, score it
        if not channel.update_current_date(next_line):

          # If we can find a nick in the line, score it
          nick = Nick.get_nick(next_line)
          if nick:
            score_rules.delay(channel=channel, line=next_line, nick=nick)
    except ObjectDoesNotExist:
      pass
    return HttpResponse(status=201)
