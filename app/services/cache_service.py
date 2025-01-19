import redis
from datetime import timedelta
import json
from app.config import REDIS_URL, logger

# Uitgebreide debug logging
logger.info("="*50)
logger.info("REDIS CONFIGURATION")
logger.info(f"URL: {REDIS_URL}")
logger.info("="*50)

try:
    # Probeer verbinding te maken
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,  # Auto-decode responses
        socket_timeout=5,       # 5 sec timeout
        retry_on_timeout=True   # Auto-retry
    )
    
    # Test verbinding
    ping = redis_client.ping()
    logger.info(f"Redis ping successful: {ping}")
    
    # Test schrijven/lezen
    redis_client.set("test_key", "test_value", ex=60)
    test_value = redis_client.get("test_key")
    logger.info(f"Redis test read/write: {test_value}")
    
except Exception as e:
    logger.error(f"Redis initialization error: {str(e)}")
    logger.error(f"Error type: {type(e).__name__}")
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
        redis_client.setex(key, expire_seconds, json_data)
        logger.info(f"Successfully cached data for key: {key}")
    except Exception as e:
        logger.error(f"Cache set error: {str(e)}") 