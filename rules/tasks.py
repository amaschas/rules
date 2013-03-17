from celery import Celery
from celery import group
import glob
import re

from models import Rule
from signals import update_rules

celery = Celery('rules', backend='redis://localhost', broker='amqp://guest:guest@localhost:5672//')

# could do this with score_channel.apply_async((channel_id, rule_id=None), link=score_log.s(rules, log_path, start_position))

# need thi'score_rules'# @celery.task
# def nick_scan

@celery.task
def score_rules(channel_slug):
  rules = Rule.objects.all()
  g = group(score.s(rule) for rule in rules)
  g.apply_async()

@celery.task
def score(rule):
  return rule.score()

# def test():
#   print 'blah'
#   update_rules.send('score_rules')

# @celery.task
# def score_channel(channel_slug, rule_id=None):
#   print 'running'
#   try:
#     channel = Channel.objects.get(pk=channel_d)
#     start_position = 0
#     rules = {}
#     if rule_id:
#       rules = Rule.objects.get(pk=rule_id)
#       if rules.status == 'new':
#         rules.status = 'scoring'
#         rules.save()
#       else:
#         start_position = channel.current_log_position
#     else:
#       rules = Rules.objects.get()
#       start_position = channel.current_log_position
#     score_log.delay(rules, channel.log_path, start_position)
#     return {'rules' : rules, 'log_path' : channel.log_path, 'start_position' : start_position}
#   except:
#     pass

# @celery.task
# def score_log(rules, log_path, start_position):
#   log = open(log_path, 'r')
#   log.seek(start_position)
#   for line in log.xreadlines():
#     print 'checking line'
#     rules.score(line)
    #check rule length?
    # for rule in rules:
      # if rule.status == 'active':
          # rule.score(line)
   #This should check to see if the log.readline matches the current last line for the channel
  # if start_position == 0:
  #   rule[0].status = 'active'
  #   rule[0].save()