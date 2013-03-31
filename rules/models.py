import re, time, redis
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_init
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.db import IntegrityError

import logging
log = logging.getLogger(__name__)


STATUSES = (
  ('active', 'Actively Scoring'),
  ('scoring', 'Initial Scoring'),
  ('new', 'New')
)

class Rule(models.Model):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  status = models.CharField(choices=STATUSES, max_length=20, default='new')
  def __unicode__(self):
      return self.name

  # TODO might be able to get rid of the score arg
  def save(self, score=False, *args, **kwargs):
    # log.debug('rule save started')
    # log.debug(self.id)
    # log.debug(score)
    if score or self.id == None:
      # log.debug('rule saving - will score')
      super(Rule, self).save(*args, **kwargs)
      from tasks import score_rule_from_index
      score_rule_from_index.delay(self)
    else:
      # log.debug('rule saving - will not score')
      super(Rule, self).save(*args, **kwargs)


class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20, unique=True)
  redis_db = models.IntegerField(default=0)
  current_line = models.IntegerField(default=0)
  start_date = models.DateTimeField(blank=True, null=True)
  current_date = models.DateTimeField(blank=True, null=True)
  status = models.CharField(choices=STATUSES, max_length=20, default='new')
  def __unicode__(self):
      return self.title

  # TODO might be able to get rid of the score arg
  def save(self, score=False, *args, **kwargs):
    # log.debug('rule save started')
    # log.debug(self.id)
    # log.debug(score)
    if score or self.id == None:
      # log.debug('rule saving - will score')
      super(Channel, self).save(*args, **kwargs)
      from tasks import score_channel_from_index
      score_channel_from_index.delay(self)
    else:
      # log.debug('rule saving - will not score')
      super(Channel, self).save(*args, **kwargs)

  # Gets a line, checks for a date line, returns the formatted date or false otherwise
  @staticmethod
  def format_date_line(line):
    if re.match('\[00:00\] --- ', line):
      return datetime.strptime(line[12:], '%a %b %d %Y')
    else:
      return False

  # Gets a line number, updates self.current_line if the value is an integer
  def update_current_line(self, line_number):
    try:
      self.current_line = line_number
      self.save()
      return True
    except ValueError:
      return False

  # Gets a line, checks for a date with format_date_line(), updates self.current_date if it finds a date
  def update_current_date(self, line, *args, **kwargs):
    date = Channel.format_date_line(line)
    if date:
      self.current_date = date
      self.save()
      return True
    else:
      #TODO if the line has a timestamp, add the time to the current date
      return False


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


