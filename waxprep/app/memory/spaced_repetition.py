import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

EASE_FACTOR_DEFAULT = 2.5
EASE_FACTOR_MIN = 1.3
EASE_FACTOR_MODIFIER_CORRECT = 0.1
EASE_FACTOR_MODIFIER_WRONG = -0.2
MINIMUM_INTERVAL_DAYS = 1

REVIEW_MESSAGE_PROMPT = """Generate a natural, brief spaced repetition review message from WaxPrep to a Nigerian student.

Rules:
Sound like a teacher who remembered something, not a notification system
Use the student's name
Reference the specific concept naturally
Ask one recall question about the concept
Keep it to 3 sentences maximum
Do not say "scheduled review" or "reminder" or anything robotic
Sound warm and natural

Student name: {name}
Concept to review: {concept}
Subject: {subject}
Days since it was taught: {days}

Review message:"""

class SpacedRepetitionEngine:
    def __init__(self):
        self.db = get_db_client()
        self.groq_client = Groq(api_key=settings.groq_api_key)

    async def update_after_review(
        self,
        student_id: str,
        concept_id: str,
        performance_score: float,
    ) -> None:
        try:
            response = (
                self.db.table("knowledge_maps")
                .select("*")
                .eq("student_id", student_id)
                .eq("concept_id", concept_id)
                .execute()
            )

            if not response.data:
                return

            record = response.data[0]
            params = record.get("forgetting_curve_params") or {}

            if isinstance(params, str):
                params = json.loads(params)

            ease_factor = params.get("ease_factor", EASE_FACTOR_DEFAULT)
            interval_days = params.get("interval_days", 1)
            repetitions = params.get("repetitions", 0)

            if performance_score >= 0.6:
                if repetitions == 0:
                    new_interval = 1
                elif repetitions == 1:
                    new_interval = 6
                else:
                    new_interval = round(interval_days * ease_factor)

                new_ease = max(EASE_FACTOR_MIN, ease_factor + EASE_FACTOR_MODIFIER_CORRECT + (0.1 * (performance_score - 0.6)))
                new_repetitions = repetitions + 1
                new_mastery = min(100, record["mastery_score"] + (performance_score * 15))

            else:
                new_interval = 1
                new_ease = max(EASE_FACTOR_MIN, ease_factor + EASE_FACTOR_MODIFIER_WRONG)
                new_repetitions = 0
                new_mastery = max(0, record["mastery_score"] - 10)

            next_review = datetime.utcnow() + timedelta(days=new_interval)

            self.db.table("knowledge_maps").update({
                "mastery_score": round(new_mastery, 2),
                "last_assessed_at": datetime.utcnow().isoformat(),
                "assessment_count": record["assessment_count"] + 1,
                "last_assessment_performance": performance_score,
                "next_review_due_at": next_review.isoformat(),
                "forgetting_curve_params": json.dumps({
                    "ease_factor": round(new_ease, 3),
                    "interval_days": new_interval,
                    "repetitions": new_repetitions,
                }),
            }).eq("student_id", student_id).eq("concept_id", concept_id).execute()

            logger.debug(f"Spaced rep updated: {student_id} | {concept_id} | next review in {new_interval} days")

        except Exception as e:
            logger.error(f"Failed to update spaced rep for {student_id}/{concept_id}: {e}")

    async def get_due_reviews(
        self,
        student_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            response = (
                self.db.table("knowledge_maps")
                .select("concept_id, subject, mastery_score, next_review_due_at, last_assessed_at")
                .eq("student_id", student_id)
                .lte("next_review_due_at", datetime.utcnow().isoformat())
                .order("next_review_due_at", desc=False)
                .limit(limit)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Failed to get due reviews for {student_id}: {e}")
            return []

    async def schedule_review_notifications(self, student_id: str, platform: str) -> int:
        try:
            profile_response = (
                self.db.table("student_profiles")
                .select("student_name")
                .eq("student_id", student_id)
                .execute()
            )

            name = "there"
            if profile_response.data and profile_response.data[0].get("student_name"):
                name = profile_response.data[0]["student_name"]

            due_reviews = await self.get_due_reviews(student_id, limit=3)

            scheduled_count = 0
            for review in due_reviews:
                pending = (
                    self.db.table("scheduled_notifications")
                    .select("id")
                    .eq("student_id", student_id)
                    .eq("related_concept_id", review["concept_id"])
                    .eq("status", "pending")
                    .execute()
                )

                if pending.data:
                    continue

                message = await self._generate_review_message(
                    name=name,
                    concept=review["concept_id"].replace("_", " "),
                    subject=review["subject"],
                    last_assessed_at=review.get("last_assessed_at"),
                )

                if message:
                    self.db.table("scheduled_notifications").insert({
                        "student_id": student_id,
                        "notification_type": "spaced_rep_review",
                        "scheduled_for": datetime.utcnow().isoformat(),
                        "platform": platform,
                        "content": message,
                        "status": "pending",
                        "related_concept_id": review["concept_id"],
                    }).execute()
                    scheduled_count += 1

            return scheduled_count

        except Exception as e:
            logger.error(f"Failed to schedule review notifications for {student_id}: {e}")
            return 0

    async def _generate_review_message(
        self,
        name: str,
        concept: str,
        subject: str,
        last_assessed_at: str = None,
    ) -> Optional[str]:
        try:
            days = 3
            if last_assessed_at:
                try:
                    assessed = datetime.fromisoformat(last_assessed_at.replace("Z", "+00:00"))
                    days = (datetime.utcnow().replace(tzinfo=assessed.tzinfo) - assessed).days
                except Exception:
                    days = 3

            prompt = REVIEW_MESSAGE_PROMPT.format(
                name=name,
                concept=concept,
                subject=subject,
                days=days,
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate review message: {e}")
            return None
