import json
from typing import Dict, Any, Optional, List
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client
from datetime import datetime

EXTRACTION_PROMPT = """You are analyzing a conversation between WaxPrep (an AI teacher) and a Nigerian student. Extract structured information from the conversation.

Return ONLY a valid JSON object with these exact fields. Use null for fields you cannot determine. Do not add any text before or after the JSON.

{
  "student_name": "string or null — first name the student shared or asked to be called",
  "class_level": "string or null — one of: JSS1, JSS2, JSS3, SS1, SS2, SS3, UNI_100, UNI_200, UNI_300, UNI_400",
  "exam_target": "string or null — one of: WAEC, NECO, JAMB, POST_UTME, BECE",
  "primary_subjects": ["array of subject strings the student mentioned needing help with"],
  "weak_subjects": ["array of subjects the student said they struggle with"],
  "current_topic": "string or null — the most recent topic being discussed",
  "current_subject": "string or null — the subject area of current discussion",
  "emotional_state": "string or null — one of: neutral, frustrated, anxious, discouraged, motivated, confident",
  "personal_context": "string or null — important personal context (e.g. out of school 4 years, single parent, etc.)",
  "language_register": "string or null — one of: formal, semi_formal, informal, pidgin_heavy",
  "preferred_message_length": "string or null — one of: short, medium, long",
    "voice_preferred": "boolean or null — true if student wants voice responses instead of text",
  "years_out_of_school": "integer or null",
  "has_exam_coming": true or false,
  "concepts_discussed": ["array of specific concepts taught in this conversation"],
  "misconceptions_detected": [
    {
      "concept": "string",
      "misconception": "string — what the student wrongly believed",
      "corrected": true or false
    }
  ],
  "concepts_mastered": ["array of concepts the student demonstrated clear understanding of"],
  "concepts_confused": ["array of concepts the student was unclear about"]
}

Conversation to analyze:
"""

