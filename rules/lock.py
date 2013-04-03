import redis, time, contextlib

REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0)

# Got this here: http://dr-josiah.blogspot.com/2012/01/creating-lock-with-redis.html

def acquire_lock(lockname, identifier, ltime=60):
  # print identifier
  print 'locking'
  if REDIS_CLIENT.setnx(lockname, identifier):
    REDIS_CLIENT.expire(lockname, ltime)
    return identifier
  elif not REDIS_CLIENT.ttl(lockname):
    REDIS_CLIENT.expire(lockname, ltime)

  return False

def release_lock(lockname, identifier):
  print 'unlocking'
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
