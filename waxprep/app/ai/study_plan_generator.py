import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

STUDY_PLAN_ANALYSIS_PROMPT = """You are WaxPrep analyzing a Nigerian student's current academic profile to build a personalized study plan.

Student profile:
- Name: {name}
- Class level: {class_level}
- Exam: {exam}
- Days until exam: {days}
- Current subjects with mastery data:
{mastery_summary}
- Active misconceptions: {misconceptions}
- Learning style: {learning_style}
- Average daily study time: {daily_hours} hours
- Current weaknesses: {weaknesses}

Based on this data, create a detailed analysis that includes:
1. The student's readiness level for each subject (0-100%)
2. Priority ranking of subjects from most to least urgent
3. Specific concepts that need the most attention per subject
4. Recommended daily study minutes per subject
5. Key milestones for weeks 4, 8, and 12

Return ONLY a JSON object with this structure:
{{
    "overall_readiness": number 0-100,
    "subject_readiness": {{"subject": readiness_percent}},
    "subject_priority": ["ordered list of subjects most to least urgent"],
    "critical_concepts": {{"subject": ["concept1", "concept2"]}},
    "daily_minutes_per_subject": {{"subject": minutes}},
    "week4_milestone": "string describing what student should achieve by week 4",
    "week8_milestone": "string describing week 8 target",
    "week12_milestone": "string describing final week target",
    "biggest_risk": "string describing the biggest risk to exam success",
    "biggest_strength": "string describing what is already solid"
}}"""

STUDY_PLAN_GENERATION_PROMPT = """You are WaxPrep creating a personalized 90-day study plan for a Nigerian student preparing for {exam}.

Student: {name}
Days remaining: {days}
Analysis: {analysis}

Create a weekly study plan for the next 13 weeks (or until exam day if sooner).

Rules:
1. Each week should have specific topics and subjects
2. Early weeks: cover weakest areas from the analysis
3. Middle weeks: build on strengths and fill remaining gaps
4. Final weeks: revision and past question practice only
5. Include at least one practice session (WAEC or JAMB) per week from week 4
6. Rest day each week — do not schedule study every single day
7. Use the Nigerian academic calendar context — students have school, family duties
8. Be specific about WHAT to study, not just which subject
9. The plan should feel ambitious but achievable for a motivated student with 2-3 hours per day

Write this as a natural message from WaxPrep, week by week. Not a formal document. More like a smart teacher talking through the plan with the student.

Maximum 800 words. The student will receive this on WhatsApp. Make it readable on a phone screen."""

class StudyPlanGenerator:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()
    
    async def generate_study_plan(self, student_id, exam, exam_date=None) -> str:
        try:
            profile = self.db.table("student_profiles").select("*").eq("student_id", student_id).execute()
            student = self.db.table("students").select("*").eq("id", student_id).execute()
            knowledge = self.db.table("knowledge_maps").select("concept_id, subject, mastery_score").eq("student_id", student_id).execute()
            misconceptions = self.db.table("misconceptions").select("description, subject").eq("student_id", student_id).eq("status", "active").limit(10).execute()
            
            name = "there"
            class_level = "SS3"
            weaknesses = []
            if profile.data:
                p = profile.data[0]
                name = p.get("student_name", "there")
                weak_raw = p.get("weak_subjects", "[]")
                weaknesses = json.loads(weak_raw) if isinstance(weak_raw, str) else (weak_raw or [])
            if student.data:
                s = student.data[0]
                class_level = s.get("inferred_class_level", "SS3")
                if not exam_date: exam_date = s.get("exam_date")
            
            days = 90
            if exam_date:
                try:
                    exam_dt = datetime.fromisoformat(exam_date)
                    days = max(7, (exam_dt - datetime.utcnow()).days)
                except Exception: days = 90
            
            mastery_by_subject = {}
            for k in (knowledge.data or []):
                subj = k["subject"]
                if subj not in mastery_by_subject: mastery_by_subject[subj] = []
                mastery_by_subject[subj].append((k["concept_id"].replace("_", " "), k["mastery_score"]))
            
            mastery_summary_lines = []
            for subj, concepts in mastery_by_subject.items():
                avg = sum(c[1] for c in concepts) / len(concepts) if concepts else 0
                weak_concepts = [c[0] for c in concepts if c[1] < 50][:3]
                mastery_summary_lines.append(f"  {subj}: avg mastery {avg:.0f}%, weak spots: {', '.join(weak_concepts) or 'none yet'}")
            
            misconception_list = [m["description"] for m in (misconceptions.data or [])][:5]
            
            analysis_prompt = STUDY_PLAN_ANALYSIS_PROMPT.format(
                name=name, class_level=class_level, exam=exam, days=days,
                mastery_summary="\n".join(mastery_summary_lines) or "No mastery data yet",
                misconceptions=", ".join(misconception_list) or "None",
                learning_style="balanced", daily_hours=2,
                weaknesses=", ".join(weaknesses) or "Not yet identified",
            )
            
            analysis_response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model, messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=600, temperature=0.2,
            )
            raw_analysis = analysis_response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            try: analysis = json.loads(raw_analysis)
            except Exception: analysis = {"overall_readiness": 45, "biggest_risk": "insufficient time"}
            
            plan_prompt = STUDY_PLAN_GENERATION_PROMPT.format(exam=exam, name=name, days=days, analysis=json.dumps(analysis))
            plan_response = self.groq_client.chat.completions.create(
                model=settings.groq_primary_model, messages=[{"role": "user", "content": plan_prompt}],
                max_tokens=1000, temperature=0.6,
            )
            plan_text = plan_response.choices[0].message.content.strip()
            
            try:
                self.db.table("memory_artifacts").insert({
                    "student_id": student_id, "artifact_type": "study_plan",
                    "content": f"{days}-day {exam} study plan. Readiness: {analysis.get('overall_readiness', 0)}%. Risk: {analysis.get('biggest_risk', 'unknown')}.",
                    "relevance_tags": json.dumps(["exam_prep", exam.lower(), "study_plan"]),
                    "impact_score": 0.95, "composite_score": 1.0,
                }).execute()
            except Exception: pass
            
            return plan_text
        except Exception as e:
            logger.error(f"Study plan failed: {e}")
            return f"I ran into an issue generating the study plan. For {exam} with about 90 days, focus on your weakest subjects first, do one past question session per week, and leave the final two weeks for revision. Which subject do you want to start with?"
    
    def is_study_plan_request(self, message: str) -> bool:
        triggers = ["study plan", "make me a plan", "create a plan", "give me a schedule", "how should i study", "what should i study", "plan my studies", "90 day plan", "exam plan", "revision plan", "study schedule"]
        return any(t in message.lower() for t in triggers)
