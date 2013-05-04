import glob, re, redis, os, time
from collections import deque
from celery import Celery
from celery import group

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.conf import settings

from models import *
from lock import acquire_lock, release_lock, renew_lock

# import logging
# log = logging.getLogger(__name__)

# Might not need a backend
celery = Celery('rules', broker='amqp://guest:guest@localhost:5672//')


# scores a chunk of lines at a time to reduce concurrency overhead
@celery.task
def bulk_score(scores):
  print 'bulk scoring'
  scored = list()
  try:
    while scores:
      single_score = scores.popleft()

      # single_score = scores.pop()
      matches = len(re.findall(single_score['score']['rule'].rule, single_score['line']))
      if matches:
        print 'test'
        print single_score['score']
        # date = time.strptime(single_score['score']['date'], '%Y-%m-%d %H:%M:%S')
        # print date
        scored.append(Score(rule=single_score['score']['rule'], nick=single_score['score']['nick'], channel=single_score['score']['channel'], date=single_score['score']['date'], line_index=single_score['score']['line_index'], score=matches))
  except IndexError:
    pass

  Score.objects.bulk_create(single_score for single_score in scored)
  print 'bulk_score done'


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
def update_rule(rule, batch_size=5000):
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
          score_meta = ScoreMeta(rule=rule, channel=channel, line_index=0, date=channel.start_date)
          score_meta.save()

        pool = redis.ConnectionPool(host='localhost', port=6379, db=channel.redis_db)
        r = redis.Redis(connection_pool=pool)
        pipe = r.pipeline()

        task_list = deque()
        # task_list = list()

        index = score_meta.line_index
        line_date = score_meta.date
        line_indexes = deque()

        nicks = dict()
        for nick in Nick.objects.all():
          nicks[nick.name] = nick

        while index < channel.line_count:

          line_indexes.appendleft(index)

          pipe.hgetall('-'.join([channel.slug, str(index)]))

          if index % batch_size == 0 and index > 0 or index == channel.line_count - 1:
            renew_lock(lockname, identifier)
            lines = pipe.execute()

            date =  ''

            for line in lines:
              current_line = line_indexes.pop()
              if line:
                # print current_line
                # print line
                # print line['line']
                # print line['nick']
                date = line['date']
                if not date:
                  print line
                # print 'date testing'
                # print date
                try:
                  task_list.appendleft({'score' : {'rule' : rule, 'nick' : nicks[line['nick']], 'channel' : channel, 'date' : date, 'line_index' : current_line}, 'line' : line['line']})
                except IndexError:
                  pass

            # print index
            # print date
            if not date:
              print 'no date'
            bulk_score.delay(deque(task_list))
            task_list.clear()
            score_meta.line_index = index
            # import pdb; pdb.Pdb(skip=['django.*']).set_trace()
            score_meta.date = date
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
