from django.test import TestCase
from django.utils import unittest
from django.conf import settings

from django.contrib.auth.models import User
from rules.tasks import *
from signals import update_rules

class TestGateway(TestCase):

  def test_score_task(self):
    print 'running'
    self.create_test_data()
    rules = Rule.objects.all()
    print rules
    for rule in rules:
      update_rules.connect(rule.score)
    update_rules.send('test_score_task')
    # score_rules.delay('test')

  def create_test_data(self):
    u = User(1, 'testing', 'testing@test.com', 'testing')
    r1 = Rule(creator=u, name='Test1', rule='test1')
    r2 = Rule(creator=u, name='Test2', rule='test2')
    r3 = Rule(creator=u, name='Test3', rule='test3')
    u.save()
    r1.save()
    r2.save()
    r3.save()