class ProfileIntelligenceExtractor:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()

    async def extract_and_update(
        self,
        student_id: str,
        conversation_history: List[Dict[str, str]],
        run_full_extraction: bool = False
    ) -> Dict[str, Any]:

        if len(conversation_history) < 3 and not run_full_extraction:
            return {}

        if len(conversation_history) % 5 != 0 and not run_full_extraction:
            return {}

        try:
            conversation_text = self._format_conversation(conversation_history)
            extracted = await self._extract_from_conversation(conversation_text)

            if extracted:
                await self._update_student_profile(student_id, extracted)
                await self._log_misconceptions(student_id, extracted)
                await self._log_concepts_to_knowledge_map(student_id, extracted)

            return extracted

        except Exception as e:
            logger.error(f"Profile extraction failed for {student_id}: {e}")
            return {}

    def _format_conversation(self, history: List[Dict[str, str]]) -> str:
        lines = []
        for msg in history:
            role = "Student" if msg["role"] == "user" else "WaxPrep"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    async def _extract_from_conversation(self, conversation_text: str) -> Optional[Dict[str, Any]]:
        try:
            prompt = EXTRACTION_PROMPT + conversation_text

            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()

            raw = raw.replace("```json", "").replace("```", "").strip()
            extracted = json.loads(raw)
            return extracted

        except json.JSONDecodeError as e:
            logger.warning(f"Profile extraction JSON parse failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Profile extraction AI call failed: {e}")
            return None

    async def _update_student_profile(self, student_id: str, extracted: Dict[str, Any]) -> None:
        try:
            profile_updates = {}
            student_updates = {}

            if extracted.get("student_name"):
                profile_updates["student_name"] = extracted["student_name"]

            if extracted.get("class_level"):
                student_updates["inferred_class_level"] = extracted["class_level"]

            if extracted.get("exam_target"):
                student_updates["primary_exam_target"] = extracted["exam_target"]

            if extracted.get("emotional_state"):
                profile_updates["emotional_state_current"] = extracted["emotional_state"]

            if extracted.get("language_register"):
                profile_updates["language_register"] = extracted["language_register"]

            if extracted.get("preferred_message_length"):
                profile_updates["preferred_message_length"] = extracted["preferred_message_length"]

            if extracted.get("voice_preferred") is not None:
                profile_updates["voice_preferred"] = extracted["voice_preferred"]

            if extracted.get("current_topic"):
                profile_updates["current_topic"] = extracted["current_topic"]

            if extracted.get("current_subject"):
                profile_updates["current_subject"] = extracted["current_subject"]

            if extracted.get("primary_subjects"):
                profile_updates["primary_subjects"] = json.dumps(extracted["primary_subjects"])

            if extracted.get("weak_subjects"):
                profile_updates["weak_subjects"] = json.dumps(extracted["weak_subjects"])

            # Local voice preference detection (catches "respond with voice" even if AI misses it)
            if "voice_preferred" not in profile_updates:
                try:
                    from waxprep.app.ai.subject_detector import detect_voice_preference
                    voice_pref = detect_voice_preference(extracted.get("last_message", ""))
                    if voice_pref is not None:
                        profile_updates["voice_preferred"] = voice_pref
                        logger.info(f"Voice preference detected locally: {voice_pref} for {student_id}")
                except Exception:
                    pass

            if extracted.get("personal_context"):
                profile_updates["personal_context"] = extracted["personal_context"]

            if profile_updates:
                self.db.table("student_profiles").update(profile_updates).eq("student_id", student_id).execute()
                logger.debug(f"Profile updated for {student_id}: {list(profile_updates.keys())}")

            if student_updates:
                self.db.table("students").update(student_updates).eq("id", student_id).execute()
                logger.debug(f"Student record updated for {student_id}: {list(student_updates.keys())}")

        except Exception as e:
            logger.error(f"Failed to update profile for {student_id}: {e}")

    async def _log_misconceptions(self, student_id: str, extracted: Dict[str, Any]) -> None:
        misconceptions = extracted.get("misconceptions_detected", [])
        if not misconceptions:
            return

        try:
            for m in misconceptions:
                if not m.get("concept") or not m.get("misconception"):
                    continue

                misconception_code = m["concept"].lower().replace(" ", "_") + "_misconception"
                subject = extracted.get("current_subject", "general")

                existing = (
                    self.db.table("misconceptions")
                    .select("id, status, correction_attempts")
                    .eq("student_id", student_id)
                    .eq("misconception_code", misconception_code)
                    .execute()
                )

                if existing.data:
                    existing_record = existing.data[0]
                    new_status = "resolved" if m.get("corrected") else "active"
                    new_attempts = existing_record["correction_attempts"] + (1 if m.get("corrected") else 0)

                    self.db.table("misconceptions").update({
                        "status": new_status,
                        "correction_attempts": new_attempts,
                        "last_confirmed_at": datetime.utcnow().isoformat(),
                    }).eq("id", existing_record["id"]).execute()

                else:
                    self.db.table("misconceptions").insert({
                        "student_id": student_id,
                        "subject": subject,
                        "concept_id": m["concept"].lower().replace(" ", "_"),
                        "misconception_code": misconception_code,
                        "description": m["misconception"],
                        "status": "resolved" if m.get("corrected") else "active",
                        "evidence": json.dumps([{"message": m["misconception"], "corrected": m.get("corrected", False)}]),
                    }).execute()

                    logger.info(f"Misconception logged for {student_id}: {m['concept']}")

        except Exception as e:
            logger.error(f"Failed to log misconceptions for {student_id}: {e}")

    async def _log_concepts_to_knowledge_map(self, student_id: str, extracted: Dict[str, Any]) -> None:
        try:
            subject = extracted.get("current_subject", "general")
            class_level = extracted.get("class_level") or "SS1"

            mastered = extracted.get("concepts_mastered", [])
            confused = extracted.get("concepts_confused", [])
            discussed = extracted.get("concepts_discussed", [])

            all_concepts = set()
            all_concepts.update(mastered)
            all_concepts.update(confused)
            all_concepts.update(discussed)

            for concept in all_concepts:
                if not concept:
                    continue

                concept_id = concept.lower().replace(" ", "_").replace("-", "_")

                if concept in mastered:
                    mastery_score = 75.0
                    performance = 0.8
                elif concept in confused:
                    mastery_score = 30.0
                    performance = 0.3
                else:
                    mastery_score = 50.0
                    performance = 0.5

                existing = (
                    self.db.table("knowledge_maps")
                    .select("id, mastery_score, assessment_count")
                    .eq("student_id", student_id)
                    .eq("concept_id", concept_id)
                    .execute()
                )

                from datetime import timedelta
                next_review = datetime.utcnow() + timedelta(days=settings.spaced_rep_default_interval_days)

                if existing.data:
                    record = existing.data[0]
                    old_score = record["mastery_score"]
                    new_score = (old_score * 0.7) + (mastery_score * 0.3)

                    self.db.table("knowledge_maps").update({
                        "mastery_score": round(new_score, 2),
                        "last_assessed_at": datetime.utcnow().isoformat(),
                        "assessment_count": record["assessment_count"] + 1,
                        "last_assessment_performance": performance,
                        "next_review_due_at": next_review.isoformat(),
                    }).eq("id", record["id"]).execute()

                else:
                    self.db.table("knowledge_maps").insert({
                        "student_id": student_id,
                        "concept_id": concept_id,
                        "subject": subject,
                        "class_level": class_level,
                        "mastery_score": mastery_score,
                        "last_assessed_at": datetime.utcnow().isoformat(),
                        "assessment_count": 1,
                        "last_assessment_performance": performance,
                        "next_review_due_at": next_review.isoformat(),
                        "forgetting_curve_params": json.dumps({
                            "ease_factor": 2.5,
                            "interval_days": settings.spaced_rep_default_interval_days,
                            "repetitions": 1,
                        }),
                    }).execute()

            logger.debug(f"Knowledge map updated for {student_id}: {len(all_concepts)} concepts")

        except Exception as e:
            logger.error(f"Failed to log concepts to knowledge map for {student_id}: {e}")
