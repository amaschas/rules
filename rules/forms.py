from django.db import models
from django import forms
from django.forms import ModelForm

from models import *

class NickForm(forms.ModelForm):
  class Meta:
    model = Nick
    # exclude = ('source','description')

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
    # exclude = ('source','description')