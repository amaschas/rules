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
  #TODO: add total lines member
  line_count = models.IntegerField(default=0)
  start_date = models.DateTimeField(blank=True, null=True)
  def __unicode__(self):
      return self.title

  def set_line_count(self, count):
    self.line_count = count
    self.save()


# TODO: track whether nicks are active (true on join or nick change or first seen, false on part or nick change)
# once we're tracking whether nicks are active, we can score lines read per nick
class Nick(models.Model):
  user = models.ForeignKey(User, blank=True, null=True)
  # need to run alter table rules_nick modify name varchar(100) collate utf8_bin; for case sensitivity
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
      return nick_string
      # try:
      #   nick = Nick.objects.get(name=nick_string)
      #   # log.info('nick exists, getting: %s', nick.name)
      # except ObjectDoesNotExist:
      #   nick = Nick(name=nick_string)
      #   try:
      #     nick.save()
      #     # log.info('adding nick: %s', nick.name)
      #   except IntegrityError:
      #     log.info('duplicate nick: %s', nick.name)
      #     pass
      # return nick
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
  def get_line(channel, line_index, pool=None):
    # Would a global pool lock?
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
  date = models.DateTimeField(blank=True, null=True)

  def increment_line_index(self):
    self.line_index += 1
    self.save()

  def set_date(self, date):
    self.date = date
    self.save()

  # Gets a line, checks for a date line, returns the formatted date or false otherwise
  @staticmethod
  def format_date_line(line):
    if re.match('\[00:00\] --- ', line):
      return datetime.strptime(line[12:], '%a %b %d %Y')
    else:
      return False