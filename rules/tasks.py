import glob, re, redis
from celery import Celery
from celery import group

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save

from models import *
from lock import acquire_lock, release_lock

# import logging
# log = logging.getLogger(__name__)

# Might not need a backend
celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')

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

# TODO: can line_index be in kwargs?
@celery.task
def update_channel(channel, line_index):
  identifier=str(uuid.uuid4())
  if acquire_lock('%s-scoring' % channel.slug, identifier) == identifier:
    line = Score.get_line(channel, line_index)

    while line:
      if line_index <= channel.current_line:
        pass
      else:
        channel.set_current_line(line_index)
        date = Channel.format_date_line(line)
        if date:
          channel.set_current_date(date)
        else:
          nick = Nick.get_nick(line)
          if nick:
            try:
              rules = Rule.objects.filter(status='active')
              g = group(score.s(Score(rule=rule, nick=nick, channel=channel, date=channel.current_date, line_index=channel.current_line), line=line) for rule in rules)
              g.apply_async()
            except ObjectDoesNotExist:
              pass

      line_index = channel.current_line + 1
      line = Score.get_line(channel, line_index)

    release_lock('%s-scoring' % channel.slug, identifier)
  else:
    print 'update locked'

# Might be better to avoid the monkey patch, use the displatcher response method for the signal
# allows me to segment the code for triggering only on initial save, while also letting me pass index more easily, probably
# post_save.connect(update_channel.delay, sender=Channel)


# Scores the rule against every active channel, starting at index
@celery.task
def update_rule(rule, index=0):
  identifier=str(uuid.uuid4())
  if acquire_lock('rule-%s-scoring' % rule.id, identifier) == identifier:
    try:
      channels = Channel.objects.filter(status='active')

      # Delete all previous scores for this rule from index on
      Score.objects.filter(rule=rule, line_index__gte=index).delete()

      for channel in channels:
        date = channel.start_date
        line_index = index

        line = Score.get_line(channel, line_index)
        while line:
          line_date = Channel.format_date_line(line)
          if line_date:
            date = line_date
          else:
            nick = Nick.get_nick(line)
            if nick:
              score.delay(Score(rule=rule, nick=nick, channel=channel, date=date, line_index=line_index), line=line)
          line_index += 1
          line = Score.get_line(channel, line_index)
    except ObjectDoesNotExist:
      pass
    release_lock('rule-%s-scoring' % rule.id, identifier)
  else:
    print 'update locked'
