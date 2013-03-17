from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from signals import update_rules
from django.db.models.signals import post_init

class Rule(models.Model):
  RULE_STATUSES = (
      ('active', 'Actively Scoring'),
      ('scoring', 'Initial Scoring'),
      ('new', 'New')
  )
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  status = models.CharField(choices=RULE_STATUSES, max_length=20, default='new')
  def __unicode__(self):
      return self.name

  def score(self, **kwargs):
    return 'worked'

# TODO add a listener to the post_save signal that scores the entire channel against the rule
# needs to make sure that it accounts for modifications: delete all previous scores associated with rule and re-score


class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20)
  latest_line = models.BigIntegerField(default=0)
  def __unicode__(self):
      return self.title


class Score(models.Model):
  nick = models.ForeignKey(User)
  rule = models.ForeignKey(Rule)
  date = models.DateTimeField()
  line_id = models.BigIntegerField(default=0)


class Nick(models.Model):
  user = models.ForeignKey(User)
  name = models.CharField(max_length=100)