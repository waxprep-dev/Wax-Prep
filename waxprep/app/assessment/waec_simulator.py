import json
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

WAEC_THEORY_EVALUATION_PROMPT = """You are WaxPrep evaluating a Nigerian student's answer to a WAEC theory question.

Question: {question}

Marking Guide: {marking_guide}

Worked Solution: {worked_solution}

Student's Answer: {student_answer}

Evaluate the student's answer against the marking guide. Be generous with partial credit — award marks for each correct element the student includes, even if imperfectly worded.

Return ONLY a JSON object:
{{
    "marks_awarded": number between 0 and {max_marks},
    "max_marks": {max_marks},
    "percentage": number between 0 and 100,
    "correct_elements": ["list of things the student got right"],
    "missing_elements": ["list of things the student missed"],
    "examiner_feedback": "brief feedback as a WAEC examiner would give",
    "what_to_study": "one specific thing to review based on the gaps"
}}"""

THEORY_RESPONSE_PROMPT = """You are WaxPrep giving feedback to a Nigerian student on their WAEC theory question attempt.
You have the evaluation data. Your job is to deliver this feedback naturally, like a teacher reviewing their student's exam script.

Evaluation: {evaluation}
Question topic: {topic}

Rules:
- Acknowledge what they got right first
- Be specific about what they missed
- Explain WHY the missing elements matter for WAEC marking
- Reference the marking guide naturally
- End by asking if they want to see the full worked solution or try a similar question
- Keep it natural Nigerian teacher voice — warm but honest
- Do not hide disappointing scores behind excessive encouragement

Your feedback:"""

