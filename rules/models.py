import re, time, redis
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_init
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.db import IntegrityError

import tasks
from lock import unlock

import logging
log = logging.getLogger(__name__)

class StatusHandler(models.Model):
  STATUSES = (
    ('active', 'Active'),
    ('scoring', 'Scoring'),
    ('new', 'New')
  )
  status = models.CharField(choices=STATUSES, max_length=20, default='new')
  class Meta:
        abstract = True

  def set_active(self):
    if self.status != 'active':
      self.status = 'active';
      self.save()

  def set_scoring(self):
    if self.status != 'scoring':
      self.status = 'scoring'
      self.save()

class Rule(StatusHandler):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  def __unicode__(self):
      return self.name

  # TODO I want to stick this in StatusHandler, but importing tasks is weird
  def save(self, *args, **kwargs):
    if self.id == None:
      super(Rule, self).save(*args, **kwargs)
      tasks.score_rule_from_index.delay(self)
    else:
      super(Rule, self).save(*args, **kwargs)


class Channel(StatusHandler):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20, unique=True)
  redis_db = models.IntegerField(default=0)
  current_line = models.IntegerField(default=0)
  start_date = models.DateTimeField(blank=True, null=True)
  current_date = models.DateTimeField(blank=True, null=True)
  def __unicode__(self):
      return self.title

  # TODO I want to stick this in StatusHandler, but importing tasks is weird
  def save(self, *args, **kwargs):
    if self.id == None:
      self.current_date = self.start_date
      super(Channel, self).save(*args, **kwargs)
      tasks.score_channel_from_index.delay(self)
    else:
      super(Channel, self).save(*args, **kwargs)

  # Gets a line, checks for a date line, returns the formatted date or false otherwise
  @staticmethod
  def format_date_line(line):
    if re.match('\[00:00\] --- ', line):
      return datetime.strptime(line[12:], '%a %b %d %Y')
    else:
      return False

  # Gets a line number, updates self.current_line if the value is an integer
  def set_current_line(self, line_number):
    self.current_line = line_number
    self.save()

  def set_current_date(self, date):
    self.current_date = date
    self.save()

  def reset(self):
    self.set_current_line(0)
    self.set_current_date(self.start_date)

  def update(self, line_index):
    line = Score.get_line(self, line_index)
    if line:
      if line_index <= self.current_line:
        pass
      else:
        self.set_current_line(line_index)
        date = Channel.format_date_line(line)
        if date:
          self.set_current_date(date)
        else:
          tasks.score_rules.delay(channel=self, line_index=self.current_line, date=self.current_date, line=line)
      self.update(line_index + 1)
    else:
      pass
      # Unlock the channel for scoring when there are no more lines to score
      # unlock('%s-scoring' % self.slug)
    return


class Nick(models.Model):
  user = models.ForeignKey(User, blank=True, null=True)
  name = models.CharField(max_length=100, unique=True)
  def __unicode__(self):
    return self.name

  # Gets or creates a nick object from a line
  @staticmethod
  def get_nick(line):

    #[a-zA-Z0-9\_\-\\\[\]\{\}\^\`\|]
    # Regex to match irc nick strings
    nick_regex_string = '[a-zA-Z0-9_-\{\}\^\`\|]+'

    # Cut off timestamp
    line = line[8:]

    # Match strings for irc line types
    regex_strings = [
      '<(?P<nick>%s)>' % nick_regex_string,
      'Action: (?P<nick>%s) ' % nick_regex_string,
      'Nick change: (?P<nick>%s) ' % nick_regex_string,
      'Topic changed on [#&][[a-zA-Z0-9]+ by (?P<nick>%s)\!' % nick_regex_string,
      '%s kicked from [#&][[a-zA-Z0-9]+ by (?P<nick>%s)' % (nick_regex_string, nick_regex_string),
      '(?P<nick>%s) \(.*\) [left|joined]' % nick_regex_string,
      '[#&][[a-zA-Z0-9]+: mode change \'.*\' by (?P<nick>%s)\!' % nick_regex_string
    ]

    nick_string = ''
    # Search for nick in line using each match pattern
    for regex_string in regex_strings:
      nick_match = re.match(regex_string, line)
      if nick_match:
        nick_string = nick_match.group('nick')

    # If nick string exists, either create or return existing, otherwise return False
    if nick_string:
      try:
        nick = Nick.objects.get(name=nick_string)
        # log.debug('nick exists, getting: %s', nick.name)
      except ObjectDoesNotExist:
        nick = Nick(name=nick_string)
        nick.save()
        # log.debug('adding nick: %s', nick.name)
      return nick
    else:
      return False

class Score(models.Model):
  nick = models.ForeignKey(Nick)
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  date = models.DateTimeField()
  line_index = models.IntegerField(default=0)
  score = models.IntegerField(default=1)

  # Gets any line for any channel
  @staticmethod
  def get_line(channel, line_index):
    r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)
    line = r.get('%s-%d' % (channel.slug, line_index))
    if line:
      return line
    else:
      return False

  # Gets own line
  def line(self):
    return Score.get_line(self.channel, self.line_index)


