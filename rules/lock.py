import redis, time, contextlib

REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0)

# Got this here: http://dr-josiah.blogspot.com/2012/01/creating-lock-with-redis.html

def acquire_lock(lockname, identifier, ltime=10):
  # print identifier
  print 'locking %s' % lockname
  if REDIS_CLIENT.setnx(lockname, identifier):
    REDIS_CLIENT.expire(lockname, ltime)
    return identifier
  # could put renew_lock here
  elif not REDIS_CLIENT.ttl(lockname):
    REDIS_CLIENT.expire(lockname, ltime)
  return False

def check_lock(lockname):
  if REDIS_CLIENT.get(lockname):
    return True
  return False

def renew_lock(lockname, identifier, ltime=10):
  # print 'lock renewed'
  if REDIS_CLIENT.get(lockname) == identifier:
    REDIS_CLIENT.expire(lockname, ltime)
    return True
  return False

def release_lock(lockname, identifier):
  print 'unlocking %s' % lockname
  pipe = REDIS_CLIENT.pipeline(True)

  while True:
    try:
      pipe.watch(lockname)
      if pipe.get(lockname) == identifier:
        pipe.multi()
        pipe.delete(lockname)
        pipe.execute()
        return True

      pipe.unwatch()
      break

    except redis.exceptions.WatchError:
        pass
  # we lost the lock
  return False
