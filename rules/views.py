import redis
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect, Http404

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view

from models import *
from forms import *
from tasks import score_rules

class RulesView(TemplateView):
  def BuildContext(self, request, args, kwargs):
    return

  def get(self, request, *args, **kwargs):
    return self.render_to_response(self.BuildContext(request, args, kwargs))


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

      # Get the next line
      next_line_index = channel.current_line + 1
      next_line = r.get('%s-%d' % (channel.slug, next_line_index))
      # next_line = r.get('avara-2523')
      if next_line:

        # Update the line here, so rule.score() can get the updated line from the channel
        channel.update_current_line(next_line_index)
        channel.save()

        # If update_current_date returns false, line is not a date, score it
        if not channel.update_current_date(next_line):

          # If we can find a nick in the line, score it
          nick = Nick.get_nick(next_line)
          if nick:
            score_rules.delay(channel=channel, line=next_line, nick=nick)
    except ObjectDoesNotExist:
      pass
    return HttpResponse(status=201)
