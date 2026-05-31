from typing import Optional
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.cache.redis_client import cache_set, cache_exists, dedup_key, DEDUP_TTL
from waxprep.app.database.client import get_db_client

class DeduplicationCache:
    def __init__(self):
        self.db = get_db_client()

    async def is_duplicate(self, message_id: str) -> bool:
        redis_result = await cache_exists(dedup_key(message_id))
        if redis_result:
            return True

        try:
            response = (
                self.db.table("message_dedup")
                .select("platform_message_id")
                .eq("platform_message_id", message_id)
                .execute()
            )
            if response.data:
                await cache_set(dedup_key(message_id), True, DEDUP_TTL)
                return True
        except Exception:
            pass

        return False

    async def mark_processed(self, message_id: str, student_id: Optional[str] = None) -> None:
        await cache_set(dedup_key(message_id), True, DEDUP_TTL)

        try:
            expires_at = datetime.utcnow() + timedelta(seconds=DEDUP_TTL + 60)
            self.db.table("message_dedup").insert({
                "platform_message_id": message_id,
                "student_id": student_id,
                "expires_at": expires_at.isoformat(),
            }).execute()
        except Exception:
            pass
