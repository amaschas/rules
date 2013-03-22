#!/usr/bin/python

import os, sys
from collections import deque

# argv[1]: target directory
# argv[2]: channel name (used as file filter string)
# Counts lines in a directory of log files

def ReadLog(logdir):
  line_index = 0
  try:
    file = open(logdir.popleft(), 'r')
    for line in file:
      line_index += 1
    print line_index
    line_index += ReadLog(logdir)
  except IndexError:
    pass
  return line_index

if __name__ == "__main__":
  #TODO verify args here

  path = sys.argv[1] if len(sys.argv) > 1 else '.'

  # Grab a list of files in the target directory, sort and stick in a deque for optimized access (lists are slow)
  logdir = deque()
  for f in sorted(filter(lambda x: sys.argv[2] in x, os.listdir(sys.argv[1]))):
    logdir.append('%s%s' % (sys.argv[1], f))

  line_index = ReadLog(logdir)
  print line_index
