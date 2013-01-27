from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect

from django.views.generic.edit import CreateView, UpdateView, DeleteView

from models import *
from forms import *

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

class ScoreView(View):

  def post(self, request, args, kwargs):
    print kwargs['score_string']