
import glob, re, redis, os, time
from collections import deque
from celery import Celery
from celery import group

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.conf import settings

from models import *
from lock import acquire_lock, release_lock, renew_lock

import logging
log = logging.getLogger(__name__)
hdlr = logging.FileHandler('/tmp/score.log')
log.addHandler(hdlr)
log.setLevel(logging.INFO)

# Might not need a backend
celery = Celery('rules', broker='amqp://guest:guest@localhost:5672//')


# scores a chunk of lines at a time to reduce concurrency overhead
@celery.task
def bulk_score(scores):
  scored = list()
  try:
    while scores:
      single_score = scores.popleft()
      # Get the number of matches, filtered for empty matches
      matches = len(filter(bool, re.findall(single_score['score']['rule'].rule, single_score['line'])))
      if matches:
        scored.append(Score(rule=single_score['score']['rule'], nick=single_score['score']['nick'], channel=single_score['score']['channel'], date=single_score['score']['date'], line_index=single_score['score']['line_index'], score=matches))
  except IndexError:
    pass

  Score.objects.bulk_create(single_score for single_score in scored)


# Using a receiver function here instead of directly calling update_channel so update_channel can remain generalized
@receiver(post_save, sender=Channel)
def update_channel_save_trigger(sender, **kwargs):
  if kwargs['created']:
    try:
      update_channel.delay(kwargs['instance'])
    except ObjectDoesNotExist:
      pass


# TODO use BATCH_SIZE in settings here?
# Scores the rule against every active channel
@celery.task
def update_rule(rule, batch_size=50000):
  print 'starting score'
  identifier = str(uuid.uuid4())
  lockname = 'rule-%s-scoring' % rule.id
  if acquire_lock(lockname, identifier) == identifier:

    try:
      channels = Channel.objects.filter()
      for channel in channels:
        try:
          score_meta = ScoreMeta.objects.get(rule=rule, channel=channel)
        except ObjectDoesNotExist:
          score_meta = ScoreMeta(rule=rule, channel=channel, line_index=0)
          score_meta.save()

        # Create list of redis keys keyed by line index
        # line_index = 0
        # redis_keys = list()
        # while line_index < score_meta.channel.line_count:
        #   redis_keys.append('-'.join([channel.slug, str(line_index)]))
        #   line_index += 1

        # print redis_keys

        # Using a redis pipline here to batch the redis get queries and reduce overhead per query
        pool = redis.ConnectionPool(host='localhost', port=6379, db=channel.redis_db)
        r = redis.Redis(connection_pool=pool)
        pipe = r.pipeline()

        # Using deque for speed, though I'm not sure the gains are noticeable
        score_queue = deque()

        # Creating local variables in most cases, though I'm not sure it results in speed gains as long as I avoid saving score_meta
        index = score_meta.line_index
        line_indexes = deque()

        # Get all the nicks up front, so we're searching a dict rather than querying the DB for each iterration
        nicks = dict()
        for nick in Nick.objects.all():
          nicks[nick.name] = nick

        while index < channel.line_count:
          # Store the lines for the current batch
          line_indexes.appendleft(index)

          pipe.hgetall('-'.join([channel.slug, str(index)]))
          # pipe.hgetall(redis_keys[index])

          if index % batch_size == 0 and index > 0 or index == channel.line_count - 1:
            
            # Renewing the lock every batch
            # Might be a better way to do this, probably worth bumping the batch size
            renew_lock(lockname, identifier)

            # Get all batched lines
            lines = pipe.execute()

            for line in lines:
              # Get the current line from the stores array of batch lines
              current_line = line_indexes.pop()
              try:
                score_queue.appendleft({'score' : {'rule' : rule, 'nick' : nicks[line['nick']], 'channel' : channel, 'date' : line['date'], 'line_index' : current_line}, 'line' : line['line']})
              except KeyError:
                pass

            bulk_score.delay(deque(score_queue))
            score_queue.clear()
            score_meta.line_index = index
            score_meta.save()

          index += 1

        score_meta.line_index = index
        score_meta.save()


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
    update_rule.delay(rule=kwargs['instance'])
