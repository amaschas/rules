import redis

REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0)

def lock(key, timeout=500):
  lock = REDIS_CLIENT.lock(key, timeout=timeout)
  if lock.acquire(blocking=False):
    return True
  else:
    return False

def unlock(key):
  lock = REDIS_CLIENT.lock(key)
  lock.release()