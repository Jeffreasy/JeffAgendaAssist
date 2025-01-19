import redis
from datetime import timedelta
import json
from app.config import REDIS_URL, logger

# Uitgebreide debug logging
logger.info("="*50)
logger.info("REDIS INITIALIZATION")
logger.info(f"REDIS_URL present: {bool(REDIS_URL)}")
logger.info("="*50)

if not REDIS_URL:
    logger.warning("No REDIS_URL configured, caching disabled")
    redis_client = None
else:
    try:
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        # Test connection
        ping = redis_client.ping()
        logger.info(f"Redis connection test: {ping}")
        
    except Exception as e:
        logger.error(f"Redis initialization failed: {str(e)}")
        redis_client = None

async def get_cached_data(key: str):
    """Haal data op uit Redis cache"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return None
        
    try:
        data = redis_client.get(key)
        hit = bool(data)
        logger.info(f"Cache {'HIT' if hit else 'MISS'} for key: {key}")
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Cache get error: {str(e)}")
        return None

async def set_cached_data(key: str, data: dict, expire_seconds: int = 300):
    """Sla data op in Redis cache"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return
        
    try:
        json_data = json.dumps(data)
        logger.info(f"Attempting to cache data for key: {key}")
        logger.info(f"Data size: {len(json_data)} bytes")
        
        success = redis_client.setex(key, expire_seconds, json_data)
        logger.info(f"Cache set success: {success}")
        
        # Verify the data was stored
        stored_data = redis_client.get(key)
        logger.info(f"Verification - data in cache: {bool(stored_data)}")
        
        return success
    except Exception as e:
        logger.error(f"Cache set error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return False 