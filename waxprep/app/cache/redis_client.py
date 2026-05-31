import json
from typing import Any, Optional, Dict
from loguru import logger
import redis.asyncio as aioredis
from waxprep.app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None

async def get_redis() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} — running without cache")
            _redis_client = None
    return _redis_client

async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    try:
        redis = await get_redis()
        if redis is None:
            return False
        serialized = json.dumps(value, default=str)
        await redis.setex(key, ttl_seconds, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache set failed for {key}: {e}")
        return False

async def cache_get(key: str) -> Optional[Any]:
    try:
        redis = await get_redis()
        if redis is None:
            return None
        raw = await redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Cache get failed for {key}: {e}")
        return None

async def cache_delete(key: str) -> bool:
    try:
        redis = await get_redis()
        if redis is None:
            return False
        await redis.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete failed for {key}: {e}")
        return False

async def cache_exists(key: str) -> bool:
    try:
        redis = await get_redis()
        if redis is None:
            return False
        return bool(await redis.exists(key))
    except Exception as e:
        return False

STUDENT_PROFILE_TTL = 600
SESSION_STATE_TTL = 1800
KNOWLEDGE_MAP_TTL = 3600
DEDUP_TTL = 120
CONVERSATION_CONTEXT_TTL = 1800

def student_profile_key(student_id: str) -> str:
    return f"wax:profile:{student_id}"

def session_state_key(student_id: str, platform: str) -> str:
    return f"wax:session:{student_id}:{platform}"

def knowledge_map_key(student_id: str) -> str:
    return f"wax:km:{student_id}"

def dedup_key(message_id: str) -> str:
    return f"wax:dedup:{message_id}"

def conversation_key(conversation_id: str) -> str:
    return f"wax:conv:{conversation_id}"

def frustration_key(student_id: str) -> str:
    return f"wax:frustration:{student_id}"
