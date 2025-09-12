# foxmask/core/redis.py
import redis
from foxmask.core.config import get_settings

settings = get_settings()

def get_redis_client():
    return redis.Redis.from_url(str(settings.REDIS_URI), decode_responses=True)

