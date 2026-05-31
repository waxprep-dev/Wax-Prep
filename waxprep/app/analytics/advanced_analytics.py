import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client

class AdvancedAnalyticsEngine:
    def __init__(self):
        self.db = get_db_client()
    
    async def get_platform_health(self) -> Dict:
        try:
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            active_last_7 = self.db.table("students").select("id", count="exact").eq("status", "active").gte("last_active_at", seven_days_ago).execute()
            messages_last_7 = self.db.table("messages").select("id", count="exact").gte("timestamp", seven_days_ago).execute()
            sessions_last_7 = self.db.table("conversations").select("id", count="exact").gte("started_at", seven_days_ago).execute()
            assessments_last_7 = self.db.table("assessment_questions").select("id, final_score").eq("status", "completed").gte("created_at", seven_days_ago).execute()
            avg_score = 0
            if assessments_last_7.data:
                scores = [a["final_score"] for a in assessments_last_7.data if a.get("final_score") is not None]
                avg_score = sum(scores) / len(scores) if scores else 0
            fine_tuning_stats = self.db.table("fine_tuning_samples").select("id", count="exact").execute()
            return {
                "period": "last_7_days", "active_students": active_last_7.count or 0,
                "total_messages": messages_last_7.count or 0,
                "avg_messages_per_day": round((messages_last_7.count or 0) / 7, 1),
                "total_sessions": sessions_last_7.count or 0,
                "assessment_attempts": len(assessments_last_7.data or []),
                "average_assessment_score": round(avg_score * 100, 1),
                "fine_tuning_samples_total": fine_tuning_stats.count or 0,
            }
        except Exception as e:
            logger.error(f"Platform health failed: {e}")
            return {}
    
    async def get_subject_difficulty_heatmap(self) -> List[Dict]:
        try:
            knowledge = self.db.table("knowledge_maps").select("subject, concept_id, mastery_score").execute()
            concept_stats = {}
            for k in (knowledge.data or []):
                key = f"{k['subject']}::{k['concept_id']}"
                if key not in concept_stats: concept_stats[key] = {"subject": k["subject"], "concept": k["concept_id"].replace("_", " "), "scores": []}
                concept_stats[key]["scores"].append(k["mastery_score"])
            result = []
            for key, data in concept_stats.items():
                scores = data["scores"]
                avg = sum(scores) / len(scores) if scores else 0
                result.append({"subject": data["subject"], "concept": data["concept"], "average_mastery": round(avg, 1), "student_count": len(scores), "difficulty_level": "easy" if avg >= 70 else "medium" if avg >= 40 else "hard", "percentage_struggling": round(sum(1 for s in scores if s < 40) / len(scores) * 100, 1) if scores else 0})
            result.sort(key=lambda x: x["average_mastery"])
            return result
        except Exception as e:
            logger.error(f"Heatmap failed: {e}")
            return []
    
    async def get_retention_analysis(self) -> Dict:
        try:
            all_students = self.db.table("students").select("id, created_at, last_active_at, session_count").eq("status", "active").execute()
            cohorts = {"week1": 0, "week2": 0, "month1": 0, "month3": 0, "active": 0}
            for student in (all_students.data or []):
                try:
                    created = datetime.fromisoformat(student["created_at"].replace("Z", "+00:00"))
                    last_active = datetime.fromisoformat(student["last_active_at"].replace("Z", "+00:00"))
                    now = datetime.utcnow().replace(tzinfo=created.tzinfo)
                    days_since_active = (now - last_active).days
                    if days_since_active <= 7: cohorts["active"] += 1
                    elif days_since_active <= 14: cohorts["week2"] += 1
                    elif days_since_active <= 30: cohorts["month1"] += 1
                    else: cohorts["month3"] += 1
                except Exception: pass
            total = sum(cohorts.values())
            return {"total_active_students": total, "active_last_7_days": cohorts["active"], "active_8_to_14_days": cohorts["week2"], "active_15_to_30_days": cohorts["month1"], "inactive_30_plus_days": cohorts["month3"], "7_day_retention_rate": round(cohorts["active"] / total * 100, 1) if total > 0 else 0, "30_day_retention_rate": round((cohorts["active"] + cohorts["week2"] + cohorts["month1"]) / total * 100, 1) if total > 0 else 0}
        except Exception as e:
            logger.error(f"Retention failed: {e}")
            return {}
    
    async def get_exam_readiness_overview(self) -> List[Dict]:
        try:
            students_with_exams = self.db.table("students").select("id, primary_exam_target, exam_date, inferred_class_level").not_.is_("exam_date", "null").eq("status", "active").execute()
            result = []
            for student in (students_with_exams.data or []):
                try:
                    exam_dt = datetime.fromisoformat(student["exam_date"])
                    days_until = (exam_dt - datetime.utcnow()).days
                    if days_until < 0: continue
                    knowledge = self.db.table("knowledge_maps").select("mastery_score").eq("student_id", student["id"]).execute()
                    scores = [k["mastery_score"] for k in (knowledge.data or [])]
                    avg_mastery = sum(scores) / len(scores) if scores else 0
                    readiness = "on_track" if avg_mastery >= 60 and days_until > 30 else "needs_attention" if avg_mastery < 40 and days_until < 60 else "at_risk" if avg_mastery < 30 and days_until < 30 else "normal"
                    result.append({"student_id": student["id"], "exam": student["primary_exam_target"], "days_until_exam": days_until, "average_mastery": round(avg_mastery, 1), "concepts_tracked": len(scores), "readiness_category": readiness})
                except Exception: pass
            result.sort(key=lambda x: (x["readiness_category"] == "at_risk", -x["days_until_exam"]))
            return result
        except Exception as e:
            logger.error(f"Exam readiness failed: {e}")
            return []
