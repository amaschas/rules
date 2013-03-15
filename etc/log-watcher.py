#!/usr/bin/python

import os, sys, time, re, json, redis
from collections import deque
from httplib2 import Http
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler 

# argv[1]: target directory
# argv[2]: file filter string
# Feeds directory of log files into redis, and notifies the Django app when shit changes
# invoke like this: python logwatch.py /path/to/logs/ <filter string for logs>

class LogUpdateHandler(FileSystemEventHandler): 
  def __init__(self):

    # Grab a list of files in the target directory, sort and stick in a deque for optimized access (lists are slow)
    self.dir = deque()
    for f in sorted(filter(lambda x: sys.argv[2] in x, os.listdir(sys.argv[1]))):
      self.dir.append('%s%s' % (sys.argv[1], f))

    # Open the first file in the queue
    self.file = open(self.dir.popleft(), 'r')

    # Init ourself some redis
    self.r = redis.Redis(host='localhost', port=6379, db=0)
    self.redis_index = 0

    # Set the initial file position
    self.where = self.file.tell()

    # Run the initial feed of the logs
    self.ReadLog()
    FileSystemEventHandler.__init__(self)

  # If a new file is created, append to list of files in target directory
  def on_created(self, event):
    if sys.argv[2] in os.path.basename(event.src_path):
      self.dir.append(event.src_path)

  # If anything is modified, trigger ReadLog()
  def on_modified(self, event):
    if sys.argv[2] in os.path.basename(event.src_path):
      self.ReadLog()

  #TODO: method that triggers the dango app api
    # h = Http()
    # resp, content = h.request("http://127.0.0.1:8000/update/", "POST", json.dumps({'update' : 'avara'}), headers={'content-type':'application/json'})

  def ReadLog(self):
    # Set byte position in file
    self.file.seek(self.where)

    # For each line in the file, insert into redis, keyed by the line number
    for line in self.file:
      # print '%s - %s' % (self.redis_index, line.strip())
      self.r.set(self.redis_index, line.strip())
      self.redis_index += 1

    # Once we're done with the file, check if there is another, and run ReadLog() on it if it exists
    try:
      self.file = open(self.dir.popleft(), 'r')
      self.where = 0
      self.ReadLog()

    # Else keep our position in the file
    except IndexError:
      self.where = self.file.tell()

if __name__ == "__main__":
  # Initializing watchdog stuff
  path = sys.argv[1] if len(sys.argv) > 1 else '.'
  event_handler = LogUpdateHandler()
  observer = Observer()
  observer.schedule(event_handler, path, recursive=False)
  observer.start()
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()
  observer.join()