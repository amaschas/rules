from django.db import models
from django import forms
from django.forms import ModelForm

from models import *

class TestForm(forms.Form):
  choices = (
    ('delete-channels', 'Delete all channels'),
    ('delete-rules', 'Delete all rules'),
    ('delete-nicks', 'Delete all nicks'),
    ('delete-scores', 'Delete all scores'),
    ('score-channels', 'Initial score channels'),
    ('score-rules', 'Initial score rules'),
  )
  choices = forms.fields.MultipleChoiceField(label='test', choices=(choices), widget=forms.CheckboxSelectMultiple())

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
    exclude = ('status',)

# TODO: I think this is going to need a custom view and form
class RuleUpdateForm(RuleForm):
  def __init__(self, *args, **kwargs):
    super(RuleUpdateForm, self).__init__(*args, **kwargs)
    del self.fields['creator']

    def save(self, *args, **kwargs):
      print 'saving'
      # kwargs['instance'].save(update_fields=['name', 'rule'])
      # super(RuleUpdateForm, self).__init__(*args, **kwargs)
