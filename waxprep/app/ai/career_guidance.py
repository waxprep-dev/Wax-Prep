import json
from typing import Dict, Any, List, Optional
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

NIGERIAN_CAREER_PATHS = {
    "medicine": {"title": "Medicine and Surgery (MBBS)", "jamb_subjects": ["Biology", "Chemistry", "Physics", "English"], "minimum_jamb": 280, "duration_years": 6, "career_prospects": ["Medical Doctor", "Surgeon", "Specialist", "Public Health Doctor"], "average_salary_range_naira": "₦500K — ₦2M+ per month", "realities": "Extremely competitive. 6 years + housemanship + residency. JAMB below 280 rarely considered.", "alternatives_if_jamb_low": ["Nursing", "Pharmacy", "Medical Lab Science", "Physiotherapy"]},
    "engineering": {"title": "Engineering", "jamb_subjects": ["Mathematics", "Physics", "Chemistry", "English"], "minimum_jamb": 200, "duration_years": 5, "career_prospects": ["Mechanical", "Civil", "Electrical", "Petroleum", "Software Engineer"], "average_salary_range_naira": "₦150K — ₦500K+ per month", "realities": "5-year programme. Petroleum engineering has highest earning in Nigeria. COREN registration required."},
    "law": {"title": "Law (LLB)", "jamb_subjects": ["English", "Government/CRS", "Literature/Economics", "Arts subject"], "minimum_jamb": 200, "duration_years": 5, "career_prospects": ["Barrister", "Corporate Lawyer", "Judge", "Legal Consultant"], "average_salary_range_naira": "₦100K — ₦2M+ per month", "realities": "5 years + Law School. Must pass Bar Finals. Lagos firms pay significantly more."},
    "pharmacy": {"title": "Pharmacy (B.Pharm)", "jamb_subjects": ["Chemistry", "Biology", "Maths/Physics", "English"], "minimum_jamb": 200, "duration_years": 5, "career_prospects": ["Hospital Pharmacist", "Community Pharmacist", "Industrial Pharmacist"], "average_salary_range_naira": "₦200K — ₦600K per month"},
    "accounting": {"title": "Accounting", "jamb_subjects": ["Economics", "Mathematics", "English", "Accounting/Commerce"], "minimum_jamb": 160, "duration_years": 4, "career_prospects": ["Chartered Accountant", "Auditor", "Financial Analyst", "CFO"], "average_salary_range_naira": "₦100K — ₦500K+ per month; higher with ICAN/ACCA"},
    "computer_science": {"title": "Computer Science", "jamb_subjects": ["Mathematics", "Physics", "English", "Chemistry/Biology"], "minimum_jamb": 160, "duration_years": 4, "career_prospects": ["Software Developer", "Data Scientist", "Cybersecurity", "AI Engineer"], "average_salary_range_naira": "₦200K — ₦2M+ per month; international remote jobs pay dollars", "realities": "Fastest growing sector. Nigerian tech ecosystem booming. Many work remotely for dollar salaries."},
    "economics": {"title": "Economics", "jamb_subjects": ["Economics", "Mathematics", "English", "Government/Commerce"], "minimum_jamb": 160, "duration_years": 4, "career_prospects": ["Economist", "Financial Analyst", "Investment Banker"], "average_salary_range_naira": "₦150K — ₦800K per month"},
    "nursing": {"title": "Nursing Science (BNSc)", "jamb_subjects": ["Biology", "Chemistry", "Physics/Maths", "English"], "minimum_jamb": 160, "duration_years": 5, "career_prospects": ["Registered Nurse", "Midwife", "International Nursing (diaspora)"], "average_salary_range_naira": "₦80K — ₦300K per month in Nigeria; much higher abroad", "realities": "Nigerian nurses in high demand abroad (UK, USA, Canada). Strong career for international opportunities."},
    "architecture": {"title": "Architecture", "jamb_subjects": ["Mathematics", "Physics", "English", "Art/Tech Drawing"], "minimum_jamb": 160, "duration_years": 6, "career_prospects": ["Architect", "Urban Planner", "Real Estate Developer"], "average_salary_range_naira": "₦150K — ₦500K per month"},
    "mass_communication": {"title": "Mass Communication", "jamb_subjects": ["English", "Government/Literature", "Two Arts subjects"], "minimum_jamb": 160, "duration_years": 4, "career_prospects": ["Journalist", "PR Professional", "Digital Content Creator"], "average_salary_range_naira": "₦80K — ₦400K per month"},
}

