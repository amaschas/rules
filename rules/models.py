import re, time, redis, uuid
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_init
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.db import IntegrityError

from lock import acquire_lock, release_lock

import logging
log = logging.getLogger(__name__)

class Rule(models.Model):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  def __unicode__(self):
      return self.name


class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20, unique=True)
  redis_db = models.IntegerField(default=1)
  line_count = models.IntegerField(default=0)
  start_date = models.DateTimeField(blank=True, null=True)
  def __unicode__(self):
      return self.title

  def set_line_count(self, count):
    self.line_count = count
    self.save()

  def get_latest_date(self):
    latest_score = Score.objects.filter(channel=self).latest('date')
    if latest_score:
      return latest_score.date
    else:
      return False

# TODO: track whether nicks are active (true on join or nick change or first seen, false on part or nick change)
# once we're tracking whether nicks are active, we can score lines read per nick
class Nick(models.Model):
  user = models.ForeignKey(User, blank=True, null=True)
  # need to run alter table rules_nick modify name varchar(100) collate utf8_bin; for case sensitivity
  name = models.CharField(max_length=100, unique=True)
  def __unicode__(self):
    return self.name


class Score(models.Model):
  nick = models.ForeignKey(Nick)
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  date = models.DateTimeField()
  line_index = models.IntegerField(default=0)
  score = models.IntegerField(default=1)

  # Gets any line for any channel
  @staticmethod
  def get_line(channel, line_index, pool=None):
    if pool:
     r = redis.Redis(connection_pool=pool)
    else:
      r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)
    line = r.get('%s-%d' % (channel.slug, line_index))
    if line:
      return line
    else:
      return False

  # Gets own line
  def line(self):
    return Score.get_line(self.channel, self.line_index)


class ScoreMeta(models.Model):
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  line_index = models.IntegerField(default=0)

  def increment_line_index(self):
    self.line_index += 1
    self.save()

  def set_date(self, date):
    self.date = date
    self.save()