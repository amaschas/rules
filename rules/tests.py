import redis, re
from django.test import TestCase
from django.utils import unittest
from django.conf import settings

from django.contrib.auth.models import User
from rules.tasks import *
from signals import update_rules
from rules.models import *

class TestGateway(TestCase):

  def test_score_task(self):
    print 'running'
    self.create_test_data()
    rules = Rule.objects.all()
    print rules
    for rule in rules:
      update_rules.connect(rule.score)
    update_rules.send('test_score_task')

  def create_test_data(self):
    u = User(1, 'testing', 'testing@test.com', 'testing')
    r1 = Rule(creator=u, name='Test1', rule='test1')
    r2 = Rule(creator=u, name='Test2', rule='test2')
    r3 = Rule(creator=u, name='Test3', rule='test3')
    u.save()
    r1.save()
    r2.save()
    r3.save()

  def test_score_object(self):
    c = Channel(title='testing', slug='testing')
    n = Nick(name='test')
    r = Rule(creator=u, name='Test1', rule='o')
    score = Score(rule=r, nick=n, channel=c, line_index=0)
    # print score.nick
    score.delay(score, '1')

  def test_regex_search(self):
    r = redis.Redis(host='localhost', port=6379, db=0)
    l = r.get('avara-1')
    s = re.findall('hoorj', l)
    print len(s)


  def test_save(self):
    # c = Channel(title='testing', slug='testing')
    # c.save()
    u = User(username='testing', email='testing@test.com', password='testing')
    u.save()
    r1 = Rule(creator=u, name='Test1', rule='test1')
    r1.save()
    r1.status='active'
    r1.save(update_fields=['status'])

  def test_lines(self):
    r = redis.Redis(host='localhost', port=6379, db=0)
    line_index = 0
    line = r.get('%s-%d' % ('avara', line_index))
    while line:
      if not re.match('\[.*\] <.*>', line):
        print line
        # print '%d - %s' % (line_index, line[8:])
        nick = Nick.get_nick(line)
        if nick:
          print nick.name
      line_index += 1
      line = r.get('%s-%d' % ('avara', line_index))

  def test_get_nick(self):
    r = redis.Redis(host='localhost', port=6379, db=0)
    line = r.get('avara-1027')
    Nick.get_nick(line)

  def test_channel_functions(self):
    c = Channel(title='testing', slug='testing')
    print c.update_current_line(2)