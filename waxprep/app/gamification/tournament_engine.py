import json
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client

class TournamentEngine:
    def __init__(self):
        self.db = get_db_client()
    
    async def get_active_tournaments(self) -> List[Dict]:
        try:
            response = (
                self.db.table("tournaments")
                .select("*")
                .eq("is_active", True)
                .gte("ends_at", datetime.utcnow().isoformat())
                .order("starts_at", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get active tournaments: {e}")
            return []
    
    async def create_weekly_tournaments(self) -> int:
        subjects_and_levels = [
            ("mathematics", "SS1", "WAEC/JAMB Mathematics Championship"),
            ("biology", "SS1", "Biology Master Tournament"),
            ("physics", "SS1", "Physics Challenge Cup"),
            ("chemistry", "SS1", "Chemistry League"),
            ("english_language", "SS1", "English Excellence Tournament"),
            ("economics", "SS2", "Economics Expert Challenge"),
            ("government", "SS2", "Government Quiz Championship"),
            ("mathematics", "JSS3", "Junior Mathematics Cup"),
        ]
        now = datetime.utcnow()
        week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        created = 0
        for subject, level, title in subjects_and_levels:
            existing = self.db.table("tournaments").select("id").eq("subject", subject).eq("class_level", level).gte("starts_at", week_start.isoformat()).execute()
            if not existing.data:
                self.db.table("tournaments").insert({
                    "title": f"Week {now.isocalendar()[1]} — {title}",
                    "subject": subject, "class_level": level,
                    "starts_at": week_start.isoformat(), "ends_at": week_end.isoformat(),
                    "question_count": 20, "prize_description": "Top 3 earn Tournament Champion badge and bonus XP",
                    "is_active": True,
                }).execute()
                created += 1
        return created
    
    async def enter_tournament(self, student_id, tournament_id) -> Tuple[bool, str, List[Dict]]:
        try:
            tournament = self.db.table("tournaments").select("*").eq("id", tournament_id).execute()
            if not tournament.data: return False, "Tournament not found", []
            t = tournament.data[0]
            if t["ends_at"] < datetime.utcnow().isoformat(): return False, "This tournament has ended", []
            existing_entry = self.db.table("tournament_entries").select("id, completed").eq("tournament_id", tournament_id).eq("student_id", student_id).execute()
            if existing_entry.data and existing_entry.data[0].get("completed"): return False, "You have already completed this tournament", []
            questions = await self._get_tournament_questions(subject=t["subject"], class_level=t["class_level"], count=t["question_count"])
            if not questions: return False, "Tournament questions not available yet", []
            if not existing_entry.data:
                self.db.table("tournament_entries").insert({"tournament_id": tournament_id, "student_id": student_id, "total_questions": len(questions)}).execute()
            return True, f"Tournament started — {len(questions)} questions", questions
        except Exception as e:
            logger.error(f"Tournament entry failed: {e}")
            return False, "Something went wrong", []
    
    async def _get_tournament_questions(self, subject, class_level, count) -> List[Dict]:
        try:
            jamb_q = self.db.table("jamb_questions").select("id, question_text, option_a, option_b, option_c, option_d, correct_option, topic").eq("subject", subject).limit(count + 5).execute()
            waec_q = self.db.table("waec_questions").select("id, question_text, option_a, option_b, option_c, option_d, correct_option, topic").eq("subject", subject).eq("paper_type", "objective").limit(count + 5).execute()
            all_questions = list(jamb_q.data or []) + list(waec_q.data or [])
            random.shuffle(all_questions)
            return all_questions[:count]
        except Exception as e:
            logger.error(f"Failed to get tournament questions: {e}")
            return []
    
    async def submit_tournament_result(self, student_id, tournament_id, answers, time_taken) -> Dict:
        try:
            correct = 0; total = len(answers)
            for q_id, answer in answers.items():
                q_check = self.db.table("jamb_questions").select("correct_option").eq("id", q_id).execute()
                if not q_check.data: q_check = self.db.table("waec_questions").select("correct_option").eq("id", q_id).execute()
                if q_check.data and q_check.data[0]["correct_option"] == answer.upper(): correct += 1
            score = (correct / total * 100) if total > 0 else 0
            speed_bonus = max(0, (1800 - time_taken) / 1800 * 10)
            final_score = score + speed_bonus
            self.db.table("tournament_entries").update({"score": round(final_score, 2), "correct_count": correct, "total_questions": total, "time_taken_seconds": time_taken, "completed": True, "completed_at": datetime.utcnow().isoformat()}).eq("tournament_id", tournament_id).eq("student_id", student_id).execute()
            rank = await self._calculate_rank(tournament_id, student_id, final_score)
            xp_earned = int(score * 2) + (50 if rank <= 3 else 20 if rank <= 10 else 5)
            return {"score": round(score, 1), "correct": correct, "total": total, "time_taken": time_taken, "rank": rank, "xp_earned": xp_earned, "speed_bonus": round(speed_bonus, 1)}
        except Exception as e:
            logger.error(f"Tournament result submission failed: {e}")
            return {"score": 0, "correct": 0, "rank": 0, "xp_earned": 0}
    
    async def _calculate_rank(self, tournament_id, student_id, score) -> int:
        try:
            higher_scores = self.db.table("tournament_entries").select("id", count="exact").eq("tournament_id", tournament_id).eq("completed", True).gt("score", score).execute()
            return (higher_scores.count or 0) + 1
        except Exception: return 1
    
    async def get_leaderboard(self, tournament_id, limit=20) -> List[Dict]:
        try:
            response = self.db.table("tournament_entries").select("*, students(wax_code), student_profiles(student_name)").eq("tournament_id", tournament_id).eq("completed", True).order("score", desc=True).limit(limit).execute()
            result = []
            for i, entry in enumerate(response.data or []):
                result.append({"rank": i + 1, "name": entry.get("student_profiles", {}).get("student_name") or entry.get("students", {}).get("wax_code", "Anonymous"), "score": entry.get("score", 0), "correct": entry.get("correct_count", 0), "total": entry.get("total_questions", 0)})
            return result
        except Exception as e:
            logger.error(f"Leaderboard fetch failed: {e}")
            return []
    
    def is_tournament_trigger(self, message: str) -> bool:
        triggers = ["tournament", "competition", "compete", "leaderboard", "challenge someone", "quiz competition", "weekly challenge"]
        return any(t in message.lower() for t in triggers)
    
    async def generate_tournament_announcement(self, student_name: str) -> str:
        tournaments = await self.get_active_tournaments()
        if not tournaments: return "No active tournaments right now. I'll let you know when the next one starts."
        t = tournaments[0]
        return f"There's an active tournament right now: {t['title']}\n\nSubject: {t['subject'].capitalize()}\nLevel: {t['class_level']}\nEnds: {t['ends_at'][:10]}\n\nPrize: {t.get('prize_description', 'Top 3 earn special achievements')}\n\nType 'enter tournament' to join and compete on the leaderboard!"
