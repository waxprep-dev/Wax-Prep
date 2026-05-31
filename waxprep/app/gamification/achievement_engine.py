import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

ACHIEVEMENT_ANNOUNCEMENT_PROMPT = """Write a brief, warm achievement announcement from WaxPrep to a Nigerian student who just earned an achievement.

Student name: {name}
Achievement: {achievement_title}
Achievement description: {achievement_description}
XP earned: {xp}
Achievement rarity: {rarity}
Context of how they earned it: {context}

Rules:
- Maximum 3 sentences
- Sound genuinely warm and specific — not generic "Congratulations!"
- Reference what they actually did to earn it
- For rare or legendary achievements, be more enthusiastic
- End with something encouraging about their next goal
- Sound like WaxPrep, not a game notification

Announcement:"""

class AchievementEngine:
    
    XP_PER_LEVEL = {1: 100, 2: 200, 3: 350, 4: 550, 5: 800, 6: 1100, 7: 1500, 8: 2000, 9: 2600, 10: 3300}
    LEVEL_NAMES = {1: "Beginner", 2: "Student", 3: "Learner", 4: "Scholar", 5: "Academic", 6: "Expert", 7: "Master", 8: "Champion", 9: "Elite", 10: "Legend"}
    
    def __init__(self):
        self.db = get_db_client()
        self.groq_client = Groq(api_key=settings.groq_api_key)
    
    async def check_and_award_achievements(self, student_id, event_type, event_data) -> List[Dict]:
        newly_earned = []
        try:
            all_achievements = self.db.table("achievements").select("*").execute()
            if not all_achievements.data: return []
            already_earned = self.db.table("student_achievements").select("achievement_id").eq("student_id", student_id).execute()
            earned_ids = {a["achievement_id"] for a in (already_earned.data or [])}
            stats = await self._get_student_stats(student_id)
            for achievement in all_achievements.data:
                if achievement["id"] in earned_ids: continue
                if await self._check_condition(achievement, stats, event_type, event_data):
                    try:
                        self.db.table("student_achievements").insert({"student_id": student_id, "achievement_id": achievement["id"], "context": json.dumps(event_data)}).execute()
                        await self._award_xp(student_id, achievement["xp_reward"])
                        newly_earned.append(achievement)
                        logger.info(f"Achievement: {student_id} — {achievement['code']}")
                    except Exception: pass
            return newly_earned
        except Exception as e:
            logger.error(f"Achievement check failed: {e}")
            return []
    
    async def _check_condition(self, achievement, stats, event_type, event_data) -> bool:
        condition_type = achievement.get("condition_type")
        condition_value = achievement.get("condition_value", {})
        if isinstance(condition_value, str): condition_value = json.loads(condition_value)
        try:
            if condition_type == "session_count": return stats.get("session_count", 0) >= condition_value.get("min", 1)
            elif condition_type == "study_streak": return stats.get("study_streak", 0) >= condition_value.get("min", 1)
            elif condition_type == "correct_answers": return stats.get("total_correct_answers", 0) >= condition_value.get("min", 1)
            elif condition_type == "concepts_mastered": return stats.get("concepts_mastered", 0) >= condition_value.get("min", 1)
            elif condition_type == "misconceptions_corrected": return stats.get("misconceptions_corrected", 0) >= condition_value.get("min", 1)
            elif condition_type == "waec_sessions": return stats.get("waec_sessions", 0) >= condition_value.get("min", 1)
            elif condition_type == "jamb_sessions": return stats.get("jamb_sessions", 0) >= condition_value.get("min", 1)
            elif condition_type == "waec_score": return event_type == "waec_complete" and event_data.get("score", 0) >= condition_value.get("min", 0)
            elif condition_type == "peer_sessions": return stats.get("peer_sessions", 0) >= condition_value.get("min", 1)
            elif condition_type == "concept_mastery":
                concept = condition_value.get("concept", "")
                return stats.get(f"mastery_{concept}", 0) >= condition_value.get("min", 70)
            elif condition_type == "study_time":
                current_hour = datetime.utcnow().hour + 1
                return condition_value.get("hour_min", 0) <= current_hour < condition_value.get("hour_max", 24)
            elif condition_type == "return_after_gap": return event_type == "session_started" and event_data.get("days_since_last", 0) >= condition_value.get("days_min", 5)
            elif condition_type == "voice_notes_sent": return stats.get("voice_notes_sent", 0) >= condition_value.get("min", 1)
            return False
        except Exception: return False
    
    async def _get_student_stats(self, student_id) -> Dict:
        try:
            student = self.db.table("students").select("session_count").eq("id", student_id).execute()
            profile = self.db.table("student_profiles").select("study_streak_current, sent_voice_count").eq("student_id", student_id).execute()
            correct = self.db.table("assessment_questions").select("id", count="exact").eq("student_id", student_id).eq("status", "completed").gte("final_score", 0.7).execute()
            concepts = self.db.table("knowledge_maps").select("concept_id, mastery_score").eq("student_id", student_id).execute()
            misc = self.db.table("misconceptions").select("id", count="exact").eq("student_id", student_id).eq("status", "resolved").execute()
            waec = self.db.table("waec_simulation_sessions").select("id", count="exact").eq("student_id", student_id).execute()
            jamb = self.db.table("jamb_simulation_sessions").select("id", count="exact").eq("student_id", student_id).execute()
            stats = {
                "session_count": student.data[0].get("session_count", 0) if student.data else 0,
                "study_streak": profile.data[0].get("study_streak_current", 0) if profile.data else 0,
                "total_correct_answers": correct.count or 0,
                "concepts_mastered": sum(1 for c in (concepts.data or []) if c["mastery_score"] >= 70),
                "misconceptions_corrected": misc.count or 0,
                "waec_sessions": waec.count or 0, "jamb_sessions": jamb.count or 0,
                "voice_notes_sent": profile.data[0].get("sent_voice_count", 0) if profile.data else 0,
            }
            for c in (concepts.data or []): stats[f"mastery_{c['concept_id']}"] = c["mastery_score"]
            return stats
        except Exception as e:
            logger.error(f"Stats failed: {e}")
            return {}
    
    async def _award_xp(self, student_id, xp) -> Tuple[int, bool]:
        try:
            existing = self.db.table("student_xp").select("*").eq("student_id", student_id).execute()
            if existing.data:
                record = existing.data[0]
                new_total = record["total_xp"] + xp
                old_level = record["current_level"]
                new_level = self._calculate_level(new_total)
                leveled_up = new_level > old_level
                xp_to_next = self._xp_for_level(new_level + 1) - new_total
                self.db.table("student_xp").update({"total_xp": new_total, "current_level": new_level, "xp_to_next_level": max(0, xp_to_next), "last_xp_event": datetime.utcnow().isoformat()}).eq("student_id", student_id).execute()
                return new_level, leveled_up
            else:
                new_level = self._calculate_level(xp)
                self.db.table("student_xp").insert({"student_id": student_id, "total_xp": xp, "current_level": new_level, "xp_to_next_level": max(0, self._xp_for_level(2) - xp)}).execute()
                return new_level, False
        except Exception as e:
            logger.error(f"XP failed: {e}")
            return 1, False
    
    def _calculate_level(self, total_xp): 
        for level in range(10, 0, -1):
            if total_xp >= self._xp_for_level(level): return level
        return 1
    
    def _xp_for_level(self, level): return sum(self.XP_PER_LEVEL.get(i, 500) for i in range(1, level)) if level > 1 else 0
    
    async def generate_achievement_announcement(self, achievement, student_name, context) -> str:
        try:
            prompt = ACHIEVEMENT_ANNOUNCEMENT_PROMPT.format(name=student_name, achievement_title=achievement["title"], achievement_description=achievement["description"], xp=achievement["xp_reward"], rarity=achievement["rarity"], context=str(context)[:100])
            response = self.groq_client.chat.completions.create(model=settings.groq_fast_model, messages=[{"role": "user", "content": prompt}], max_tokens=120, temperature=0.7)
            message = response.choices[0].message.content.strip()
            emoji = achievement.get("icon_emoji", "🏆")
            return f"{emoji} Achievement Unlocked: {achievement['title']}\n\n{message}\n\n+{achievement['xp_reward']} XP"
        except Exception:
            return f"{achievement.get('icon_emoji', '🏆')} Achievement Unlocked: {achievement['title']} (+{achievement['xp_reward']} XP)"
    
    async def get_student_xp_status(self, student_id) -> Dict:
        try:
            xp_record = self.db.table("student_xp").select("*").eq("student_id", student_id).execute()
            if xp_record.data:
                record = xp_record.data[0]
                level = record["current_level"]
                return {"level": level, "level_name": self.LEVEL_NAMES.get(level, "Scholar"), "total_xp": record["total_xp"], "xp_to_next": record["xp_to_next_level"]}
            return {"level": 1, "level_name": "Beginner", "total_xp": 0, "xp_to_next": 100}
        except Exception: return {"level": 1, "level_name": "Beginner", "total_xp": 0, "xp_to_next": 100}
    
    async def get_student_achievements_summary(self, student_id) -> str:
        try:
            earned = self.db.table("student_achievements").select("*, achievements(*)").eq("student_id", student_id).order("earned_at", desc=True).limit(5).execute()
            xp_status = await self.get_student_xp_status(student_id)
            if not earned.data: return f"Level {xp_status['level']} — {xp_status['level_name']}\nTotal XP: {xp_status['total_xp']}\nNo achievements yet. Keep studying."
            achievement_list = [f"{ea['achievements']['icon_emoji']} {ea['achievements']['title']}" for ea in earned.data[:5] if ea.get("achievements")]
            return f"Level {xp_status['level']} — {xp_status['level_name']}\nTotal XP: {xp_status['total_xp']} | {xp_status['xp_to_next']} XP to next level\n\nAchievements ({len(earned.data)} total):\n" + "\n".join(achievement_list)
        except Exception as e:
            logger.error(f"Summary failed: {e}")
            return "Couldn't load achievements."
