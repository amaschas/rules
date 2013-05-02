import glob, re, redis, os
from collections import deque
from celery import Celery
from celery import group

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save

from models import *
from lock import acquire_lock, release_lock, renew_lock

# import logging
# log = logging.getLogger(__name__)

# Might not need a backend
celery = Celery('rules', broker='amqp://guest:guest@localhost:5672//')


# scores a chunk of lines at a time to reduce concurrency overhead
@celery.task
def bulk_score(scores):
  # print 'bulk scoring'
  scored = list()
  try:
    while scores:
      single_score = scores.popleft()

      # single_score = scores.pop()
      matches = len(re.findall(single_score['score']['rule'].rule, single_score['line']))
      if matches:
        scored.append(Score(rule=single_score['score']['rule'], nick=single_score['score']['nick'], channel=single_score['score']['channel'], date=single_score['score']['date'], line_index=single_score['score']['line_index'], score=matches))
  except IndexError:
    pass

  Score.objects.bulk_create(single_score for single_score in scored)
  print 'bulk_score done'


# TODO remove all non scoring lines
@celery.task
def update_channel(channel):
  #this needs to lock
  redis_index = channel.line_count
  nicks = []
  # get_line is slightly slower, maybe just do it the other way
  pool = redis.ConnectionPool(host='localhost', port=6379, db=channel.redis_db)
  line = Score.get_line(channel, redis_index, pool)
  # r = redis.Redis(connection_pool=pool)
  # line = r.get('%s-%d' % (channel.slug, redis_index))
  while line:
    # if redis_index % 1000 == 0:
    #   os.system('clear')
    #   print redis_index
    nick = Nick.get_nick(line)
    if nick and nick not in nicks:
      nicks.append(nick)
    redis_index += 1
    line = Score.get_line(channel, redis_index, pool)
    # line = r.get('%s-%d' % (channel.slug, redis_index))
  print nicks
  if Nick.objects.count() == 0:
    Nick.objects.bulk_create(Nick(name=nick_string) for nick_string in nicks)
  else:
    for nick_string in nicks:
      Nick.objects.get_or_create(name=nick_string)
  channel.set_line_count(redis_index + 1)

  rules = Rule.objects.filter()
  g = group(update_rule.s(rule=rule) for rule in rules)
  g.apply_async()

  print 'done'


# Using a receiver function here instead of directly calling update_channel so update_channel can remain generalized
@receiver(post_save, sender=Channel)
def update_channel_save_trigger(sender, **kwargs):
  if kwargs['created']:
    try:
      # Could do this in a loop to prevent nick collisions
      rules = Rule.objects.filter()
      g = group(update_rule.s(rule=rule) for rule in rules)
      g.apply_async()
      update_channel.delay(kwargs['instance'])
    except ObjectDoesNotExist:
      pass


#TODO maybe worth using a redis hash to store nick, channel and date for each line, keyed by line number, maybe also the line?
# Scores the rule against every active channel
@celery.task
def update_rule(rule):
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
          # print index

          line_indexes.appendleft(index)
          pipe.get('%s-%d' % (channel.slug, index))

          # TODO use BATCH_SIZE in settings here
          if index % 5000 == 0 and index > 0 or index == channel.line_count - 1:
            renew_lock(lockname, identifier)
            lines = pipe.execute()

            for line in lines:
              current_line = line_indexes.pop()
              if line:
                line_date = ScoreMeta.format_date_line(line, line_date)
                nick_string = Nick.get_nick(line)
                if nick_string:
                  try:
                    task_list.appendleft({'score' : {'rule' : rule, 'nick' : nicks[nick_string], 'channel' : channel, 'date' : score_meta.date, 'line_index' : current_line}, 'line' : line})
                  except IndexError:
                    pass

            bulk_score.delay(deque(task_list))
            task_list.clear()
            score_meta.line_index = index
            score_meta.date = line_date
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
    update_rule.delay(rule=kwargs['instance'], index=0)
