import redis
from datetime import timedelta
import json
from app.config import REDIS_URL, logger

redis_client = redis.from_url(REDIS_URL)

async def get_cached_data(key: str):
    """Haal data op uit Redis cache"""
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None

async def set_cached_data(key: str, data: dict, expire_seconds: int = 300):
    """Sla data op in Redis cache"""
    try:
        redis_client.setex(
            key,
            timedelta(seconds=expire_seconds),
            json.dumps(data)
        )
    except Exception as e:
        logger.error(f"Cache set error: {e}") 