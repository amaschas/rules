from django.db import models
from django import forms
from django.forms import ModelForm

from models import *

class ClaimNickForm(forms.ModelForm):
  def __init__(self, *args, **kwargs):
    super(ClaimNickForm, self).__init__(*args, **kwargs)
    self.fields['user'].widget = forms.HiddenInput()
    self.fields['disputed'].widget = forms.HiddenInput()
    self.fields['disputer'].widget = forms.HiddenInput()
  class Meta:
    model = Nick
    exclude = ('name', 'first_seen')


class ChannelForm(forms.ModelForm):
  class Meta:
    model = Channel


class RuleForm(forms.ModelForm):
  def __init__(self, *args, **kwargs):
    super(RuleForm, self).__init__(*args, **kwargs)
    self.fields['creator'].widget = forms.HiddenInput()
    self.fields['name'] = forms.CharField(widget=forms.TextInput(attrs=dict(placeholder='Rule Name')))
    self.fields['rule'] = forms.CharField(widget=forms.TextInput(attrs=dict(placeholder='Rule Regex')))
  class Meta:
    model = Rule
    exclude = ('status',)