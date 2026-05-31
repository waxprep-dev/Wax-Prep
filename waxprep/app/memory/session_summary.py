import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

SESSION_SUMMARY_PROMPT = """You are summarizing a WaxPrep teaching session for a Nigerian student.
Write ONE paragraph (not bullet points) that a teacher would use to resume teaching this student seamlessly in the next session. Include:
What subject and specific topics were covered
What the student understood well and what confused them
Any misconceptions that came up and whether corrected
The student's emotional state and engagement level
Any personal context the student shared
The natural next step for the next session
Any promises made ("we will continue with X next time")
This summary is read by an AI at the start of the next conversation. Make it information-dense and pedagogically useful.
Conversation:
"""

RETURN_GREETING_PROMPT = """Based on this previous session summary, write a natural opening message from WaxPrep to this returning student.
Student name: {name}
Days since last session: {days}
Previous session summary: {summary}
Rules:
Use the student's name
Reference what was covered last time naturally, like a real teacher would
NEVER say "Welcome back" or "I'm glad you're back" or "I noticed you haven't been studying"
Jump into the learning naturally — a question about the last topic, or a quick recap challenge
Maximum 3 sentences
Sound warm and natural — not robotic
If it has been more than 5 days, acknowledge briefly that some time has passed without guilt-tripping
Opening message:"""

class SessionSummaryGenerator:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()

    async def generate_and_save_session_summary(self, conversation_id: str, student_id: str, student_wax_code: str = "UNKNOWN") -> Optional[str]:
        try:
            messages_response = self.db.table("messages").select("direction, content, timestamp").eq("conversation_id", conversation_id).order("timestamp", desc=False).execute()
            if not messages_response.data or len(messages_response.data) < 3:
                self.db.table("conversations").update({"is_active": False, "ended_at": datetime.utcnow().isoformat()}).eq("id", conversation_id).execute()
                return None

            conversation_text = []
            for msg in messages_response.data:
                role = "Student" if msg["direction"] == "inbound" else "WaxPrep"
                conversation_text.append(f"{role}: {msg['content']}")

            full_text = "\n".join(conversation_text)
            summary = None

            for attempt in range(3):
                try:
                    response = self.groq_client.chat.completions.create(
                        model=settings.groq_fast_model or "llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": SESSION_SUMMARY_PROMPT + full_text[:6000]}],
                        max_tokens=400, temperature=0.3,
                    )
                    summary = response.choices[0].message.content.strip()
                    break
                except Exception as e:
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(2)
                    else:
                        logger.warning(f"Summary generation failed after 3 attempts: {e}")

            self.db.table("conversations").update({"summary": summary, "is_active": False, "ended_at": datetime.utcnow().isoformat()}).eq("id", conversation_id).execute()

            if summary:
                try:
                    from waxprep.app.data.fine_tuning_pipeline import FineTuningPipeline
                    pipeline = FineTuningPipeline()
                    extracted = await pipeline.extract_from_session(conversation_id=conversation_id, student_wax_code=student_wax_code)
                    if extracted > 0:
                        logger.info(f"Fine-tuning: extracted {extracted} samples from {conversation_id}")
                except Exception as e:
                    logger.debug(f"Fine-tuning extraction skipped: {e}")

            logger.info(f"Session summary generated for {conversation_id}")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            return None

    async def generate_return_greeting(self, student_id: str) -> Optional[str]:
        try:
            profile_response = self.db.table("student_profiles").select("student_name, emotional_state_current").eq("student_id", student_id).execute()
            name = "there"
            if profile_response.data and profile_response.data[0].get("student_name"):
                name = profile_response.data[0]["student_name"]

            summary_response = self.db.table("conversations").select("summary, ended_at").eq("student_id", student_id).eq("is_active", False).not_.is_("summary", "null").order("ended_at", desc=True).limit(1).execute()
            if not summary_response.data or not summary_response.data[0].get("summary"):
                return None

            last_session = summary_response.data[0]
            summary = last_session["summary"]
            days_since = 0
            if last_session.get("ended_at"):
                try:
                    ended = datetime.fromisoformat(last_session["ended_at"].replace("Z", "+00:00"))
                    days_since = (datetime.utcnow().replace(tzinfo=ended.tzinfo) - ended).days
                except Exception:
                    days_since = 1

            prompt = RETURN_GREETING_PROMPT.format(name=name, days=days_since, summary=summary[:600])

            for attempt in range(3):
                try:
                    response = self.groq_client.chat.completions.create(
                        model=settings.groq_fast_model or "llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150, temperature=0.7,
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(1)
                    else:
                        logger.warning(f"Return greeting generation failed: {e}")
                        return None
        except Exception as e:
            logger.error(f"Failed to generate return greeting for {student_id}: {e}")
            return None

    async def check_and_close_inactive_sessions(self) -> int:
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=settings.session_timeout_minutes or 30)
            stale_sessions = self.db.table("conversations").select("id, student_id").eq("is_active", True).lt("last_message_at", timeout_threshold.isoformat()).execute()
            closed_count = 0
            for session in (stale_sessions.data or []):
                student_data = self.db.table("students").select("wax_code").eq("id", session["student_id"]).execute()
                wax_code = student_data.data[0]["wax_code"] if student_data.data else "UNKNOWN"
                await self.generate_and_save_session_summary(conversation_id=session["id"], student_id=session["student_id"], student_wax_code=wax_code)
                closed_count += 1
            return closed_count
        except Exception as e:
            logger.error(f"Failed to close inactive sessions: {e}")
            return 0
