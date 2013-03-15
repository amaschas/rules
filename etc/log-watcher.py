#!/usr/bin/python

import os, sys, time, redis
from collections import deque
from httplib2 import Http
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler 

class LogUpdateHandler(FileSystemEventHandler): 
  def __init__(self):
    # This needs to read each file in sequence
    self.dir = deque()
    for f in sorted(filter(lambda x: x.find('avara') > -1, os.listdir(sys.argv[1]))):
      self.dir.append(f)
    self.file = open('%s%s' % (sys.argv[1], self.GetLog()), 'r')
    self.r = redis.Redis(host='localhost', port=6379, db=0)
    self.redis_index = 0
    self.where = self.file.tell()
    self.ReadLog()
    FileSystemEventHandler.__init__(self)

  def on_any_event(self, event): 
    self.ReadLog()
    print event
    # h = Http()
    # resp, content = h.request("http://127.0.0.1:8000/update/", "POST", json.dumps({'message' : 'updated'}), headers={'content-type':'application/json'})

  def GetLog(self):
    return self.dir.popleft()


  def ReadLog(self):
    self.file.seek(self.where)
    for line in self.file:
      print '%s - %s' % (self.redis_index, line.strip())
      self.r.set(self.redis_index, line.strip())
      self.redis_index += 1
    try:
      self.file = open('%s%s' % (sys.argv[1], self.GetLog()), 'r')
      self.where = 0
      self.ReadLog()
    except IndexError:
      self.where = self.file.tell()

if __name__ == "__main__":
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
  # except:
  #   try:
  #     print 'Log not found at: %s' % sys.argv[1]
  #   except IndexError:
  #     print 'Usage: log-watcher.py <path-to-log-file>'