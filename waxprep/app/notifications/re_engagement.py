import json
from typing import Optional, List
from datetime import datetime, timedelta
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

RE_ENGAGEMENT_PROMPT = """Generate a re-engagement message from WaxPrep to a Nigerian student who has been inactive.

Student name: {name}
Days inactive: {days}
Last topic studied: {topic}
Last subject: {subject}
Student's exam target: {exam}
Personal context to be aware of: {context}

Rules:
Do not say "I noticed you haven't been studying" — too surveillance-like
Do not guilt-trip the student
Do not say "Welcome back" — they haven't responded yet
Reference what they were working on naturally
Make it feel like the teacher just thought of them
Keep it to 2-3 sentences
End with an easy re-entry question, not pressure

Message:"""

class ReEngagementSystem:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()

    async def find_and_schedule_re_engagements(self) -> int:
        try:
            threshold_5_days = datetime.utcnow() - timedelta(days=5)
            threshold_14_days = datetime.utcnow() - timedelta(days=14)

            inactive_students = (
                self.db.table("students")
                .select("id, platform_whatsapp, platform_telegram, last_active_at, primary_exam_target")
                .eq("status", "active")
                .lt("last_active_at", threshold_5_days.isoformat())
                .gt("last_active_at", threshold_14_days.isoformat())
                .execute()
            )

            if not inactive_students.data:
                return 0

            scheduled = 0
            for student in inactive_students.data:
                already_pending = (
                    self.db.table("scheduled_notifications")
                    .select("id")
                    .eq("student_id", student["id"])
                    .eq("notification_type", "re_engagement")
                    .eq("status", "pending")
                    .execute()
                )

                if already_pending.data:
                    continue

                message = await self._generate_re_engagement_message(student["id"])
                if message:
                    platform = "whatsapp" if student.get("platform_whatsapp") else "telegram"
                    self.db.table("scheduled_notifications").insert({
                        "student_id": student["id"],
                        "notification_type": "re_engagement",
                        "scheduled_for": datetime.utcnow().isoformat(),
                        "platform": platform,
                        "content": message,
                        "status": "pending",
                    }).execute()
                    scheduled += 1

            logger.info(f"Scheduled {scheduled} re-engagement messages")
            return scheduled

        except Exception as e:
            logger.error(f"Re-engagement scheduling failed: {e}")
            return 0

    async def _generate_re_engagement_message(self, student_id: str) -> Optional[str]:
        try:
            profile = self.db.table("student_profiles").select("*").eq("student_id", student_id).execute()
            student = self.db.table("students").select("primary_exam_target, last_active_at").eq("id", student_id).execute()

            name = "there"
            topic = None
            subject = None
            context = None
            exam = None

            if profile.data:
                name = profile.data[0].get("student_name", "there")
                topic = profile.data[0].get("current_topic")
                subject = profile.data[0].get("current_subject")
                context = profile.data[0].get("personal_context")

            if student.data:
                exam = student.data[0].get("primary_exam_target")
                last_active_str = student.data[0].get("last_active_at", "")
                if last_active_str:
                    last_active = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                    days = (datetime.utcnow().replace(tzinfo=last_active.tzinfo) - last_active).days
                else:
                    days = 7
            else:
                days = 7

            prompt = RE_ENGAGEMENT_PROMPT.format(
                name=name,
                days=days,
                topic=topic or "your last topic",
                subject=subject or "your subject",
                exam=exam or "your exam",
                context=context or "none",
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate re-engagement message: {e}")
            return None
