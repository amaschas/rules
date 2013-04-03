import redis, time, contextlib

REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0)

def acquire_lock(lockname, identifier, atime=1, ltime=60):
  # print identifier
  end = time.time() + atime
  while end > time.time():
    if REDIS_CLIENT.setnx(lockname, identifier):
      REDIS_CLIENT.expire(lockname, ltime)
      return identifier
    elif not REDIS_CLIENT.ttl(lockname):
      REDIS_CLIENT.expire(lockname, ltime)

    time.sleep(.001)

  return False


# def get_lock(lockname, identifier):
#   pipe = REDIS_CLIENT.pipeline(True)

#   while True:
#     try:
#       pipe.watch(lockname)
#       test = pipe.get(lockname)
#       if test == identifier:
#         return True

#       pipe.unwatch()
#       break

#     except redis.exceptions.WatchError:
#         pass

#   return False


def release_lock(lockname, identifier):
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
