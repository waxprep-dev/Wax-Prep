import secrets
import string
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client

REFERRAL_REWARD_XP = 200
REFERRAL_FRIEND_BONUS_XP = 100
PREMIUM_DAYS_PER_REFERRAL = 7

class ReferralSystem:
    def __init__(self):
        self.db = get_db_client()
    
    def generate_referral_code(self, student_name: str = None) -> str:
        prefix = "".join(c.upper() for c in student_name if c.isalpha())[:4] if student_name else "WAX"
        suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        return f"{prefix}{suffix}"
    
    async def get_or_create_referral_code(self, student_id: str, student_name: str = None) -> str:
        try:
            existing = self.db.table("referral_codes").select("code").eq("student_id", student_id).execute()
            if existing.data: return existing.data[0]["code"]
            code = self.generate_referral_code(student_name)
            while True:
                check = self.db.table("referral_codes").select("id").eq("code", code).execute()
                if not check.data: break
                code = self.generate_referral_code()
            self.db.table("referral_codes").insert({"student_id": student_id, "code": code}).execute()
            return code
        except Exception as e:
            logger.error(f"Referral code creation failed: {e}")
            return "ERROR"
    
    async def process_referral(self, new_student_id: str, referral_code: str) -> bool:
        try:
            code_record = self.db.table("referral_codes").select("student_id, uses, max_uses").eq("code", referral_code.upper()).execute()
            if not code_record.data: return False
            record = code_record.data[0]
            if record["uses"] >= record["max_uses"]: return False
            if record["student_id"] == new_student_id: return False
            existing_conversion = self.db.table("referral_conversions").select("id").eq("referred_student_id", new_student_id).execute()
            if existing_conversion.data: return False
            self.db.table("referral_conversions").insert({"referrer_student_id": record["student_id"], "referred_student_id": new_student_id}).execute()
            self.db.table("referral_codes").update({"uses": record["uses"] + 1}).eq("code", referral_code.upper()).execute()
            await self._grant_referral_rewards(referrer_id=record["student_id"], referred_id=new_student_id)
            return True
        except Exception as e:
            logger.error(f"Referral processing failed: {e}")
            return False
    
    async def _grant_referral_rewards(self, referrer_id: str, referred_id: str) -> None:
        try:
            xp_response = self.db.table("student_xp").select("total_xp").eq("student_id", referrer_id).execute()
            if xp_response.data:
                new_xp = xp_response.data[0]["total_xp"] + REFERRAL_REWARD_XP
                self.db.table("student_xp").update({"total_xp": new_xp}).eq("student_id", referrer_id).execute()
            else:
                self.db.table("student_xp").insert({"student_id": referrer_id, "total_xp": REFERRAL_REWARD_XP, "current_level": 1}).execute()
            
            premium_expires = datetime.utcnow() + timedelta(days=PREMIUM_DAYS_PER_REFERRAL)
            self.db.table("student_subscriptions").insert({"student_id": referrer_id, "tier_id": "basic", "expires_at": premium_expires.isoformat(), "is_active": True, "payment_reference": f"referral_reward_{referred_id[:8]}"}).execute()
            
            referred_xp = self.db.table("student_xp").select("total_xp").eq("student_id", referred_id).execute()
            if referred_xp.data:
                new_xp = referred_xp.data[0]["total_xp"] + REFERRAL_FRIEND_BONUS_XP
                self.db.table("student_xp").update({"total_xp": new_xp}).eq("student_id", referred_id).execute()
            else:
                self.db.table("student_xp").insert({"student_id": referred_id, "total_xp": REFERRAL_FRIEND_BONUS_XP, "current_level": 1}).execute()
            
            logger.info(f"Referral rewards granted: referrer={referrer_id}, referred={referred_id}")
        except Exception as e:
            logger.error(f"Referral reward grant failed: {e}")
    
    async def get_referral_stats(self, student_id: str) -> Dict:
        try:
            code_record = self.db.table("referral_codes").select("code, uses").eq("student_id", student_id).execute()
            conversions = self.db.table("referral_conversions").select("id", count="exact").eq("referrer_student_id", student_id).execute()
            code = code_record.data[0]["code"] if code_record.data else None
            total_referrals = conversions.count or 0
            return {"referral_code": code, "total_referrals": total_referrals, "premium_days_earned": total_referrals * PREMIUM_DAYS_PER_REFERRAL, "xp_earned": total_referrals * REFERRAL_REWARD_XP, "referral_message": f"Share your code *{code}* with friends! Each friend who joins gives you {PREMIUM_DAYS_PER_REFERRAL} days of Basic plan and {REFERRAL_REWARD_XP} XP."}
        except Exception as e:
            logger.error(f"Referral stats failed: {e}")
            return {}
    
    def is_referral_request(self, message: str) -> bool:
        triggers = ["referral code", "refer a friend", "invite friend", "my code", "share waxprep", "how to invite", "referral link"]
        return any(t in message.lower() for t in triggers)
