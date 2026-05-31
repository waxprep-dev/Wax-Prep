import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client
from waxprep.app.memory.spaced_repetition import SpacedRepetitionEngine

QUESTION_GENERATION_PROMPT = """You are WaxPrep generating a teaching assessment question for a Nigerian student.

Student profile:
Class level: {class_level}
Subject: {subject}
Topic: {topic}
Concept being tested: {concept}
Difficulty target: {difficulty} (1=very easy, 5=very hard)
Question type: {question_type}
Known misconceptions to target: {misconceptions}
Recent conversation context: {context}

Generate a question that:
Feels like a natural part of the conversation — not a formal test
Tests understanding of {concept} at difficulty level {difficulty}
If there are known misconceptions, the question should probe whether those misconceptions are still present
Is phrased the way WaxPrep talks — naturally, not like a textbook
For difficulty 1-2: straightforward recall or recognition
For difficulty 3: requires application of the concept
For difficulty 4-5: requires analysis, comparison, or multi-step reasoning

Return ONLY a valid JSON object, nothing else:
{{
"question": "the question text exactly as WaxPrep would ask it",
"correct_answer": "the complete correct answer",
"answer_key_points": ["key point 1", "key point 2", "key point 3"],
"common_wrong_answers": ["typical wrong answer 1", "typical wrong answer 2"],
"hint_level_1": "a gentle hint that does not give away the answer",
"hint_level_2": "a more direct hint still requiring the student to finish",
"difficulty_actual": {difficulty},
"question_type": "{question_type}"
}}"""

ANSWER_EVALUATION_PROMPT = """You are evaluating a Nigerian student's answer to a teaching question.

Question: {question}
Correct answer: {correct_answer}
Key answer points: {key_points}
Student's answer: {student_answer}
Attempts so far: {attempts}

Evaluate the student's answer and return ONLY a valid JSON object:
{{
"is_correct": true or false,
"is_partially_correct": true or false,
"score": 0.0 to 1.0,
"correct_elements": ["what the student got right"],
"missing_elements": ["what the student missed or got wrong"],
"misconception_detected": "string describing any specific misconception shown, or null",
"feedback_type": "correct" | "partially_correct" | "wrong_hint1" | "wrong_hint2" | "wrong_explain"
}}

feedback_type rules:
"correct" if score >= 0.8
"partially_correct" if 0.4 <= score < 0.8
"wrong_hint1" if score < 0.4 and attempts == 1
"wrong_hint2" if score < 0.4 and attempts == 2
"wrong_explain" if score < 0.4 and attempts >= 3"""