class WAECSimulator:
    def __init__(self):
        self.db = get_db_client()
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self._active_sessions: Dict[str, Dict] = {}
    
    async def start_objective_session(self, student_id, subject, year=None, count=10, student_name="there") -> str:
        try:
            query = self.db.table("waec_questions").select("*").eq("subject", subject).eq("paper_type", "objective")
            if year: query = query.eq("year", year)
            response = query.limit(count + 5).execute()
            if not response.data:
                return f"I don't have WAEC {subject} objective questions yet. Want me to teach you instead?"
            questions = response.data
            random.shuffle(questions)
            questions = questions[:count]
            session_response = self.db.table("waec_simulation_sessions").insert({
                "student_id": student_id, "subject": subject, "paper_type": "objective",
                "question_ids": json.dumps([q["id"] for q in questions]), "total_questions": len(questions),
            }).execute()
            session_id = session_response.data[0]["id"] if session_response.data else "unknown"
            self._active_sessions[student_id] = {
                "session_id": session_id, "session_type": "objective", "subject": subject,
                "questions": questions, "current_index": 0, "answers": {}, "student_name": student_name,
            }
            first_q = questions[0]
            year_label = f"({first_q.get('year', 'Past Paper')})" if first_q.get("year") else ""
            return (
                f"WAEC {subject.capitalize()} Objective — {len(questions)} questions {year_label}\n\n"
                f"Question 1 of {len(questions)} — {first_q.get('topic', '').capitalize()}\n\n"
                f"{first_q['question_text']}\n\n"
                f"A) {first_q['option_a']}\nB) {first_q['option_b']}\nC) {first_q['option_c']}\nD) {first_q['option_d']}"
            )
        except Exception as e:
            logger.error(f"WAEC objective start failed: {e}")
            return "Something went wrong. Try again?"
    
    async def start_theory_session(self, student_id, subject, student_name="there") -> str:
        try:
            response = self.db.table("waec_questions").select("*").eq("subject", subject).eq("paper_type", "theory").limit(5).execute()
            if not response.data:
                return f"WAEC theory questions for {subject} aren't loaded yet. Want objective practice instead?"
            questions = response.data
            random.shuffle(questions)
            question = questions[0]
            self._active_sessions[student_id] = {
                "session_type": "theory", "subject": subject, "current_question": question,
                "awaiting_answer": True, "student_name": student_name,
            }
            marks = question.get("marks_available", 10)
            return (
                f"WAEC {subject.capitalize()} Theory Practice\n\n"
                f"This question carries {marks} marks — take your time.\n\n"
                f"{question['question_text']}\n\n"
                f"Write your full answer and I'll mark it against the official marking guide."
            )
        except Exception as e:
            logger.error(f"WAEC theory start failed: {e}")
            return "Something went wrong. Try again?"
    
    async def process_objective_answer(self, student_id, answer) -> str:
        session = self._active_sessions.get(student_id)
        if not session or session.get("session_type") != "objective": return None
        answer = answer.strip().upper()
        if answer not in ["A", "B", "C", "D"]: return "Just type A, B, C, or D."
        current_q = session["questions"][session["current_index"]]
        is_correct = answer == current_q["correct_option"]
        session["answers"][current_q["id"]] = {"given": answer, "correct": current_q["correct_option"], "is_correct": is_correct, "topic": current_q.get("topic", "")}
        if is_correct: feedback = f"✓ Correct — {answer}."
        else:
            correct_text = current_q.get(f"option_{current_q['correct_option'].lower()}", "")
            worked = current_q.get("worked_solution", "")
            feedback = f"✗ Answer is {current_q['correct_option']}: {correct_text}."
            if worked: feedback += f"\n\nWhy: {worked[:200]}"
        session["current_index"] += 1
        self._active_sessions[student_id] = session
        if session["current_index"] >= len(session["questions"]):
            del self._active_sessions[student_id]
            return await self._generate_objective_results(student_id, session, feedback)
        next_q = session["questions"][session["current_index"]]
        total = len(session["questions"])
        current_num = session["current_index"] + 1
        return (
            f"{feedback}\n\nQuestion {current_num} of {total} — {next_q.get('topic', '').capitalize()}\n\n"
            f"{next_q['question_text']}\n\n"
            f"A) {next_q['option_a']}\nB) {next_q['option_b']}\nC) {next_q['option_c']}\nD) {next_q['option_d']}"
        )
    
    async def process_theory_answer(self, student_id, student_answer) -> str:
        session = self._active_sessions.get(student_id)
        if not session or session.get("session_type") != "theory": return None
        question = session["current_question"]
        try:
            eval_prompt = WAEC_THEORY_EVALUATION_PROMPT.format(
                question=question["question_text"], marking_guide=question.get("marking_guide", ""),
                worked_solution=question.get("worked_solution", ""), student_answer=student_answer,
                max_marks=question.get("marks_available", 10),
            )
            eval_response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model, messages=[{"role": "user", "content": eval_prompt}],
                max_tokens=400, temperature=0.2,
            )
            raw = eval_response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            evaluation = json.loads(raw)
            feedback_prompt = THEORY_RESPONSE_PROMPT.format(evaluation=json.dumps(evaluation), topic=question.get("topic", "this topic"))
            feedback_response = self.groq_client.chat.completions.create(
                model=settings.groq_primary_model, messages=[{"role": "user", "content": feedback_prompt}],
                max_tokens=400, temperature=0.6,
            )
            feedback = feedback_response.choices[0].message.content.strip()
            del self._active_sessions[student_id]
            return f"WAEC Theory Assessment\n\nScore: {evaluation.get('marks_awarded', 0)}/{evaluation.get('max_marks', 10)} ({evaluation.get('percentage', 0):.0f}%)\n\n{feedback}"
        except Exception as e:
            logger.error(f"Theory evaluation failed: {e}")
            del self._active_sessions[student_id]
            return "I had trouble marking that. Here's the worked solution:\n\n" + question.get("worked_solution", "")
    
    async def _generate_objective_results(self, student_id, session, final_feedback) -> str:
        answers = session["answers"]
        total = len(answers)
        correct = sum(1 for a in answers.values() if a["is_correct"])
        percentage = round((correct / total) * 100) if total > 0 else 0
        waec_grades = {75: "A1", 70: "B2", 65: "B3", 60: "C4", 55: "C5", 50: "C6", 45: "D7", 40: "E8"}
        grade = "F9"
        for threshold, g in waec_grades.items():
            if percentage >= threshold: grade = g; break
        weak_topics = list(set(a["topic"] for a in answers.values() if not a["is_correct"] and a.get("topic")))
        strong_topics = list(set(a["topic"] for a in answers.values() if a["is_correct"] and a.get("topic")))
        result = f"{final_feedback}\n\nSession Complete — {session['subject'].capitalize()} Objective\nScore: {correct}/{total} ({percentage}%) — WAEC Grade: {grade}\n\n"
        if weak_topics: result += f"Topics to review: {', '.join(weak_topics[:5])}\n"
        if strong_topics: result += f"Topics handled well: {', '.join(strong_topics[:3])}\n"
        result += "\nLet's work through the topics you missed — which one first?" if percentage < 60 else "\nSolid. Want theory practice or harder questions?"
        return result
    
    def has_active_session(self, student_id): return student_id in self._active_sessions
    def get_session_type(self, student_id):
        session = self._active_sessions.get(student_id)
        return session.get("session_type") if session else None
    def is_simulation_answer(self, message): return message.strip().upper() in ["A", "B", "C", "D"]
    def is_waec_trigger(self, message):
        triggers = ["waec practice", "waec questions", "waec simulation", "waec mock", "past waec", "waec objective", "waec theory", "practice waec", "do waec"]
        return any(t in message.lower() for t in triggers)
