#!/usr/bin/python

import os, sys, time, re, json, redis, argparse
from collections import deque
from httplib2 import Http, ServerNotFoundError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max

from rules.models import *
from rules.tasks import *

# initializes or updates a channel and a redis db of log lines
class LogUpdateHandler(FileSystemEventHandler):

  def __init__(self, options):

    # print options

    # Store the command line args
    self.options = options
    self.channel = Channel.objects.get(slug=self.options['channel_name'])

    # Init ourselves some redis
    pool = redis.ConnectionPool(host='localhost', port=6379, db=self.channel.redis_db)
    r = redis.Redis(connection_pool=pool)
    self.pipe = r.pipeline()
    self.redis_index = 0

    # If the overwrite flag is set, flush the redis db, 
    # set the channel line count to 0, and set the date
    # context to the channel start date, else grab the latest
    # date from the scores
    if self.options['overwrite']:
      r.flushdb()
      self.channel.set_line_count(0)
      self.date = self.channel.start_date
    else:
      self.date = self.channel.get_latest_date()

    # Define the nick handling members
    self.nicks = dict()
    nick_regex_string = '[a-zA-Z0-9_-\{\}\^\`\|]+'
    self.nick_regex_strings = [
      '<(?P<nick>%s)>' % nick_regex_string,
      'Action: (?P<nick>%s) ' % nick_regex_string,
      'Nick change: (?P<nick>%s) ' % nick_regex_string,
      'Topic changed on [#&][[a-zA-Z0-9]+ by (?P<nick>%s)\!' % nick_regex_string,
      '%s kicked from [#&][[a-zA-Z0-9]+ by (?P<nick>%s)' % (nick_regex_string, nick_regex_string),
      '(?P<nick>%s) \(.*\) [left|joined]' % nick_regex_string,
      '[#&][[a-zA-Z0-9]+: mode change \'.*\' by (?P<nick>%s)\!' % nick_regex_string
    ]

    #Grab a list of files in the target directory, sort and stick in a deque for optimized access (lists are slow)
    self.dir = deque()
    for f in sorted(filter(lambda x: self.options['filter_string'] in x, os.listdir(self.options['path']))):
      self.dir.append('%s%s' % (self.options['path'], f))

    # Open the first file in the queue
    self.file = open(self.dir.popleft(), 'r')

    # Set the initial file position
    self.where = self.file.tell()

    # Run the initial feed of the logs
    self.ReadLog()
    FileSystemEventHandler.__init__(self)

  # If a new file is created, append to list of files in target directory, run ReadLog and Score
  def on_created(self, event):
    if event.__class__.__name__ == 'FileCreatedEvent':
      if self.options['filter_string'] and self.options['filter_string'] not in os.path.basename(event.src_path):
        pass
      else:
        self.dir.append(event.src_path)
        self.ReadLog()
        # self.score()

  # If file is modified, run ReadLog and Score
  def on_modified(self, event):
    if event.__class__.__name__ == 'FileModifiedEvent':
      if self.options['filter_string'] and self.options['filter_string'] not in os.path.basename(event.src_path):
        pass
      else:
        self.ReadLog()
        # self.score()

  def ReadLog(self):
    # Set byte position in file
    self.file.seek(self.where)

    # For each line in the file, insert into redis, keyed by the channel name and line number
    # TODO set the date for the entire file at the end, so each file is dated correctly regardless of order
    for line in self.file:
      if not self.options['overwrite'] and self.redis_index < self.channel.line_count:
        pass
      else:
        line = line.strip()
        if self.redis_index % 1000 == 0 and self.options['verbose']:
          os.system('clear')
          print 'Current index: %s' % self.redis_index
        if re.match('\[00:00\] --- ', line):
          self.date = datetime.strptime(line[12:], '%a %b %d %Y')
        else:
          for regex_string in self.nick_regex_strings:
            nick_match = re.match(regex_string, line[8:])
            if nick_match:
              nick_string = nick_match.group('nick')
              if nick_string not in self.nicks:
                self.nicks[nick_string] = True
              self.pipe.hmset(str(self.redis_index), {
                'line' : line,
                'date' : self.date,
                'nick' : nick_string
              })
              break
        self.redis_index += 1

    self.channel.set_line_count(self.redis_index + 1)
    self.pipe.execute()
    # if Nick.objects.count() == 0:
    #   Nick.objects.bulk_create(Nick(name=nick[0], first_seen=self.date) for nick in self.nicks.iteritems())
    # else:
    for nick in self.nicks.iteritems():
      if nick[1]:
        Nick.objects.get_or_create(name=nick[0], first_seen=self.date)
        self.nicks[nick[0]] = False

    # Once we're done with the file, check if there is another, and run ReadLog() on it if it exists
    try:
      self.file = open(self.dir.popleft(), 'r')
      self.where = 0
      self.ReadLog()

    # Else keep our position in the file
    except IndexError:
      self.where = self.file.tell()
      pass

class Command(BaseCommand):
  option_list = BaseCommand.option_list + (
    make_option('--path', help="The path to the log directory"),
    make_option('--channel-name', help="The name of the channel being logged"),
    make_option('-f', '--filter-string', help="A string used to filter filenames", default=''),
    make_option('-o', '--overwrite', help="Flag to overwrite prior entries", action="store_true"),
    make_option('--verbose', help="Enable verbose output", action="store_true", default=False),
  )

  def handle(self, *args, **options):

    sys.setrecursionlimit(10000)

    options['path'] = os.path.normpath(options['path']) + os.sep
    if not os.path.isdir(options['path']):
      raise ValueError("Invalid Path")

    # Initializing watchdog stuff
    event_handler = LogUpdateHandler(options)
    observer = Observer()
    observer.schedule(event_handler, options['path'], recursive=False)
    observer.start()
    try:
      while True:
        time.sleep(1)
    except KeyboardInterrupt:
      observer.stop()
    observer.join()