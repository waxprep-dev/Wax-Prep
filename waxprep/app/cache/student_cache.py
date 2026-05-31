from typing import Optional, Dict, Any
from loguru import logger
from waxprep.app.cache.redis_client import (
    cache_get, cache_set, cache_delete,
    student_profile_key, knowledge_map_key, STUDENT_PROFILE_TTL, KNOWLEDGE_MAP_TTL
)
from waxprep.app.database.client import get_db_client

class StudentCache:
    def __init__(self):
        self.db = get_db_client()

    async def get_student_profile(self, student_id: str) -> Optional[Dict[str, Any]]:
        cached = await cache_get(student_profile_key(student_id))
        if cached is not None:
            return cached

        try:
            response = (
                self.db.table("student_profiles")
                .select("*")
                .eq("student_id", student_id)
                .execute()
            )

            if response.data:
                profile = response.data[0]
                await cache_set(student_profile_key(student_id), profile, STUDENT_PROFILE_TTL)
                return profile

            return None

        except Exception as e:
            logger.error(f"Failed to get profile for {student_id}: {e}")
            return None

    async def update_student_profile(self, student_id: str, updates: Dict[str, Any]) -> None:
        try:
            self.db.table("student_profiles").update(updates).eq("student_id", student_id).execute()
            await cache_delete(student_profile_key(student_id))
        except Exception as e:
            logger.error(f"Failed to update profile for {student_id}: {e}")

    async def get_knowledge_map(self, student_id: str) -> list:
        cached = await cache_get(knowledge_map_key(student_id))
        if cached is not None:
            return cached

        try:
            response = (
                self.db.table("knowledge_maps")
                .select("concept_id, subject, mastery_score, next_review_due_at")
                .eq("student_id", student_id)
                .order("mastery_score", desc=True)
                .limit(15)
                .execute()
            )

            data = response.data or []
            await cache_set(knowledge_map_key(student_id), data, KNOWLEDGE_MAP_TTL)
            return data

        except Exception as e:
            logger.error(f"Failed to get knowledge map for {student_id}: {e}")
            return []

    async def invalidate_knowledge_map(self, student_id: str) -> None:
        await cache_delete(knowledge_map_key(student_id))
