#!/usr/bin/python

import os, sys, time, redis
from collections import deque
from httplib2 import Http
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler 

# argv[1]: target directory
# argv[2]: file filter string
# Feeds directory of log files into redis, and notified the Django app when shit changes
# invoke like this: python logwatch.py /path/to/logs/ <filter string for logs>

class LogUpdateHandler(FileSystemEventHandler): 
  def __init__(self):
    # Grab a list of files in the target directory, sort and stick in a deque for optimized access (lists are slow)
    self.dir = deque()
    for f in sorted(filter(lambda x: x.find(sys.argv[2]) > -1, os.listdir(sys.argv[1]))):
      self.dir.append(f)
    # Open the first file in the queue
    self.file = open('%s%s' % (sys.argv[1], self.dir.popleft()), 'r')
    # Init ourself some redis
    self.r = redis.Redis(host='localhost', port=6379, db=0)
    self.redis_index = 0
    # Set the initial file position
    self.where = self.file.tell()
    # Run the initial feed of the logs
    self.ReadLog()
    FileSystemEventHandler.__init__(self)

  def on_any_event(self, event): 
    # Feed from the logs when anything happens
    # TODO: When a file is added, it should be appended to the queue before logs are read
    self.ReadLog()
    # print event
    # TODO: Hit the API call on the Django app
    # h = Http()
    # resp, content = h.request("http://127.0.0.1:8000/update/", "POST", json.dumps({'message' : 'updated'}), headers={'content-type':'application/json'})

  def ReadLog(self):
    # Set byte position in file
    self.file.seek(self.where)
    # For each line in the file, insert into redis, keyed by the line number
    for line in self.file:
      # print '%s - %s' % (self.redis_index, line.strip())
      self.r.set(self.redis_index, line.strip())
      self.redis_index += 1
    try:
      # Once we're done with the file, check if there is another, and run ReadLog() on it if it exists
      self.file = open('%s%s' % (sys.argv[1], self.dir.popleft()), 'r')
      self.where = 0
      self.ReadLog()
    except IndexError:
      # Else keep our position in the file
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