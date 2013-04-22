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


# Using a receiver function here instead of directly calling update_channel so update_channel can remain generalized
@receiver(post_save, sender=Channel)
def update_channel_save_trigger(sender, **kwargs):
  if kwargs['created']:
    try:
      rules = Rule.objects.filter()
      g = group(update_rule.s(rule=rule) for rule in rules)
      g.apply_async()
    except ObjectDoesNotExist:
      pass


# Scores the rule against every active channel, starting at index
@celery.task
def update_rule(rule):
  print 'starting score'
  identifier=str(uuid.uuid4())
  if acquire_lock('rule-%s-scoring' % rule.id, identifier, 60) == identifier:
    try:
      channels = Channel.objects.filter()
      for channel in channels:
        try:
          score_meta = ScoreMeta.objects.get(rule=rule, channel=channel)
        except ObjectDoesNotExist:
          score_meta = ScoreMeta(rule=rule, channel=channel, line_index=0, date=channel.start_date)
          score_meta.save()
        line = Score.get_line(channel, score_meta.line_index)
        while line:
          line_date = ScoreMeta.format_date_line(line)
          if line_date:
            score_meta.set_date(line_date)
          else:
            nick = Nick.get_nick(line)
            if nick:
              score.delay(Score(rule=rule, nick=nick, channel=channel, date=score_meta.date, line_index=score_meta.line_index), line=line)
          score_meta.increment_line_index()
          line = Score.get_line(channel, score_meta.line_index)
    except ObjectDoesNotExist:
      pass
    print 'ending score'
    release_lock('rule-%s-scoring' % rule.id, identifier)
  else:
    print '%s update locked' % rule.name


# Using a receiver function here instead of directly calling update_rule so update_rule can remain generalized
@receiver(post_save, sender=Rule)
def update_rule_save_trigger(sender, **kwargs):
  if kwargs['created']:
    update_rule.delay(channel=kwargs['instance'], index=0)
