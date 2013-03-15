from django.db import models
from django.contrib.auth.models import User

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

  def score(self, line):
    print line

  # def get_user_from_nick(line):

class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20)
  start_date = models.DateTimeField()
  # total_lines_scored = models.BigIntegerField(default=0)
  log_path = models.FilePathField(path="/Users/alexi/Desktop", max_length=200)
  #might need these
  current_log_file = models.CharField(max_length=100)
  current_log_position = models.BigIntegerField(default=0)
  current_log_count = models.BigIntegerField(default=0)


# Each line score is a single entry, which will allow us to graph
class Score(models.Model):
  nick = models.ForeignKey(User)
  rule = models.ForeignKey(Rule)
  date = models.DateTimeField()

class Nick(models.Model):
  user = models.ForeignKey(User)
  name = models.CharField(max_length=100)