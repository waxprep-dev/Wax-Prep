import json
from typing import Dict, Any, Optional, List
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

WORKED_PROBLEM_PROMPT = """You are WaxPrep working through a mathematics problem with a Nigerian student step by step.

Problem: {problem}
Subject: {subject}
Topic: {topic}
Student class level: {class_level}
Current step number: {step_number}
Steps completed so far: {completed_steps}
Student's response to last step: {student_response}

Your job is to guide the student through this problem one step at a time using scaffolded problem solving.

Rules:
Break the problem into the minimum number of logical steps
For each step, ask the student to do ONE specific thing — a calculation, a decision, or a statement of what they observe
Do not do the step for the student — ask them to do it
If the student's response to the previous step was correct, confirm briefly and move to the next step
If wrong, redirect using: "Not quite — think about it this way..." then ask them to try again
When all steps are done and correct, confirm the full solution and explain why the method worked
Sound like a teacher working alongside a student, not a textbook

Return ONLY a JSON object:
{{
"step_instruction": "what you ask the student to do in this step",
"step_number": {step_number},
"is_final_step": true or false,
"previous_step_correct": true or false,
"previous_step_feedback": "brief feedback on their previous response or empty string if first step",
"expected_step_answer": "what the correct answer to this step is",
"step_hint": "hint if they get stuck"
}}"""

PROBLEM_SETUP_PROMPT = """You are WaxPrep setting up a worked mathematics problem for a Nigerian student.

Topic: {topic}
Class level: {class_level}
Difficulty: {difficulty} out of 5
Student's known misconceptions: {misconceptions}
Recent conversation context: {context}

Generate a problem that:
Is appropriate for the class level and difficulty
Can be broken into 3-6 clear steps
Uses Nigerian context where possible (not foreign names or currencies)
Is the type that appears in WAEC or JAMB for this topic

Return ONLY a JSON object:
{{
"problem_statement": "the full problem as WaxPrep would present it",
"total_steps": number between 3 and 6,
"solution_method": "brief description of the method to use",
"final_answer": "the complete final answer",
"topic": "{topic}",
"difficulty": {difficulty}
}}"""

class WorkedProblemEngine:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()
        self._active_problems: Dict[str, Dict] = {}

    async def start_worked_problem(
        self,
        student_id: str,
        topic: str,
        class_level: str,
        difficulty: int = 2,
        misconceptions: List[str] = None,
        recent_context: str = "",
    ) -> Optional[str]:
        try:
            prompt = PROBLEM_SETUP_PROMPT.format(
                topic=topic,
                class_level=class_level,
                difficulty=difficulty,
                misconceptions=json.dumps(misconceptions or []),
                context=recent_context[:150],
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.5,
            )

            raw = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            problem_data = json.loads(raw)

            self._active_problems[student_id] = {
                **problem_data,
                "current_step": 1,
                "completed_steps": [],
                "student_id": student_id,
            }

            return problem_data["problem_statement"]

        except Exception as e:
            logger.error(f"Failed to start worked problem: {e}")
            return None

    async def process_step_response(
        self,
        student_id: str,
        student_response: str,
    ) -> Optional[str]:
        active = self._active_problems.get(student_id)
        if not active:
            return None

        try:
            prompt = WORKED_PROBLEM_PROMPT.format(
                problem=active["problem_statement"],
                subject="mathematics",
                topic=active.get("topic", ""),
                class_level=active.get("class_level", "SS1"),
                step_number=active["current_step"],
                completed_steps=json.dumps(active["completed_steps"]),
                student_response=student_response,
            )

            response = self.groq_client.chat.completions.create(
                model=settings.groq_primary_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.4,
            )

            raw = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            step_data = json.loads(raw)

            active["completed_steps"].append({
                "step": active["current_step"],
                "instruction": step_data.get("step_instruction"),
                "student_response": student_response,
                "correct": step_data.get("previous_step_correct", False),
            })

            if step_data.get("previous_step_correct"):
                active["current_step"] += 1

            if step_data.get("is_final_step") and step_data.get("previous_step_correct"):
                del self._active_problems[student_id]
                await self._log_problem_complete(student_id, active)

            response_text = ""
            if step_data.get("previous_step_feedback"):
                response_text += step_data["previous_step_feedback"] + " "
            response_text += step_data.get("step_instruction", "")

            return response_text

        except Exception as e:
            logger.error(f"Failed to process step response: {e}")
            return "Let me rephrase that step. " + active.get("problem_statement", "")

    def has_active_problem(self, student_id: str) -> bool:
        return student_id in self._active_problems

    async def abandon_problem(self, student_id: str) -> None:
        if student_id in self._active_problems:
            del self._active_problems[student_id]

    async def _log_problem_complete(self, student_id: str, problem_data: Dict) -> None:
        try:
            from datetime import datetime
            correct_steps = sum(1 for s in problem_data.get("completed_steps", []) if s.get("correct"))
            total_steps = len(problem_data.get("completed_steps", []))
            score = correct_steps / total_steps if total_steps > 0 else 0

            self.db.table("learning_events").insert({
                "student_id": student_id,
                "event_type": "worked_problem_completed",
                "subject": "mathematics",
                "details": json.dumps({
                    "topic": problem_data.get("topic"),
                    "difficulty": problem_data.get("difficulty"),
                    "steps_correct": correct_steps,
                    "total_steps": total_steps,
                    "score": score,
                }),
                "timestamp": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log worked problem: {e}")
