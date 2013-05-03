import cProfile
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from rules.models import *
from rules.tasks import *

class Command(BaseCommand):
  option_list = BaseCommand.option_list + (
    make_option('--delete-rules', action='store_true', default=False, help='Delete all rules'),
    make_option('--delete-nicks', action='store_true', default=False, help='Delete all nicks'),
    make_option('--reset-scores', action='store_true', default=False, help='Deletes all scores and resets score meta'),
    make_option('--score-channel', help='Score all rules for a single channel slug'),
    make_option('--score-rule', help='Score a single rule by id'),
    make_option('--profile', default='/tmp/score_profile', help='Enable profiling with cProfile, takes an optional path argument'),
  )

  def handle(self, *args, **options):

    if 'profile' in options and options['profile']:
      prof = cProfile.Profile()

    if 'delete_rules' in options and options['delete_rules']:
      self.stdout.write('Deleting rules')
      Rule.objects.all().delete()
      self.stdout.write('Rules successfully deleted')

    if 'delete_nicks' in options and options['delete_nicks']:
      self.stdout.write('Deleting nicks')
      Nick.objects.all().delete()
      self.stdout.write('Nicks successfully deleted')

    if 'reset_scores' in options and options['reset_scores']:
      self.stdout.write('Deleting scores')
      Score.objects.all().delete()
      ScoreMeta.objects.all().delete()
      self.stdout.write('Scores successfully deleted')

    if 'score_channel' in options and options['score_channel']:
      try:
        channel = Channel.objects.get(slug=options['score_channel'])
        channel.line_count=0
        channel.save()

        self.stdout.write('Scoring channel "%s"' % channel.title)
        if options['profile']:
          prof.runcall(update_channel, channel=channel)
          prof.dump_stats(options['profile'])
        else:
          update_channel(channel)
        self.stdout.write('Finished scoring channel "%s"' % channel.title)
      except ObjectDoesNotExist:
        self.stdout.write('No channel with slug: "%s"' % options['score_channel'])

    if 'score_rule' in options and options['score_rule']:
      try:
        rule = Rule.objects.get(id=options['score_rule'])

        self.stdout.write('Scoring rule "%s"' % rule.name)
        if options['profile']:
          prof.runcall(update_rule, rule=rule)
          prof.dump_stats(options['profile'])
        else:
          update_rule(rule)
        self.stdout.write('Finished scoring rule "%s"' % rule.name)
      except ObjectDoesNotExist:
        self.stdout.write('No rule with id: "%s"' % options['score_rule'])