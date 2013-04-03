import glob, re, redis
from celery import Celery
from celery import group

from django.core.exceptions import ObjectDoesNotExist

import models

import logging
log = logging.getLogger(__name__)

# Might not need a backend
celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')


# Compiles a task group for all active rules, executes the group
@celery.task
def score_rules(channel, line_index, nick, date, line):
  return
  try:
    rules = models.Rule.objects.filter(status='active')
    g = group(score.s(models.Score(rule=rule, nick=nick, channel=channel, date=date, line_index=line_index), line=line) for rule in rules)
    g.apply_async()
  except ObjectDoesNotExist:
    pass


# Receives a rule, line and channel slug, calls score on the rule instance with the parameters
@celery.task
def score(score, line):
  # log.debug('testing line %d - %s' % (score.line_index, line))
  matches = len(re.findall(score.rule.rule, line))
  if matches:
    # print '%d - %s' % (matches, line)
    score.score = matches
    score.save()
    return True
  else:
    return False


# Scores the rule against every active channel, starting at index
@celery.task
def score_rule_from_index(rule, index=0):
  try:
    channels = models.Channel.objects.filter(status='active')

    log.debug('initial_rule_score started')

    # Delete all previous scores for this rule
    models.Score.objects.filter(rule=rule, line_index__gte=index).delete()

    # Rule set status to scoring to avoid double scoring from new line events
    rule.status = 'scoring'
    rule.save()

    # TODO use a task group for this
    for channel in channels:
      date = channel.start_date
      line_index = index
      r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)

      # For every line in the channel, call the score task
      line = r.get('%s-%d' % (channel.slug, line_index))
      while line:
        line_date = models.Channel.format_date_line(line)
        if line_date:
          date = line_date
        else:
          nick = models.Nick.get_nick(line)
          if nick:
            score.delay(models.Score(rule=rule, nick=nick, channel=channel, date=date, line_index=line_index), line=line)
        line_index += 1
        line = r.get('%s-%d' % (channel.slug, line_index))

    # Finished scoring rule, set it active to register with score_rules()
    rule.status = 'active'
    rule.save()

    log.debug('initial_rule_score finished')
  except ObjectDoesNotExist:
    log.debug('no active channels')
    pass


# Scores the channel against every active rule, starting at index
@celery.task
def score_channel_from_index(channel, index=0):
  channel.update(index)
