#!/usr/bin/python

import sys
import time
import json
from httplib2 import Http
# from urllib import urlencode

def tail_f(file):
  interval = 1.0

  while True:
    where = file.tell()
    line = file.readline()
    print where
    if not line:
      time.sleep(interval)
      file.seek(where)
    else:
      yield line

try:
  for line in tail_f(open(sys.argv[1], 'r')):
    # print line,
    # json.dumps({'line' : line})
    h = Http()
    resp, content = h.request("http://127.0.0.1:8000/score/", "POST", json.dumps({'line' : line}), headers={'content-type':'application/json'})
except:
  try:
    print 'Log not found at: %s' % sys.argv[1]
  except IndexError:
    print 'Usage: log-watcher.py <path-to-log-file>'