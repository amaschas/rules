from celery import Celery
import glob
import re

celery = Celery('rules', broker='django://')

# could do this with score_channel.apply_async((channel_id, rule_id=None), link=score_log.s(rules, log_path, start_position))

# need this
# @celery.task
# def nick_scan

@celery.task
def log_watcher():
  # channels = Channel.objects.get()
  # for channel in channels:
  logs = glob.glob('/Users/alexi/Documents/log.avara/*')
  print 'test'
  print logs.__len__()


@celery.task
def score_channel(channel_slug, rule_id=None):
  print 'running'
  try:
    channel = Channel.objects.get(pk=channel_d)
    start_position = 0
    rules = {}
    if rule_id:
      rules = Rule.objects.get(pk=rule_id)
      if rules.status == 'new':
        rules.status = 'scoring'
        rules.save()
      else:
        start_position = channel.current_log_position
    else:
      rules = Rules.objects.get()
      start_position = channel.current_log_position
    score_log.delay(rules, channel.log_path, start_position)
    return {'rules' : rules, 'log_path' : channel.log_path, 'start_position' : start_position}
  except:
    pass

@celery.task
def score_log(rules, log_path, start_position):
  log = open(log_path, 'r')
  log.seek(start_position)
  for line in log.xreadlines():
    print 'checking line'
    rules.score(line)
    #check rule length?
    # for rule in rules:
      # if rule.status == 'active':
          # rule.score(line)
   #This should check to see if the log.readline matches the current last line for the channel
  # if start_position == 0:
  #   rule[0].status = 'active'
  #   rule[0].save()