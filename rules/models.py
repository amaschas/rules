import re
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_init
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save


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

  # Gets a line and a channel slug, score the line against the rule, for the channel
  # TODO this needs to receive the line number and date, so as not to rely on the channel model for state
  def score(self, line, channel, date, line_index, *args, **kwargs):
    # print 'actually scoring'
    nick = Nick.get_nick(line)
    if nick:
      # Score line minus timestamp
      if re.search(self.rule, line[8:]):
        print 'scoring line %d' % line_index
        score = Score(nick=nick, rule=self, channel=channel, date=date, line_id=line_index)
        score.save()
        return True
    return False

# post_save.connect(rule_score_receiver, sender=Rule)
@receiver(post_save, sender=Rule)
def rule_score_receiver(sender, **kwargs):
  from tasks import initial_rule_score
  print kwargs
  try:
    if 'rule' in kwargs['update_fields']:
      print 'starting scoring rule - rule changed'
      initial_rule_score.delay(kwargs['instance'])
  except TypeError:
    if kwargs['created']:
      print 'starting scoring rule - created'
      initial_rule_score.delay(kwargs['instance'])
    else:
      print 'ignoring score run'
      pass


class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20, unique=True)
  redis_db = models.IntegerField(default=0)
  current_line = models.BigIntegerField(default=0)
  start_date = models.DateTimeField(blank=True, null=True)
  current_date = models.DateTimeField(blank=True, null=True)
  status = models.CharField(choices=STATUSES, max_length=20, default='new')
  def __unicode__(self):
      return self.title

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
      return False

# post_save.connect(channel_score_receiver, sender=Channel)
@receiver(post_save, sender=Channel)
def channel_score_receiver(sender, **kwargs):
  try:
    if 'status' in kwargs['update_fields']:
      pass
  except TypeError:
    if kwargs['created']:
      pass
    else:
      return
  print 'starting scoring channel'
  from tasks import initial_channel_score
  initial_channel_score.delay(kwargs['instance'])


class Nick(models.Model):
  user = models.ForeignKey(User, blank=True, null=True)
  name = models.CharField(max_length=100, unique=True)

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
      except ObjectDoesNotExist:
        nick = Nick(name=nick_string)
        nick.save()
      return nick
    else:
      return False

class Score(models.Model):
  nick = models.ForeignKey(Nick)
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  date = models.DateTimeField()
  line_id = models.BigIntegerField(default=0)
