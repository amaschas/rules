from celery import Celery
import re

celery = Celery('tasks', broker='amqp://guest@localhost//')

# could do this with score_channel.apply_async((channel_id, rule_id=None), link=score_log.s(rules, log_path, start_position))

# need this
# @celery.task
# def nick_scan

@celery.task
def score_channel(channel_slug, rule_id=None):
  try:
    channel = Channel.objects.get(pk=channel_d)
    start_position = 0
    rules = {}
    if rule_id:
      rules = Rules.objects.get(pk=rule_id)
      if rules[0].status = 'new':
        rules[0].status = 'scoring'
        rules[0].save()
      else:
        start_position = channel.current_log_position
    else
      rules = Rules.objects.get()
      start_position = channel.current_log_position
    # score.delay(rules, channel.log_path, start_position)
    return {'rules' : rules, 'log_path' : channel.log_path, 'start_position' : start_position}

@celery.task
def score_log(rules, log_path, start_position):
  log = open(log_path, 'r')
  log.seek(start_position)
  while line = log.readline()
    #check rule length?
    for rule in rules:
      if re.search(rule.regex, line):
        user = get_user_from_nick(line)
        score(rule.id, user)
  if start_position = 0:
    rule[0].status = 'active'
    rule[0].save()