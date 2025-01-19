import redis
from datetime import timedelta
import json
from app.config import REDIS_URL, logger, CACHE_TTL_SHORT, CACHE_TTL_MEDIUM, CACHE_TTL_LONG
from enum import Enum
from typing import Optional, Any

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

class CacheTTL(Enum):
    SHORT = "short"   # 5 min
    MEDIUM = "medium" # 1 uur
    LONG = "long"     # 1 dag

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

async def set_cached_data(key: str, data: Any, ttl_type: CacheTTL = CacheTTL.SHORT):
    """Sla data op in Redis cache met verschillende TTLs"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return False
        
    try:
        json_data = json.dumps(data)
        
        # TTL bepalen
        ttl_mapping = {
            CacheTTL.SHORT: CACHE_TTL_SHORT,
            CacheTTL.MEDIUM: CACHE_TTL_MEDIUM,
            CacheTTL.LONG: CACHE_TTL_LONG
        }
        expire_seconds = ttl_mapping.get(ttl_type, CACHE_TTL_SHORT)
        
        success = redis_client.setex(key, expire_seconds, json_data)
        logger.info(f"Cache set with TTL {ttl_type.value}: {success}")
        return success
    except Exception as e:
        logger.error(f"Cache set error: {str(e)}")
        return False

async def invalidate_cache(pattern: str = None):
    """Verwijder specifieke of alle cache entries"""
    if not redis_client:
        return
        
    try:
        if pattern:
            # Verwijder keys die matchen met pattern
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} keys matching {pattern}")
        else:
            # Verwijder alle keys
            redis_client.flushdb()
            logger.info("Cleared entire cache")
    except Exception as e:
        logger.error(f"Cache invalidation error: {str(e)}") 