class AssessmentEngine:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()
        self.spaced_rep = SpacedRepetitionEngine()
        self._active_assessments: Dict[str, Dict] = {}

    async def generate_question(
        self,
        student_id: str,
        subject: str,
        concept: str,
        class_level: str,
        difficulty: int = 2,
        question_type: str = "short_answer",
        misconceptions: List[str] = None,
        recent_context: str = "",
    ) -> Optional[Dict[str, Any]]:
        try:
            prompt = QUESTION_GENERATION_PROMPT.format(
                class_level=class_level,
                subject=subject,
                topic=concept,
                concept=concept,
                difficulty=difficulty,
                question_type=question_type,
                misconceptions=json.dumps(misconceptions or []),
                context=recent_context[:200],
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.6,
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            question_data = json.loads(raw)

            question_data["student_id"] = student_id
            question_data["subject"] = subject
            question_data["concept"] = concept
            question_data["class_level"] = class_level
            question_data["created_at"] = datetime.utcnow().isoformat()
            question_data["attempts"] = 0

            self._active_assessments[student_id] = question_data

            await self._save_question_to_db(student_id, question_data)

            return question_data

        except json.JSONDecodeError as e:
            logger.warning(f"Question generation JSON parse failed: {e}")
            return self._generate_fallback_question(concept, subject, difficulty)
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return self._generate_fallback_question(concept, subject, difficulty)

    async def evaluate_answer(
        self,
        student_id: str,
        student_answer: str,
    ) -> Optional[Dict[str, Any]]:
        active = self._active_assessments.get(student_id)
        if not active:
            active = await self._load_active_question(student_id)

        if not active:
            return None

        attempts = active.get("attempts", 0) + 1
        active["attempts"] = attempts

        try:
            prompt = ANSWER_EVALUATION_PROMPT.format(
                question=active["question"],
                correct_answer=active["correct_answer"],
                key_points=json.dumps(active.get("answer_key_points", [])),
                student_answer=student_answer,
                attempts=attempts,
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            evaluation = json.loads(raw)

            evaluation["question"] = active["question"]
            evaluation["correct_answer"] = active["correct_answer"]
            evaluation["hint_level_1"] = active.get("hint_level_1", "")
            evaluation["hint_level_2"] = active.get("hint_level_2", "")
            evaluation["attempts"] = attempts
            evaluation["concept"] = active.get("concept", "")
            evaluation["subject"] = active.get("subject", "")

            if evaluation.get("is_correct"):
                del self._active_assessments[student_id]
                await self._record_assessment_complete(student_id, active, evaluation)
                await self.spaced_rep.update_after_review(
                    student_id=student_id,
                    concept_id=active.get("concept", "").lower().replace(" ", "_"),
                    performance_score=evaluation.get("score", 0.8),
                )

            if evaluation.get("misconception_detected"):
                await self._log_assessment_misconception(
                    student_id=student_id,
                    concept=active.get("concept", ""),
                    subject=active.get("subject", ""),
                    misconception=evaluation["misconception_detected"],
                )

            return evaluation

        except Exception as e:
            logger.error(f"Answer evaluation failed: {e}")
            return {
                "is_correct": False,
                "is_partially_correct": False,
                "score": 0.0,
                "feedback_type": "wrong_hint1",
                "question": active.get("question", ""),
                "hint_level_1": active.get("hint_level_1", "Think about the core function of this concept."),
                "hint_level_2": active.get("hint_level_2", ""),
                "attempts": attempts,
                "concept": active.get("concept", ""),
                "subject": active.get("subject", ""),
            }

    def has_active_assessment(self, student_id: str) -> bool:
        return student_id in self._active_assessments

    async def clear_active_assessment(self, student_id: str) -> None:
        if student_id in self._active_assessments:
            del self._active_assessments[student_id]

    def get_active_assessment_context(self, student_id: str) -> Optional[Dict[str, Any]]:
        active = self._active_assessments.get(student_id)
        if not active:
            return None
        return {
            "current_question": active.get("question"),
            "correct_answer": active.get("correct_answer"),
            "difficulty_level": active.get("difficulty_actual", 2),
            "attempts": active.get("attempts", 0),
        }

    async def _save_question_to_db(self, student_id: str, question_data: Dict) -> None:
        try:
            self.db.table("assessment_questions").insert({
                "student_id": student_id,
                "subject": question_data.get("subject"),
                "concept_id": question_data.get("concept", "").lower().replace(" ", "_"),
                "question_text": question_data.get("question"),
                "correct_answer": question_data.get("correct_answer"),
                "difficulty": question_data.get("difficulty_actual", 2),
                "question_type": question_data.get("question_type", "short_answer"),
                "status": "active",
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save question to DB: {e}")

    async def _load_active_question(self, student_id: str) -> Optional[Dict]:
        try:
            response = (
                self.db.table("assessment_questions")
                .select("*")
                .eq("student_id", student_id)
                .eq("status", "active")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data:
                q = response.data[0]
                return {
                    "question": q["question_text"],
                    "correct_answer": q["correct_answer"],
                    "answer_key_points": [],
                    "hint_level_1": "Think carefully about the core idea.",
                    "hint_level_2": "Focus on the specific definition.",
                    "attempts": q.get("attempts", 0),
                    "concept": q.get("concept_id", "").replace("_", " "),
                    "subject": q.get("subject", ""),
                    "difficulty_actual": q.get("difficulty", 2),
                }
            return None
        except Exception as e:
            logger.warning(f"Failed to load active question: {e}")
            return None

    async def _record_assessment_complete(
        self,
        student_id: str,
        question_data: Dict,
        evaluation: Dict,
    ) -> None:
        try:
            self.db.table("assessment_questions").update({
                "status": "completed",
                "final_score": evaluation.get("score", 0),
                "attempts_taken": evaluation.get("attempts", 1),
                "completed_at": datetime.utcnow().isoformat(),
            }).eq("student_id", student_id).eq("status", "active").execute()

            self.db.table("learning_events").insert({
                "student_id": student_id,
                "event_type": "assessment_completed",
                "concept_id": question_data.get("concept", "").lower().replace(" ", "_"),
                "subject": question_data.get("subject"),
                "class_level": question_data.get("class_level"),
                "details": json.dumps({
                    "score": evaluation.get("score"),
                    "attempts": evaluation.get("attempts"),
                    "question_type": question_data.get("question_type"),
                }),
                "timestamp": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to record assessment complete: {e}")

    async def _log_assessment_misconception(
        self,
        student_id: str,
        concept: str,
        subject: str,
        misconception: str,
    ) -> None:
        try:
            code = concept.lower().replace(" ", "_") + "_assessment_misconception"
            existing = (
                self.db.table("misconceptions")
                .select("id, correction_attempts")
                .eq("student_id", student_id)
                .eq("misconception_code", code)
                .execute()
            )
            if not existing.data:
                self.db.table("misconceptions").insert({
                    "student_id": student_id,
                    "subject": subject,
                    "concept_id": concept.lower().replace(" ", "_"),
                    "misconception_code": code,
                    "description": misconception,
                    "status": "active",
                    "evidence": json.dumps([{"source": "assessment", "description": misconception}]),
                }).execute()
        except Exception as e:
            logger.warning(f"Failed to log assessment misconception: {e}")

    def _generate_fallback_question(self, concept: str, subject: str, difficulty: int) -> Dict:
        return {
            "question": f"In your own words, explain what you understand about {concept}.",
            "correct_answer": f"Student should demonstrate basic understanding of {concept}.",
            "answer_key_points": [f"Shows understanding of {concept}"],
            "common_wrong_answers": [],
            "hint_level_1": f"Think about what {concept} actually does or means.",
            "hint_level_2": f"Consider the context in which {concept} appears in {subject}.",
            "difficulty_actual": difficulty,
            "question_type": "short_answer",
            "attempts": 0,
            "concept": concept,
            "subject": subject,
        }
