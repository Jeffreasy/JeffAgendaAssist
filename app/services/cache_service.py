import redis
from datetime import timedelta
import json
from app.config import REDIS_URL, logger

# Debug logging toevoegen
logger.info(f"Connecting to Redis at: {REDIS_URL}")

try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()  # Test de verbinding
    logger.info("Redis connection successful")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

async def get_cached_data(key: str):
    """Haal data op uit Redis cache"""
    if not redis_client:
        logger.warning("Redis not connected, skipping cache")
        return None
        
    try:
        data = redis_client.get(key)
        if data:
            logger.info(f"Cache HIT for key: {key}")
            return json.loads(data)
        logger.info(f"Cache MISS for key: {key}")
        return None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None

async def set_cached_data(key: str, data: dict, expire_seconds: int = 300):
    """Sla data op in Redis cache"""
    if not redis_client:
        logger.warning("Redis not connected, skipping cache")
        return
        
    try:
        redis_client.setex(
            key,
            timedelta(seconds=expire_seconds),
            json.dumps(data)
        )
        logger.info(f"Data cached for key: {key}")
    except Exception as e:
        logger.error(f"Cache set error: {e}") 