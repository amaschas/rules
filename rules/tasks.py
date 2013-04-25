import glob, re, redis, os
from celery import Celery
from celery import group

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save

from models import *
from lock import acquire_lock, release_lock, renew_lock

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
    # maybe return the score and save it in a batch
    return True
  else:
    return False


# This should also get all unique nicks
# prevents the nick collision problem
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
    if redis_index % 1000 == 0:
      os.system('clear')
      print redis_index
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

        task_list = []
        line = Score.get_line(channel, score_meta.line_index, pool)
        index = score_meta.line_index

        while line:
          # print index
          renew_lock(lockname, identifier)
          line_date = ScoreMeta.format_date_line(line)
          if line_date:
            score_meta.set_date(line_date)
          else:
            nick_string = Nick.get_nick(line)
            if nick_string:
              nick = Nick.objects.get(name=nick_string)

              # task_list.append(score.s(Score(rule=rule, nick=nick, channel=channel, date=score_meta.date, line_index=index), line=line))

              # doesn't seem to be any advantage to doing this async
              score(Score(rule=rule, nick=nick, channel=channel, date=score_meta.date, line_index=index), line=line)

          index += 1
          line = Score.get_line(channel, index, pool)
        score_meta.line_index = index
        score_meta.save()

        # g = group(task_list)
        # g.apply_async()

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
