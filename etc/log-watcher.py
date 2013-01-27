#!/usr/bin/python

import sys
import time

def tail_f(file):
  interval = 1.0

  while True:
    where = file.tell()
    line = file.readline()
    if not line:
      time.sleep(interval)
      file.seek(where)
    else:
      yield line

try:
  for line in tail_f(open(sys.argv[1], 'r')):
    print line,
except:
  try:
    print 'Log not found at: %s' % sys.argv[1]
  except IndexError:
    print 'Usage: log-watcher.py <path-to-log-file>'