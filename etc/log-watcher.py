#!/usr/bin/python

import os, sys, time, re, json, redis, argparse
from collections import deque
from httplib2 import Http
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler 

# Feeds directory of log files into redis, and notifies the Django app when shit changes

class LogUpdateHandler(FileSystemEventHandler): 
  def __init__(self):
    # Grab a list of files in the target directory, sort and stick in a deque for optimized access (lists are slow)
    self.dir = deque()
    for f in sorted(filter(lambda x: args.filter_string in x, os.listdir(args.path))):
      self.dir.append('%s%s' % (args.path, f))

    # Open the first file in the queue
    self.file = open(self.dir.popleft(), 'r')

    # Init ourselves some redis
    self.r = redis.Redis(host='localhost', port=6379, db=args.db_index)
    self.redis_index = 0

    # Set the initial file position
    self.where = self.file.tell()

    # Run the initial feed of the logs
    self.ReadLog()
    FileSystemEventHandler.__init__(self)

  # If a new file is created, append to list of files in target directory, run ReadLog and Score
  def on_created(self, event):
    if event.__class__.__name__ == 'FileCreatedEvent':
      if args.filter_string and args.filter_string not in os.path.basename(event.src_path):
        pass
      else:
        self.dir.append(event.src_path)
        self.ReadLog()
        self.score()

  # If file is modified, run ReadLog and Score
  def on_modified(self, event):
    if event.__class__.__name__ == 'FileModifiedEvent':
      if args.filter_string and args.filter_string not in os.path.basename(event.src_path):
        pass
      else:
        self.ReadLog()
        self.score()

  # Makes an API request to the Django app that starts the scoring process
  def score(self):
    h = Http()
    resp, content = h.request('http://%s' % args.api_url, "POST", json.dumps({'channel' : args.channel_name}), headers={'content-type':'application/json'})

    #not sure if we need:
    # h.add_certificate('serverkey.pem', 'servercert.pem', '')

    # For Production
    # h = Http(disable_ssl_certificate_validation=True)
    # h.add_credentials('name', 'password')
    # resp, content = h.request("https://127.0.0.1:8000/score/", "POST", json.dumps({'channel' : args.channel_name}), headers={'content-type':'application/json'})

  def ReadLog(self):
    # Set byte position in file
    self.file.seek(self.where)

    # For each line in the file, insert into redis, keyed by the channel name and line number
    for line in self.file:
      if not args.overwrite and self.r.get('%s-%s' % (args.channel_name, self.redis_index)):
        pass
      else:
        if args.verbose:
          print '%s-%s: %s' % (args.channel_name, self.redis_index, line.strip())
        self.r.set('%s-%s' % (args.channel_name, self.redis_index), line.strip())
      self.redis_index += 1

    # Once we're done with the file, check if there is another, and run ReadLog() on it if it exists
    try:
      self.file = open(self.dir.popleft(), 'r')
      self.where = 0
      self.ReadLog()

    # Else keep our position in the file
    except IndexError:
      self.where = self.file.tell()
      pass

if __name__ == "__main__":

  parser = argparse.ArgumentParser()
  parser.add_argument('path', help="The path to the log directory")
  parser.add_argument('channel_name', help="The name of the channel being logged")
  parser.add_argument('api_url', help="The API url to notify of updates")
  parser.add_argument('-d', '--db-index', help="The index of the redis db to use (default: 0)", default=0, type=int)
  parser.add_argument('-f', '--filter-string', help="A string used to filter filenames", default='')
  parser.add_argument('-o', '--overwrite', help="Flag to overwrite prior entries", action="store_true")
  parser.add_argument('-v', '--verbose', help="Print each line logged", action="store_true")
  # parser.add_argument('-s', '--secure', help="Flag to use https instead of http for API target", action="store_true")
  # parser.add_argument('-u', '--username', help="Username for the client API target")
  # parser.add_argument('-p', '--password', help="Password for the client API target")
  args = parser.parse_args()

  args.path = os.path.normpath(args.path) + os.sep
  if not os.path.isdir(args.path):
    raise ValueError("Invalid Path")

  # Initializing watchdog stuff
  event_handler = LogUpdateHandler()
  observer = Observer()
  observer.schedule(event_handler, args.path, recursive=False)
  observer.start()
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()
  observer.join()