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
    return True
  else:
    return False


# Using a receiver function here instead of directly calling update_channel so update_channel can remain generalized
@receiver(post_save, sender=Channel)
def update_channel_save_trigger(sender, **kwargs):
  if kwargs['created']:
    try:
      # Could do this in a loop to prevent nick collisions
      rules = Rule.objects.filter()
      g = group(update_rule.s(rule=rule) for rule in rules)
      g.apply_async()
      channel_count.delay(kwargs['instance'])
    except ObjectDoesNotExist:
      pass


# This should also get all unique nicks
# prevents the nick collision problem
@celery.task
def channel_count(channel):
  redis_index = channel.line_count
  nicks = []
  pool = redis.ConnectionPool(host='localhost', port=6379, db=channel.redis_db)
  line = Score.get_line(channel, redis_index, pool)
  while line:
    if redis_index % 1000 == 0:
      os.system('clear')
      print redis_index
    nick = Nick.get_nick(line)
    if nick and nick not in nicks:
      nicks.append(nick)
    redis_index += 1
    line = Score.get_line(channel, redis_index, pool)
  print nicks
  Nick.objects.bulk_create(Nick(name=nick_string) for nick_string in nicks)
  channel.set_line_count(redis_index + 1)
  print 'done'


# Could have a redis record of scoreable lines, or maybe just dump the non-scoring lines?
# This would mean any line I read is garaunteed scorable
# Scores the rule against every active channel, starting at index
@celery.task
def update_rule(rule):
  print 'starting score'
  identifier = str(uuid.uuid4())
  lockname = 'rule-%s-scoring' % rule.id
  if acquire_lock(lockname, identifier) == identifier:

    test_nick = Nick.objects.get(name='test')

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
            # TODO separate get_nick from scoring process
            # maybe have a simpler match_nick?
            nick = Nick.get_nick(line)
            if nick:
              # could make this one enormous score group
              # score.delay(Score(rule=rule, nick=nick, channel=channel, date=score_meta.date, line_index=score_meta.line_index), line=line)

              # score.delay(Score(rule=rule, nick=test_nick, channel=channel, date=score_meta.date, line_index=index), line=line)
              task_list.append(score.s(Score(rule=rule, nick=test_nick, channel=channel, date=score_meta.date, line_index=index), line=line))

              score(Score(rule=rule, nick=test_nick, channel=channel, date=score_meta.date, line_index=index), line=line)


          # TODO use a counter var to avoid slow mysql saves
          # Maybe update this every 1000 interrations?
          index += 1
          line = Score.get_line(channel, index, pool)
        score_meta.line_index = index
        score_meta.save()

        g = group(task_list)
        g.apply_async()

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
