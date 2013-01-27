from django.db import models
from django.contrib.auth.models import User

class Rule(models.Model):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)
  def __unicode__(self):
      return self.name

class Score(models.Model):
  user = models.ForeignKey(User)
  rule = models.ForeignKey(Rule)
  score = models.IntegerField()

class Nick(models.Model):
  user = models.ForeignKey(User)
  name = models.CharField(max_length=100)