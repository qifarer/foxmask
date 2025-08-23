# foxmask/infrastructure/cache.py
from foxmask.core.redis import get_redis_client
from foxmask.core.config import get_settings
import json
from typing import Optional, Any

settings = get_settings()
redis_client = get_redis_client()

def get_cache(key: str, default: Any = None) -> Optional[Any]:
    """Get value from Redis cache"""
    value = redis_client.get(key)
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def set_cache(key: str, value: Any, expire: int = 3600) -> bool:
    """Set value in Redis cache with expiration"""
    try:
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)
        return redis_client.setex(key, expire, value)
    except Exception:
        return False

def delete_cache(key: str) -> bool:
    """Delete value from Redis cache"""
    return redis_client.delete(key) > 0