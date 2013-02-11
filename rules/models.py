from django.db import models
from django.contrib.auth.models import User

class Rule(models.Model):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  def __unicode__(self):
      return self.name

  def score(line):
    print line

class Channel(models.Model):
  title = models.CharField(max_length=100)
  slug = models.CharField(max_length=20)
  log_path = models.FilePathField(path="/Users/alexi/Desktop", max_length=200)
  current_log_position = models.BigIntegerField(default=0)
  total_lines_scored = models.BigIntegerField(default=0)

class Score(models.Model):
  SCORE_STATUSES = (
      ('active', 'Actively Scoring'),
      ('scoring', 'Initial Scoring'),
      ('new', 'New')
  )
  user = models.ForeignKey(User)
  rule = models.ForeignKey(Rule)
  score = models.BigIntegerField(default=0)
  status = models.CharField(choices=SCORE_STATUSES, max_length=20, default='new')

class Nick(models.Model):
  user = models.ForeignKey(User)
  name = models.CharField(max_length=100)