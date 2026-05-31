import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from loguru import logger
from waxprep.app.database.client import get_db_client

class ScholarshipAdvisor:
    def __init__(self):
        self.db = get_db_client()
    
    def is_scholarship_request(self, message: str) -> bool:
        triggers = ["scholarship", "bursary", "scholarship application", "financial aid", "education fund", "study grant", "how to get scholarship", "free university", "scholarship opportunity"]
        return any(t in message.lower() for t in triggers)
    
    def is_admission_request(self, message: str) -> bool:
        triggers = ["admission", "jamb result", "jamb admission", "university admission", "post utme result", "admission list", "change of institution", "direct entry", "admission status", "admission portal", "supplementary admission"]
        return any(t in message.lower() for t in triggers)
    
    async def get_relevant_scholarships(self, student_id: str, class_level: str, exam_target: str = None) -> str:
        try:
            scholarships = self.db.table("scholarships").select("*").eq("is_active", True).execute()
            relevant = []
            for s in (scholarships.data or []):
                target_levels = json.loads(s["target_levels"]) if isinstance(s["target_levels"], str) else s["target_levels"]
                if class_level in target_levels or not target_levels: relevant.append(s)
            if not relevant: return "I don't have scholarship information matching your exact profile right now. The Federal Government scholarship (scholarship.fmoe.gov.ng) and state government scholarships are the most accessible. Do you want me to explain how to apply?"
            response_lines = [f"Here are scholarships available for {class_level} students:\n"]
            for i, s in enumerate(relevant[:5], 1):
                deadline_str = ""
                if s.get("deadline"):
                    try:
                        deadline = date.fromisoformat(s["deadline"])
                        days_remaining = (deadline - date.today()).days
                        deadline_str = f" | Deadline: {deadline.strftime('%B %d, %Y')}"
                        if days_remaining < 0: deadline_str += " (CLOSED)"
                        elif days_remaining < 30: deadline_str += f" ({days_remaining} days left!)"
                    except Exception: pass
                amount = s.get("amount_description") or (f"₦{s['amount_naira']:,}" if s.get("amount_naira") else "Amount not specified")
                response_lines.append(f"{i}. *{s['title']}*\n   Provider: {s['provider']}\n   Amount: {amount}{deadline_str}\n   Eligibility: {(s.get('eligibility_criteria') or '')[:150]}...\n   Apply: {s.get('application_url', 'Check provider website')}\n")
            response_lines.append("\nWant more details about any of these? Just ask.")
            response_lines.append("\nImportant: Always verify scholarship information directly on the official website before applying.")
            return "\n".join(response_lines)
        except Exception as e:
            logger.error(f"Scholarship search failed: {e}")
            return "I'm having trouble accessing scholarship data. The most reliable source is scholarship.fmoe.gov.ng for Federal Government scholarships."
    
    async def get_admission_guidance(self, message: str, student_id: str) -> str:
        message_lower = message.lower()
        if "admission list" in message_lower or "check admission" in message_lower:
            return "To check your JAMB/CAPS admission status:\n\n1. Go to jamb.gov.ng\n2. Click on 'e-Facility' or 'CAPS'\n3. Log in with your JAMB registration number\n4. Check your admission status\n\n'Offered Admission': Accept it through CAPS.\n'Not Yet Admitted': Still being processed.\n'Rejected': Consider change of institution.\n\nWhich university are you checking for?"
        if "change of institution" in message_lower or "change of course" in message_lower:
            return "Change of Institution or Course on JAMB:\n\n1. Log into JAMB CAPS at jamb.gov.ng\n2. Click 'Change of Institution' or 'Change of Course'\n3. Select your new institution or course\n4. Pay the change fee\n\nImportant: You can only do this once per UTME cycle.\n\nWhat institution or course are you considering?"
        if "direct entry" in message_lower:
            return "Direct Entry (DE) Admission:\n\nDE is for candidates with: A-Level, OND (Lower Credit), HND, NCE, or First Degree.\n\nProcess:\n1. Register for JAMB Direct Entry (not UTME)\n2. Select universities and courses\n3. Universities invite for screening\n4. Accept admission through CAPS\n\nNote: DE candidates enter at 200 Level.\n\nDo you have any of the above qualifications?"
        return "University Admission in Nigeria — Key Information:\n\nThe Process: JAMB → Score → Post-UTME → Admission → Accept on CAPS\n\nImportant portals:\n- JAMB Portal: jamb.gov.ng\n- Individual university portals for school fees, accommodation\n\nWhat specific aspect do you need help with? You can ask about: checking admission status, change of institution, direct entry, post-UTME preparation, or cut-off marks."
