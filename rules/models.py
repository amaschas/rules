import re
from datetime import datetime
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

  # Invokes the initial rule scoring task after save
  def save(self, *args, **kwargs):
    super(Rule, self).save(*args, **kwargs)
    initial_rule_score.delay(self)

  # Gets a line and a channel slug, score the line against the rule, for the channel
  def score(self, line, channel_slug, *args, **kwargs):
    nick = Nick.get_nick(line)
    if nick:
      if re.search(self.rule, line[7:]):
        channel = Channel.objects.get(slug=channel_slug)
        score = Score(nick=nick, rule=self, channel=channel, date=channel.current_date, line_id=channel.current_line)
        score.save()
        return True
    return False


class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20)
  redis_db = models.IntegerField(default=0)
  current_line = models.BigIntegerField(default=0)
  start_date = models.DateTimeField(blank=True, null=True)
  current_date = models.DateTimeField(blank=True, null=True)
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


class Score(models.Model):
  nick = models.ForeignKey(User)
  rule = models.ForeignKey(Rule)
  channel = models.ForeignKey(Channel)
  date = models.DateTimeField()
  line_id = models.BigIntegerField(default=0)


class Nick(models.Model):
  user = models.ForeignKey(User, blank=True, null=True)
  name = models.CharField(max_length=100)

  # Gets a line, checks for a variety of line beginnings, matches and grabs the nick from the appropriate pattern, creates a nick if it doesn't already exist, grabs it if it does, returns nick or false otherwise
  @staticmethod
  def get_nick(line):

    # Standard line /[.*] <.*>/

    # [.*] Action: <nick>

    # [.*] Nick change: <nick>

    # [.*] Nick change: <nick>

    # join/leave?
    # [11:25] Charon (~nschmidt@74.63.52.2) left irc: Ping timeout: 180 seconds
    # [11:59] Charon (~nschmidt@74.63.52.2) joined #avara.

    # mode change: [.*] #<channel_slug>, or just the #
    # #avara: mode change '+o Charon' by jonah!~alek@ly.sine.com

    # kicks
    # fet kicked from #avara by jake

    # topic change
    # Topic changed on #avara by m!maschas@ur.sine.com: can a bear get breast cancer?

    # nick change
    # Nick change: vetere -> drsmokey

    #ignore all else

    pass
