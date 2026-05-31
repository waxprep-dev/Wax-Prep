from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.core.config import settings
from waxprep.app.core.constants import MessageDirection
from waxprep.app.database.client import get_db_client


class ConversationHistoryManager:

    def __init__(self):
        self.db = get_db_client()

    async def get_or_create_active_conversation(
        self,
        student_id: str,
        platform: str
    ) -> Dict[str, Any]:
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=settings.session_timeout_minutes)

            response = (
                self.db.table("conversations")
                .select("*")
                .eq("student_id", student_id)
                .eq("is_active", True)
                .eq("platform", platform)
                .gte("last_message_at", timeout_threshold.isoformat())
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]

            new_conversation = {
                "student_id": student_id,
                "platform": platform,
                "session_state": "onboarding",
                "is_active": True,
            }

            result = self.db.table("conversations").insert(new_conversation).execute()
            if result.data:
                return result.data[0]

            raise Exception("Failed to create conversation")

        except Exception as e:
            logger.error(f"Error in get_or_create_active_conversation: {e}")
            raise

    async def save_message(
        self,
        conversation_id: str,
        student_id: str,
        direction: str,
        content: str,
        message_type: str = "text",
        intent: str = None,
        platform_message_id: str = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        try:
            message_data = {
                "conversation_id": conversation_id,
                "student_id": student_id,
                "direction": direction,
                "content": content,
                "message_type": message_type,
                "intent_classified": intent,
                "platform_message_id": platform_message_id,
                "metadata": metadata or {},
            }

            result = self.db.table("messages").insert(message_data).execute()

            # Update conversation last_message_at and increment count
            self.db.table("conversations").update({
                "last_message_at": datetime.utcnow().isoformat(),
                "message_count": self.db.table("messages")
                    .select("id", count="exact")
                    .eq("conversation_id", conversation_id)
                    .execute()
                    .count
            }).eq("id", conversation_id).execute()

            if result.data:
                return result.data[0]
            return {}

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return {}

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        try:
            response = (
                self.db.table("messages")
                .select("direction, content, message_type, timestamp, intent_classified")
                .eq("conversation_id", conversation_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )

            if response.data:
                return list(reversed(response.data))
            return []

        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []

    async def get_conversation_history_for_ai(
        self,
        conversation_id: str,
        limit: int = 15
    ) -> List[Dict[str, str]]:
        messages = await self.get_recent_messages(conversation_id, limit)

        ai_history = []
        for msg in messages:
            role = "user" if msg["direction"] == MessageDirection.INBOUND.value else "assistant"
            ai_history.append({
                "role": role,
                "content": msg["content"]
            })

        return ai_history

    async def update_conversation_state(
        self,
        conversation_id: str,
        session_state: str
    ) -> None:
        try:
            self.db.table("conversations").update({
                "session_state": session_state
            }).eq("id", conversation_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update conversation state: {e}")

    async def get_previous_session_summary(self, student_id: str) -> Optional[str]:
        try:
            response = (
                self.db.table("conversations")
                .select("summary, topics_covered, session_state, ended_at")
                .eq("student_id", student_id)
                .eq("is_active", False)
                .order("ended_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data and response.data[0].get("summary"):
                return response.data[0]["summary"]
            return None

        except Exception as e:
            logger.error(f"Error getting previous session summary: {e}")
            return None
