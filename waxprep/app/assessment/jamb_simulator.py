import json
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client
from waxprep.app.cache.redis_client import cache_get, cache_set, conversation_key

SIMULATION_INTRO_TEMPLATE = """Hey {name} — I set up a JAMB practice session for you.

{question_count} questions across {subjects}. No timer pressure right now — take your time.

Here's question 1 of {question_count}:

{subject_label} | Topic: {topic}

{question_text}

A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

Type A, B, C, or D."""

NEXT_QUESTION_TEMPLATE = """{feedback}

Question {current} of {total}:

{subject_label} | Topic: {topic}

{question_text}

A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

Type A, B, C, or D."""

RESULT_TEMPLATE = """That's the end of the practice session, {name}.

Your score: {correct}/{total} ({percentage}%)

By subject:
{subject_breakdown}

Topics where you struggled:
{weak_topics}

Topics you handled well:
{strong_topics}

{jamb_projection}

What do you want to work on first?"""

class JAMBSimulator:
    def __init__(self):
        self.db = get_db_client()
        self._active_sessions: Dict[str, Dict] = {}

    async def start_simulation(
        self,
        student_id: str,
        subjects: List[str],
        questions_per_subject: int = 5,
        student_name: str = "there",
    ) -> str:
        try:
            all_question_ids = []
            question_map = {}

            knowledge_map_response = (
                self.db.table("knowledge_maps")
                .select("concept_id, mastery_score, subject")
                .eq("student_id", student_id)
                .lt("mastery_score", 60)
                .execute()
            )

            weak_concepts = {}
            if knowledge_map_response.data:
                for item in knowledge_map_response.data:
                    subj = item["subject"]
                    if subj not in weak_concepts:
                        weak_concepts[subj] = []
                    weak_concepts[subj].append(item["concept_id"].replace("_", " "))

            for subject in subjects:
                weak_for_subject = weak_concepts.get(subject, [])

                if weak_for_subject:
                    weak_questions_response = (
                        self.db.table("jamb_questions")
                        .select("*")
                        .eq("subject", subject)
                        .in_("topic", weak_for_subject[:5])
                        .limit(questions_per_subject)
                        .execute()
                    )
                    subject_questions = weak_questions_response.data or []
                else:
                    subject_questions = []

                if len(subject_questions) < questions_per_subject:
                    remaining = questions_per_subject - len(subject_questions)
                    existing_ids = [q["id"] for q in subject_questions]

                    random_response = (
                        self.db.table("jamb_questions")
                        .select("*")
                        .eq("subject", subject)
                        .order("year", desc=True)
                        .limit(remaining + len(existing_ids) + 5)
                        .execute()
                    )

                    random_questions = [q for q in (random_response.data or []) if q["id"] not in existing_ids]
                    subject_questions.extend(random_questions[:remaining])

                random.shuffle(subject_questions)
                for q in subject_questions[:questions_per_subject]:
                    all_question_ids.append(q["id"])
                    question_map[q["id"]] = q

            if not all_question_ids:
                return f"I don't have enough practice questions loaded for {', '.join(subjects)} yet. Let's do a teaching session instead — what topic do you want to work on?"

            sim_response = self.db.table("jamb_simulation_sessions").insert({
                "student_id": student_id,
                "subjects": json.dumps(subjects),
                "question_ids": json.dumps(all_question_ids),
                "total_questions": len(all_question_ids),
            }).execute()

            if not sim_response.data:
                return "Something went wrong setting up the simulation. Try again."

            session_id = sim_response.data[0]["id"]
            first_question = question_map[all_question_ids[0]]

            self._active_sessions[student_id] = {
                "session_id": session_id,
                "question_ids": all_question_ids,
                "question_map": question_map,
                "current_index": 0,
                "answers": {},
                "student_name": student_name,
                "subjects": subjects,
            }

            return SIMULATION_INTRO_TEMPLATE.format(
                name=student_name,
                question_count=len(all_question_ids),
                subjects=", ".join([s.capitalize() for s in subjects]),
                subject_label=first_question["subject"].capitalize(),
                topic=first_question.get("topic", "General"),
                question_text=first_question["question_text"],
                option_a=first_question["option_a"],
                option_b=first_question["option_b"],
                option_c=first_question["option_c"],
                option_d=first_question["option_d"],
            )

        except Exception as e:
            logger.error(f"Failed to start JAMB simulation: {e}")
            return "I ran into a problem setting up the practice session. Try asking me to teach you a specific topic instead."

    async def process_answer(
        self,
        student_id: str,
        answer: str,
    ) -> str:
        session = self._active_sessions.get(student_id)
        if not session:
            return None

        answer = answer.strip().upper()
        if answer not in ["A", "B", "C", "D"]:
            return "Just type A, B, C, or D for your answer."

        current_index = session["current_index"]
        current_q_id = session["question_ids"][current_index]
        current_q = session["question_map"][current_q_id]

        is_correct = answer == current_q["correct_option"]
        session["answers"][current_q_id] = {
            "given": answer,
            "correct": current_q["correct_option"],
            "is_correct": is_correct,
            "topic": current_q.get("topic", ""),
            "subject": current_q.get("subject", ""),
        }

        try:
            self.db.table("jamb_question_attempts").insert({
                "student_id": student_id,
                "question_id": current_q_id,
                "simulation_id": session["session_id"],
                "student_answer": answer,
                "is_correct": is_correct,
            }).execute()
        except Exception:
            pass

        if is_correct:
            feedback = f"✓ Correct — {answer} is right."
        else:
            correct_text = current_q[f"option_{current_q['correct_option'].lower()}"]
            feedback = f"✗ Not quite. The answer is {current_q['correct_option']}: {correct_text}.\n{current_q.get('explanation', '')}"

        session["current_index"] += 1
        self._active_sessions[student_id] = session

        if session["current_index"] >= len(session["question_ids"]):
            del self._active_sessions[student_id]
            return await self._generate_results(student_id, session, feedback)

        next_q = session["question_map"][session["question_ids"][session["current_index"]]]
        total = len(session["question_ids"])
        current_num = session["current_index"] + 1

        return NEXT_QUESTION_TEMPLATE.format(
            feedback=feedback,
            current=current_num,
            total=total,
            subject_label=next_q["subject"].capitalize(),
            topic=next_q.get("topic", "General"),
            question_text=next_q["question_text"],
            option_a=next_q["option_a"],
            option_b=next_q["option_b"],
            option_c=next_q["option_c"],
            option_d=next_q["option_d"],
        )

    async def _generate_results(
        self,
        student_id: str,
        session: Dict,
        final_feedback: str,
    ) -> str:
        answers = session["answers"]
        total = len(answers)
        correct = sum(1 for a in answers.values() if a["is_correct"])
        percentage = round((correct / total) * 100) if total > 0 else 0

        subject_stats: Dict[str, Dict] = {}
        weak_topics = []
        strong_topics = []

        for q_id, a in answers.items():
            subj = a["subject"]
            topic = a["topic"]
            if subj not in subject_stats:
                subject_stats[subj] = {"correct": 0, "total": 0}
            subject_stats[subj]["total"] += 1
            if a["is_correct"]:
                subject_stats[subj]["correct"] += 1
                if topic and topic not in strong_topics:
                    strong_topics.append(topic)
            else:
                if topic and topic not in weak_topics:
                    weak_topics.append(topic)

        subject_breakdown_lines = []
        for subj, stats in subject_stats.items():
            subj_pct = round((stats["correct"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            subject_breakdown_lines.append(f"  {subj.capitalize()}: {stats['correct']}/{stats['total']} ({subj_pct}%)")

        jamb_score = 189
        projected_gain = round((correct / total) * 15) if total > 0 else 0
        projected_score = jamb_score + projected_gain

        if percentage >= 80:
            jamb_projection = f"At this rate, you could be adding {projected_gain}+ points to your JAMB score. Keep going."
        elif percentage >= 60:
            jamb_projection = f"Good foundation. Fix the weak spots above and those {projected_gain} points become 10+."
        else:
            jamb_projection = f"These topics need serious work before exam day. Let's tackle them one by one."

        try:
            self.db.table("jamb_simulation_sessions").update({
                "ended_at": datetime.utcnow().isoformat(),
                "score": percentage,
                "correct_count": correct,
                "is_complete": True,
            }).eq("id", session["session_id"]).execute()
        except Exception:
            pass

        return final_feedback + "\n\n" + RESULT_TEMPLATE.format(
            name=session.get("student_name", ""),
            correct=correct,
            total=total,
            percentage=percentage,
            subject_breakdown="\n".join(subject_breakdown_lines),
            weak_topics=", ".join(weak_topics[:5]) if weak_topics else "None — great work!",
            strong_topics=", ".join(strong_topics[:5]) if strong_topics else "Keep building",
            jamb_projection=jamb_projection,
        )

    def has_active_simulation(self, student_id: str) -> bool:
        return student_id in self._active_sessions

    async def abandon_simulation(self, student_id: str) -> None:
        if student_id in self._active_sessions:
            del self._active_sessions[student_id]

    def is_simulation_answer(self, message: str) -> bool:
        return message.strip().upper() in ["A", "B", "C", "D"]
