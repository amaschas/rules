from celery import Celery
from celery import group
import glob
import re

from models import Rule

# Might not need a backend
celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')

# Compiles a task group for all active rules, executes the group
@celery.task
def score_rules(channel_slug, line):
  # This should only get active rules
  rules = Rule.objects.all()
  g = group(score.s(rule, line, channel_slug) for rule in rules)
  g.apply_async()


# Receives a rule, line and channel slug, calls score on the rule instance with the parameters
@celery.task
def score(rule, line, channel_slug):
  return rule.score(line, channel_slug)


# Called from save() on Rule, scores every line of every channel against the rule, sets rule status appropriately
@celery.task
def initial_rule_score(rule):
  channels = Channel.objects.all()

  # Rule is now scoring
  rule.status = 'scoring'
  rule.save()
  for channel in channels:
    date = channel.start_date
    line_index = 0
    r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)

    # For every line in the channel, call the score task
    line = r.get('%s-%d' % (channel.slug, line_index))
    while line:
      score.delay(rule, line, channel.slug)
      line_index += 1
      line = r.get('%s-%d' % (channel.slug, line_index))

  # Finished initial scoring rule, set it active to register with score_rules()
  rule.state = 'active'
  rule.save()
