from celery import Celery
from celery import group
import glob
import re

from models import Rule
from signals import update_rules

celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')

# need thi'score_rules'# @celery.task
# def nick_scan

@celery.task
def score_rules(channel_slug):
  rules = Rule.objects.all()
  g = group(score.s(rule) for rule in rules)
  g.apply_async()

@celery.task
def score(rule):
  return rule.score()