CAREER_GUIDANCE_PROMPT = """You are WaxPrep giving career guidance to a Nigerian student.
Student: {name}, Class: {class_level}, Subjects: {subjects}, Strong: {strong_subjects}, Weak: {weak_subjects}, JAMB: {jamb_score}
Career interest: {career_interest}
Career info: {career_info}
Provide personalized guidance: address their interest directly, give realistic expectations, mention Nigerian universities, address JAMB honestly, mention earning in Naira, suggest focus subjects. Sound like WaxPrep. Max 300 words."""

class CareerGuidanceEngine:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()
    
    def is_career_request(self, message: str) -> bool:
        triggers = ["career", "what course", "what to study", "i want to be", "i want to become", "best course", "which university", "course to study", "profession", "what subject for", "jamb subject for", "study medicine", "study law", "study engineering", "study nursing", "study pharmacy", "job prospects", "salary", "earning potential", "which is better course"]
        return any(t in message.lower() for t in triggers)
    
    async def provide_career_guidance(self, message: str, student_id: str) -> str:
        try:
            student = self.db.table("students").select("*").eq("id", student_id).execute()
            profile = self.db.table("student_profiles").select("*").eq("student_id", student_id).execute()
            km = self.db.table("knowledge_maps").select("subject, mastery_score").eq("student_id", student_id).execute()
            name = "there"; class_level = "SS2"; subjects = []; strong = []; weak = []; jamb_score = None
            if profile.data: name = profile.data[0].get("student_name", "there")
            if student.data: s = student.data[0]; class_level = s.get("inferred_class_level", "SS2")
            subject_mastery = {}
            for k in (km.data or []):
                subj = k["subject"]
                if subj not in subject_mastery: subject_mastery[subj] = []
                subject_mastery[subj].append(k["mastery_score"])
            for subj, scores in subject_mastery.items():
                avg = sum(scores) / len(scores) if scores else 0
                if avg >= 60: strong.append(subj)
                elif avg < 40: weak.append(subj)
                subjects.append(subj)
            detected_career = self._detect_career_from_message(message)
            career_info = NIGERIAN_CAREER_PATHS.get(detected_career, {}) if detected_career else {}
            prompt = CAREER_GUIDANCE_PROMPT.format(name=name, class_level=class_level, subjects=", ".join(subjects[:5]) or "not yet determined", strong_subjects=", ".join(strong[:3]) or "not assessed", weak_subjects=", ".join(weak[:3]) or "none", jamb_score=jamb_score or "not yet sat", career_interest=message[:100], career_info=json.dumps(career_info)[:500] if career_info else "No data")
            response = self.groq_client.chat.completions.create(model=settings.groq_primary_model, messages=[{"role": "user", "content": prompt}], max_tokens=400, temperature=0.6)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Career guidance failed: {e}")
            detected = self._detect_career_from_message(message)
            if detected and detected in NIGERIAN_CAREER_PATHS:
                info = NIGERIAN_CAREER_PATHS[detected]
                return f"For {info['title']}:\n\nJAMB subjects: {', '.join(info['jamb_subjects'])}\nMinimum JAMB: {info.get('minimum_jamb', 160)}+\nDuration: {info.get('duration_years', 4)} years\n\nCareer prospects: {', '.join(info['career_prospects'][:3])}\n\nWhat subjects are you studying?"
            return "Tell me which career you're interested in and I'll give you honest, specific guidance for the Nigerian university system."
    
    def _detect_career_from_message(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        career_keywords = {"medicine": ["medicine", "medical", "doctor", "mbbs", "surgery", "physician"], "engineering": ["engineering", "engineer", "electrical", "mechanical", "civil", "petroleum"], "law": ["law", "lawyer", "barrister", "solicitor", "legal", "llb"], "pharmacy": ["pharmacy", "pharmacist"], "accounting": ["accounting", "accountant", "finance", "ican"], "computer_science": ["computer science", "software", "programming", "tech", "developer", "coding"], "economics": ["economics", "economist"], "nursing": ["nursing", "nurse"], "architecture": ["architecture", "architect"], "mass_communication": ["mass communication", "journalism", "media"]}
        for career, keywords in career_keywords.items():
            if any(kw in message_lower for kw in keywords): return career
        return None
