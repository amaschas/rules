from celery import Celery
from celery import group
import glob, re, redis

from django.core.exceptions import ObjectDoesNotExist

from models import *

import logging
log = logging.getLogger(__name__)

# Might not need a backend
celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')

# TODO this might not be necessary anymore
# Compiles a task group for all active rules, executes the group
@celery.task
def score_rules(channel, line, nick):
  log.debug('compiling rule score tasks')
  try:
    rules = Rule.objects.filter(status='active')
    print rules
    g = group(score.s(Score(rule=rule, nick=nick, channel=channel, date=channel.current_date, line_index=channel.current_line), line=line) for rule in rules)
    g.apply_async()
  except ObjectDoesNotExist:
    pass


# Receives a rule, line and channel slug, calls score on the rule instance with the parameters
@celery.task
def score(score, line):
  # log.debug('testing line %d - %s' % (score.line_index, line))
  matches = len(re.findall(score.rule.rule, line))
  if matches:
    print '%d - %s' % (matches, line)
    score.score = matches
    score.save()
    return True
  else:
    return False


# Scores the rule against every active channel, starting at index
@celery.task
def score_rule_from_index(rule, index=0):
  try:
    channels = Channel.objects.filter(status='active')

    log.debug('initial_rule_score started')

    # Delete all previous scores for this rule
    Score.objects.filter(rule=rule, line_index__gte=index).delete()

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
        line_date = Channel.format_date_line(line)
        if line_date:
          date = line_date
        else:
          nick = Nick.get_nick(line)
          if nick:
            score.delay(Score(rule=rule, nick=nick, channel=channel, date=date, line_index=line_index), line=line)
        line_index += 1
        line = r.get('%s-%d' % (channel.slug, line_index))

    # Finished scoring rule, set it active to register with score_rules()
    rule.status = 'active'
    rule.save()

    log.debug('initial_rule_score finished')
  except ObjectDoesNotExist:
    log.debug('no active channels')
    pass

# def test(index):
#   testing = Score.objects.filter(channel=15, line_index__gte=index)
#   for score in testing:
#     print score.line_index

# Scores the channel against every active rule, starting at index
@celery.task
def score_channel_from_index(channel, index=0):
  try:
    Score.objects.filter(channel=channel, line_index__gte=index).delete()
    rules = Rule.objects.filter(status='active')

    # Channel is now scoring
    channel.status = 'scoring'
    channel.save()
    date = channel.start_date
    line_index = index
    r = redis.Redis(host='localhost', port=6379, db=channel.redis_db)

    # For every line in the channel, call the score task
    line = r.get('%s-%d' % (channel.slug, line_index))

    #TODO: channel counter gets incremented one too many times (I think this is fixed now)
    while line:
      # TODO I think I can get rid of line_index and just use channel.current_line
      channel.update_current_line(line_index)
      if not channel.update_current_date(line):
        # TODO get the timestamp from the post, add it to current_date, and use it
        # something like datetime.strptime(channel date stuff + split timestamp, '%a %b %d %Y blah blah')
        nick = Nick.get_nick(line)
        if nick:
          # could just use score_rules here
          # score_rules.delay(channel=channel, line=line, nick=nick)
          for rule in rules:
            score.delay(Score(rule=rule, nick=nick, channel=channel, date=channel.current_date, line_index=line_index), line=line)
      line_index += 1
      line = r.get('%s-%d' % (channel.slug, line_index))
      # print line

    # Finished scoring channel, set it active to register with score_rules()
    channel.status = 'active'
    channel.save()
  except ObjectDoesNotExist:
    pass
    #TODO: If there are no active rules, channel should get current_line and current_date anyway
