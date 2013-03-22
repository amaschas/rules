from celery import Celery
from celery import group
import glob, re, redis

from django.core.exceptions import ObjectDoesNotExist

from models import *

import logging
log = logging.getLogger(__name__)

# Might not need a backend
celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')

# Compiles a task group for all active rules, executes the group
@celery.task
def score_rules(channel, line, nick):
  try:
    rules = Rule.objects.get(status='active')
    g = group(score.s(rule=rule, line=line, nick=nick, channel=channel, date=channel.current_date, line_index=channel.current_line) for rule in rules)
    g.apply_async()
  except ObjectDoesNotExist:
    pass


# Receives a rule, line and channel slug, calls score on the rule instance with the parameters
@celery.task
def score(rule, line, nick, channel, date, line_index):
  return rule.score(line=line, nick=nick, channel=channel, date=date, line_index=line_index)


# Called from save() on Rule, scores every line of every channel against the rule, sets rule status appropriately
@celery.task
def initial_rule_score(rule):
  try:
    channels = Channel.objects.filter(status='active')

    log.debug('initial_rule_score started')

    # Delete all previous scores for this rule
    Score.objects.filter(rule=rule).delete()

    # Rule set status to scoring to avoid double scoring from new line events
    rule.status = 'scoring'
    rule.save()
    for channel in channels:
      date = channel.start_date
      line_index = 0
      r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)

      # For every line in the channel, call the score task
      line = r.get('%s-%d' % (channel.slug, line_index))
      while line:
        line_date = Channel.format_date_line(line)
        if line_date:
          date = line_date
        else:
          nick = Nick.get_nick(line)
          if nick:
            score.delay(rule=rule, line=line, nick=nick, channel=channel, date=date, line_index=line_index)
        line_index += 1
        line = r.get('%s-%d' % (channel.slug, line_index))

    # Finished initial scoring rule, set it active to register with score_rules()
    rule.status = 'active'
    rule.save()

    log.debug('initial_rule_score finished')
  except ObjectDoesNotExist:
    print 'no active channels'
    pass

# Called from save() on Channel, scores every line of channel against every rule, sets channel status appropriately
@celery.task
def initial_channel_score(channel):
  # try:
  rules = Rule.objects.filter(status='active')

  # Channel is now scoring
  channel.status = 'scoring'
  channel.save(update_fields=['status'])
  date = channel.start_date
  line_index = 0
  r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)

  # For every line in the channel, call the score task
  # TODO: this needs to score every rule against a line, rather than scoring every line against a rule, and then moving to another rule
  line = r.get('%s-%d' % (channel.slug, line_index))
  while line:
    line_date = Channel.format_date_line(line)
    if line_date:
      date = line_date
    else:
      nick = Nick.get_nick(line)
      if nick:
        for rule in rules:
          score.delay(rule=rule, line=line, nick=nick, channel=channel, date=date, line_index=line_index)
    line_index += 1
    line = r.get('%s-%d' % (channel.slug, line_index))

  # Finished initial scoring channel, set it active to register with score_rules()
  channel.status = 'active'
  channel.save(update_fields=['status'])
  # except ObjectDoesNotExist:
  #   print 'blah'
  #   pass
