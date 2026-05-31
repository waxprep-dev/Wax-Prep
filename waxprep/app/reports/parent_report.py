import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

PARENT_REPORT_PROMPT = """You are WaxPrep generating a parent/guardian progress report for a Nigerian student.

This report will be sent to the student's parent or guardian via WhatsApp. It should be warm, honest, clear, and reassuring where progress is being made — and honest about areas needing more attention.

Student information:
- Student name: {name}
- Class level: {class_level}
- Exam target: {exam}
- Report period: {period}

Academic progress data:
- Sessions completed: {sessions}
- Total study time estimate: {study_time}
- Concepts covered: {concepts_covered}
- Concepts with good mastery (70%+): {concepts_mastered}
- Active misconceptions being worked on: {active_misconceptions}
- Study streak (consecutive days): {streak}
- Last active: {last_active}

Best performing areas: {strengths}
Areas needing more work: {weaknesses}

Recent achievements: {achievements}

Rules:
- Write in natural, warm Nigerian English
- Be honest about weaknesses without being alarming
- Reference specific subjects and topics the student has worked on
- Include concrete recommendations for the parent/guardian
- Maximum 400 words
- End with a clear call to action for the parent

Parent report:"""

class ParentReportGenerator:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()
    
    async def generate_report(self, student_id, period_days=30) -> Optional[str]:
        try:
            student = self.db.table("students").select("*").eq("id", student_id).execute()
            profile = self.db.table("student_profiles").select("*").eq("student_id", student_id).execute()
            if not student.data: return None
            
            s = student.data[0]
            p = profile.data[0] if profile.data else {}
            name = p.get("student_name", "Your child")
            class_level = s.get("inferred_class_level", "Secondary School")
            exam = s.get("primary_exam_target", "upcoming exam")
            
            period_start = datetime.utcnow() - timedelta(days=period_days)
            sessions_in_period = self.db.table("conversations").select("id", count="exact").eq("student_id", student_id).gte("started_at", period_start.isoformat()).execute()
            knowledge = self.db.table("knowledge_maps").select("concept_id, subject, mastery_score").eq("student_id", student_id).execute()
            misconceptions = self.db.table("misconceptions").select("description, subject").eq("student_id", student_id).eq("status", "active").execute()
            achievements = self.db.table("student_achievements").select("*, achievements(title, icon_emoji)").eq("student_id", student_id).gte("earned_at", period_start.isoformat()).execute()
            
            mastered = [k for k in (knowledge.data or []) if k["mastery_score"] >= 70]
            weak = [k for k in (knowledge.data or []) if k["mastery_score"] < 40]
            
            subject_mastery = {}
            for k in (knowledge.data or []):
                subj = k["subject"]
                if subj not in subject_mastery: subject_mastery[subj] = []
                subject_mastery[subj].append(k["mastery_score"])
            
            strong_subjects = [subj for subj, scores in subject_mastery.items() if sum(scores)/len(scores) >= 60]
            weak_subjects = [subj for subj, scores in subject_mastery.items() if sum(scores)/len(scores) < 40]
            
            achievement_list = []
            for ea in (achievements.data or []):
                if ea.get("achievements"):
                    a = ea["achievements"]
                    achievement_list.append(f"{a.get('icon_emoji', '')} {a.get('title', '')}")
            
            last_active = s.get("last_active_at", "")
            if last_active:
                try:
                    last_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
                    days_ago = (datetime.utcnow().replace(tzinfo=last_dt.tzinfo) - last_dt).days
                    last_active_str = f"{days_ago} days ago" if days_ago > 0 else "today"
                except Exception: last_active_str = "recently"
            else: last_active_str = "unknown"
            
            prompt = PARENT_REPORT_PROMPT.format(
                name=name, class_level=class_level, exam=exam, period=f"last {period_days} days",
                sessions=sessions_in_period.count or 0,
                study_time=f"approximately {(sessions_in_period.count or 0) * 45} minutes",
                concepts_covered=len(knowledge.data or []), concepts_mastered=len(mastered),
                active_misconceptions=len(misconceptions.data or []),
                streak=p.get("study_streak_current", 0), last_active=last_active_str,
                strengths=", ".join(strong_subjects[:3]) or "Still building",
                weaknesses=", ".join(weak_subjects[:3]) or "None identified yet",
                achievements=", ".join(achievement_list[:3]) or "None this period yet",
            )
            
            response = self.groq_client.chat.completions.create(
                model=settings.groq_primary_model, messages=[{"role": "user", "content": prompt}],
                max_tokens=500, temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Parent report failed: {e}")
            return None
    
    async def schedule_monthly_reports(self) -> int:
        try:
            active_students = self.db.table("students").select("id, platform_whatsapp, platform_telegram").eq("status", "active").execute()
            scheduled = 0
            for student in (active_students.data or []):
                has_pending = self.db.table("scheduled_notifications").select("id").eq("student_id", student["id"]).eq("notification_type", "parent_report").eq("status", "pending").execute()
                if not has_pending.data:
                    platform = "whatsapp" if student.get("platform_whatsapp") else "telegram"
                    self.db.table("scheduled_notifications").insert({
                        "student_id": student["id"], "notification_type": "parent_report",
                        "scheduled_for": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                        "platform": platform, "content": "GENERATE_PARENT_REPORT", "status": "pending",
                    }).execute()
                    scheduled += 1
            return scheduled
        except Exception as e:
            logger.error(f"Parent report scheduling failed: {e}")
            return 0
