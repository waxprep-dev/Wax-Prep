import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

STUDY_PLAN_PROMPT = """You are WaxPrep creating a personalized study plan for a Nigerian student preparing for an exam.

Student name: {name}
Exam: {exam}
Days until exam: {days}
Class level: {class_level}
Subjects to cover: {subjects}
Known weak areas: {weak_areas}
Known strong areas: {strong_areas}
Daily study time available: {daily_hours} hours

Create a realistic, weekly study plan. Be specific about what to study each day. Consider:
WAEC/JAMB topic frequency — high frequency topics first
The student's weaknesses — more time on those
Spaced repetition — revisit topics regularly
Rest days — the brain needs consolidation time

Write the plan conversationally, the way WaxPrep talks. Not as a formal schedule document but as a natural recommendation from a caring teacher. Keep it to 400 words maximum.

Study plan:"""

EXAM_DAY_MESSAGE_PROMPT = """Write a short, warm, encouraging message from WaxPrep to {name} on the day before their {exam} exam.

Rules:
Acknowledge the hard work they have put in
Give 3-4 practical exam day tips
Keep it warm, not robotic
Maximum 200 words
Sound like WaxPrep — natural Nigerian teacher voice
End with genuine encouragement, not hollow "you've got this" type phrases

Message:"""

class ExamCountdownManager:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()

    async def activate_countdown_mode(
        self,
        student_id: str,
        exam: str,
        exam_date: str,
    ) -> None:
        try:
            self.db.table("students").update({
                "primary_exam_target": exam,
                "exam_date": exam_date,
            }).eq("id", student_id).execute()

            await self._schedule_countdown_notifications(student_id, exam, exam_date)

            logger.info(f"Exam countdown activated for {student_id}: {exam} on {exam_date}")

        except Exception as e:
            logger.error(f"Failed to activate countdown mode: {e}")

    async def generate_study_plan(
        self,
        student_id: str,
        exam: str,
        exam_date: str,
        subjects: List[str],
    ) -> Optional[str]:
        try:
            profile = self.db.table("student_profiles").select("*").eq("student_id", student_id).execute()
            student = self.db.table("students").select("*").eq("id", student_id).execute()

            name = "there"
            weak_areas = []
            strong_areas = []
            class_level = "SS3"

            if profile.data:
                name = profile.data[0].get("student_name", "there")
                weak_areas_raw = profile.data[0].get("weak_subjects", "[]")
                if isinstance(weak_areas_raw, str):
                    weak_areas = json.loads(weak_areas_raw) if weak_areas_raw else []
                strong_areas_raw = profile.data[0].get("strong_subjects", "[]")
                if isinstance(strong_areas_raw, str):
                    strong_areas = json.loads(strong_areas_raw) if strong_areas_raw else []

            if student.data:
                class_level = student.data[0].get("inferred_class_level", "SS3")

            exam_dt = datetime.fromisoformat(exam_date)
            days_until = max(1, (exam_dt - datetime.utcnow()).days)

            knowledge_response = (
                self.db.table("knowledge_maps")
                .select("concept_id, mastery_score, subject")
                .eq("student_id", student_id)
                .lt("mastery_score", 50)
                .order("mastery_score", desc=False)
                .limit(10)
                .execute()
            )

            if knowledge_response.data:
                weak_areas.extend([k["concept_id"].replace("_", " ") for k in knowledge_response.data])

            prompt = STUDY_PLAN_PROMPT.format(
                name=name,
                exam=exam,
                days=days_until,
                class_level=class_level,
                subjects=", ".join(subjects),
                weak_areas=", ".join(weak_areas[:8]) if weak_areas else "not yet identified",
                strong_areas=", ".join(strong_areas[:5]) if strong_areas else "not yet identified",
                daily_hours=2,
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_primary_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.5,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Failed to generate study plan for {student_id}: {e}")
            return None

    async def get_countdown_message(self, student_id: str) -> Optional[str]:
        try:
            student = self.db.table("students").select("exam_date, primary_exam_target").eq("id", student_id).execute()
            profile = self.db.table("student_profiles").select("student_name").eq("student_id", student_id).execute()

            if not student.data or not student.data[0].get("exam_date"):
                return None

            name = profile.data[0].get("student_name", "there") if profile.data else "there"
            exam = student.data[0].get("primary_exam_target", "exam")
            exam_date_str = student.data[0]["exam_date"]

            exam_dt = datetime.fromisoformat(exam_date_str)
            days_until = (exam_dt - datetime.utcnow()).days

            if days_until == 0:
                return await self._generate_exam_day_message(name, exam)
            elif days_until == 1:
                return await self._generate_day_before_message(name, exam)
            elif days_until == 7:
                return f"{name}, one week to {exam}. This is the time to focus on your strongest topics to build confidence, and run through practice questions on your weak spots one more time. What do you want to drill today?"
            elif days_until == 30:
                return f"{name}, one month to {exam}. Perfect time to do a diagnostic — let's figure out exactly what gaps are left so we can target the right things. Where do you feel least ready right now?"
            elif days_until == 90:
                return f"{name}, 90 days to {exam}. That is enough time to genuinely turn this around if we are smart about it. Want me to put together a proper study plan for you?"

            return None

        except Exception as e:
            logger.error(f"Failed to get countdown message: {e}")
            return None

    async def _generate_exam_day_message(self, name: str, exam: str) -> str:
        try:
            prompt = EXAM_DAY_MESSAGE_PROMPT.format(name=name, exam=exam)
            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"{name}, today is the day. Everything you have studied is with you. Read each question carefully before answering. Show all working in maths. Trust yourself."

    async def _generate_day_before_message(self, name: str, exam: str) -> str:
        return (
            f"{name}, tomorrow is {exam}. No heavy studying tonight — your brain needs to consolidate. "
            f"Do a light review of your notes, prepare your stationery and ID tonight so there's no rush in the morning. "
            f"Sleep at a reasonable time. You have put in the work. Tomorrow is just the demonstration."
        )

    async def _schedule_countdown_notifications(
        self,
        student_id: str,
        exam: str,
        exam_date: str,
    ) -> None:
        try:
            student = self.db.table("students").select("platform_whatsapp, platform_telegram").eq("id", student_id).execute()
            if not student.data:
                return

            platform = "whatsapp" if student.data[0].get("platform_whatsapp") else "telegram"
            exam_dt = datetime.fromisoformat(exam_date)

            notification_days = [90, 60, 30, 14, 7, 3, 1, 0]

            for days_before in notification_days:
                notif_date = exam_dt - timedelta(days=days_before)
                if notif_date > datetime.utcnow():
                    self.db.table("scheduled_notifications").insert({
                        "student_id": student_id,
                        "notification_type": "exam_countdown",
                        "scheduled_for": notif_date.isoformat(),
                        "platform": platform,
                        "content": f"GENERATE_COUNTDOWN_MESSAGE:{days_before}",
                        "status": "pending",
                    }).execute()

        except Exception as e:
            logger.warning(f"Failed to schedule countdown notifications: {e}")
