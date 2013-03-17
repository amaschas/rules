from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from signals import update_rules
from django.db.models.signals import post_init

class Rule(models.Model):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  def __unicode__(self):
      return self.name

  def save(self, *args, **kwargs):
    super(Rule, self).save(*args, **kwargs)
    print 'saving'
    for channel in Channel.objects.all():
      channel_rule_meta = ChannelRuleMeta(rule=self, channel=channel)
      channel_rule_meta.save()

  def score(self, **kwargs):
    return 'worked'

# TODO add a listener to the post_save signal that scores the entire channel against the rule
# needs to make sure that it accounts for modifications: delete all previous scores associated with rule and re-score


class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20)
  redis_db = models.IntegerField(default=0)
  def __unicode__(self):
      return self.title

class ChannelRuleMeta(models.Model):
  RULE_STATUSES = (
      ('active', 'Actively Scoring'),
      ('scoring', 'Initial Scoring'),
      ('new', 'New')
  )
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  status = models.CharField(choices=RULE_STATUSES, max_length=20, default='new')
  current_line = models.BigIntegerField(default=0)
  current_date = models.DateTimeField(blank=True, null=True)


class Score(models.Model):
  nick = models.ForeignKey(User)
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  date = models.DateTimeField()
  line_id = models.BigIntegerField(default=0)


class Nick(models.Model):
  user = models.ForeignKey(User, blank=True, null=True)
  name = models.CharField(max_length=100)