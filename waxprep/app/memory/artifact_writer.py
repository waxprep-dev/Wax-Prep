import json
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger
from waxprep.app.database.client import get_db_client

class MemoryArtifactWriter:
    def __init__(self):
        self.db = get_db_client()

    async def write_artifact(
        self,
        student_id: str,
        artifact_type: str,
        content: str,
        relevance_tags: List[str] = None,
        impact_score: float = 0.5,
    ) -> None:
        try:
            existing = (
                self.db.table("memory_artifacts")
                .select("id, access_count")
                .eq("student_id", student_id)
                .eq("artifact_type", artifact_type)
                .ilike("content", f"%{content[:50]}%")
                .eq("status", "active")
                .execute()
            )

            if existing.data:
                self.db.table("memory_artifacts").update({
                    "last_accessed_at": datetime.utcnow().isoformat(),
                    "access_count": existing.data[0]["access_count"] + 1,
                }).eq("id", existing.data[0]["id"]).execute()
                return

            self.db.table("memory_artifacts").insert({
                "student_id": student_id,
                "artifact_type": artifact_type,
                "content": content,
                "relevance_tags": json.dumps(relevance_tags or []),
                "composite_score": 1.0,
                "recency_score": 1.0,
                "relevance_score": 1.0,
                "impact_score": impact_score,
                "uniqueness_score": 1.0,
                "status": "active",
            }).execute()

            logger.debug(f"Memory artifact written for {student_id}: {artifact_type}")

        except Exception as e:
            logger.warning(f"Failed to write memory artifact for {student_id}: {e}")

    async def write_personal_context(self, student_id: str, context: str) -> None:
        await self.write_artifact(
            student_id=student_id,
            artifact_type="personal_context",
            content=context,
            relevance_tags=["always_relevant", "emotional_support", "onboarding"],
            impact_score=0.9,
        )

    async def write_learning_preference(self, student_id: str, preference: str) -> None:
        await self.write_artifact(
            student_id=student_id,
            artifact_type="preference",
            content=preference,
            relevance_tags=["teaching_style", "communication"],
            impact_score=0.7,
        )

    async def write_milestone(self, student_id: str, milestone: str) -> None:
        await self.write_artifact(
            student_id=student_id,
            artifact_type="milestone",
            content=milestone,
            relevance_tags=["motivation", "progress"],
            impact_score=0.8,
        )

    async def write_emotional_note(self, student_id: str, note: str) -> None:
        await self.write_artifact(
            student_id=student_id,
            artifact_type="emotional_note",
            content=note,
            relevance_tags=["emotional_support", "wellbeing"],
            impact_score=0.85,
        )

    async def get_active_artifacts(
        self,
        student_id: str,
        limit: int = 10,
        artifact_type: str = None,
    ) -> List[Dict[str, Any]]:
        try:
            query = (
                self.db.table("memory_artifacts")
                .select("artifact_type, content, relevance_tags")
                .eq("student_id", student_id)
                .eq("status", "active")
                .order("composite_score", desc=True)
                .limit(limit)
            )

            if artifact_type:
                query = query.eq("artifact_type", artifact_type)

            response = query.execute()
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to get artifacts for {student_id}: {e}")
            return []

    async def build_memory_context_string(self, student_id: str) -> str:
        try:
            artifacts = await self.get_active_artifacts(student_id, limit=8)

            if not artifacts:
                return ""

            parts = []
            for artifact in artifacts:
                parts.append(artifact["content"])

            return " | ".join(parts)

        except Exception as e:
            logger.error(f"Failed to build memory context for {student_id}: {e}")
            return ""
