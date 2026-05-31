import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from waxprep.app.database.client import get_db_client

class LearningEventLogger:
    def __init__(self):
        self.db = get_db_client()

    async def log_event(
        self,
        student_id: str,
        event_type: str,
        session_id: str,
        concept_id: str = None,
        subject: str = None,
        class_level: str = None,
        details: Dict[str, Any] = None,
    ) -> None:
        try:
            self.db.table("learning_events").insert({
                "student_id": student_id,
                "event_type": event_type,
                "concept_id": concept_id,
                "subject": subject,
                "class_level": class_level,
                "details": json.dumps(details or {}),
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log learning event for {student_id}: {e}")

    async def log_message_exchange(
        self,
        student_id: str,
        session_id: str,
        intent: str,
        student_message: str,
        waxprep_response: str,
        subject: str = None,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="message_exchange",
            session_id=session_id,
            subject=subject,
            details={
                "intent": intent,
                "student_message_length": len(student_message),
                "response_length": len(waxprep_response),
                "student_message_preview": student_message[:100],
            }
        )

    async def log_teaching_moment(
        self,
        student_id: str,
        session_id: str,
        concept: str,
        subject: str,
        teaching_strategy: str,
        outcome: str,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="teaching_moment",
            session_id=session_id,
            concept_id=concept.lower().replace(" ", "_"),
            subject=subject,
            details={
                "teaching_strategy": teaching_strategy,
                "outcome": outcome,
                "concept_name": concept,
            }
        )

    async def log_misconception_detected(
        self,
        student_id: str,
        session_id: str,
        concept: str,
        misconception: str,
        subject: str,
        corrected: bool,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="misconception_detected" if not corrected else "misconception_corrected",
            session_id=session_id,
            concept_id=concept.lower().replace(" ", "_"),
            subject=subject,
            details={
                "concept": concept,
                "misconception_description": misconception,
                "corrected_in_session": corrected,
            }
        )

    async def log_session_started(
        self,
        student_id: str,
        session_id: str,
        is_returning: bool,
        days_since_last: int = 0,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="session_started",
            session_id=session_id,
            details={
                "is_returning_student": is_returning,
                "days_since_last_session": days_since_last,
            }
        )

    async def log_session_ended(
        self,
        student_id: str,
        session_id: str,
        message_count: int,
        topics_covered: List[str],
        duration_minutes: int,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="session_ended",
            session_id=session_id,
            details={
                "message_count": message_count,
                "topics_covered": topics_covered,
                "duration_minutes": duration_minutes,
            }
        )

    async def log_emotional_moment(
        self,
        student_id: str,
        session_id: str,
        emotional_state: str,
        trigger: str,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="emotional_moment",
            session_id=session_id,
            details={
                "emotional_state": emotional_state,
                "trigger_summary": trigger[:200],
            }
        )

    async def log_name_captured(
        self,
        student_id: str,
        session_id: str,
        name: str,
    ) -> None:
        await self.log_event(
            student_id=student_id,
            event_type="name_captured",
            session_id=session_id,
            details={"name": name}
        )

    async def get_student_recent_events(
        self,
        student_id: str,
        limit: int = 20,
        event_type: str = None,
    ) -> List[Dict[str, Any]]:
        try:
            query = (
                self.db.table("learning_events")
                .select("*")
                .eq("student_id", student_id)
                .order("timestamp", desc=True)
                .limit(limit)
            )

            if event_type:
                query = query.eq("event_type", event_type)

            response = query.execute()
            return response.data or []

        except Exception as e:
            logger.error(f"Failed to get events for {student_id}: {e}")
            return []
