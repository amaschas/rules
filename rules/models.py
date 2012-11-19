from django.db import models
from django.contrib.auth.models import User

class Rule(models.Model):
  creator = models.ForeignKey(User)
  name = models.CharField(max_length=100)
  rule = models.CharField(max_length=100)

class Nick(models.Model):
  user = models.ForeignKey(User)
  name = models.CharField(max_length=100)