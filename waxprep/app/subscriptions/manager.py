import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client

FREE_LIMIT_MESSAGE = """You have used your 30 free messages for today.

WaxPrep is free with 30 messages per day. When you need more:

📚 Student Plan — ₦800/month
80 messages per day, WAEC practice, JAMB questions, study plans.

🚀 Premium Plan — ₦2,000/month
Unlimited messages, voice responses, parent reports — everything.

🎯 JAMB Intensive — ₦3,000 for 3 months
Full access for the entire JAMB preparation season.

To upgrade, send: UPGRADE

Your daily messages reset at midnight. Your progress is always saved."""

class SubscriptionManager:
    def __init__(self):
        self.db = get_db_client()
        self._tier_cache: Dict[str, Dict] = {}
    
    async def get_student_tier(self, student_id: str) -> Dict[str, Any]:
        try:
            sub = self.db.table("student_subscriptions").select("*, subscription_tiers(*)").eq("student_id", student_id).eq("is_active", True).order("started_at", desc=True).limit(1).execute()
            if sub.data and sub.data[0].get("subscription_tiers"):
                tier_data = sub.data[0]["subscription_tiers"]
                expires = sub.data[0].get("expires_at")
                if expires:
                    expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    if datetime.utcnow().replace(tzinfo=expires_dt.tzinfo) > expires_dt:
                        await self._expire_subscription(sub.data[0]["id"])
                        return await self._get_free_tier()
                return tier_data
            await self._ensure_free_subscription(student_id)
            return await self._get_free_tier()
        except Exception as e:
            logger.error(f"Subscription check failed: {e}")
            return await self._get_free_tier()
    
    async def check_message_allowance(self, student_id: str) -> Tuple[bool, str]:
        tier = await self.get_student_tier(student_id)
        daily_limit = tier.get("daily_message_limit", 30)
        if daily_limit == -1: return True, ""
        today = date.today()
        count_response = self.db.table("daily_message_counts").select("count").eq("student_id", student_id).eq("date", today.isoformat()).execute()
        current_count = count_response.data[0]["count"] if count_response.data else 0
        if current_count >= daily_limit: return False, FREE_LIMIT_MESSAGE
        return True, ""
    
    async def increment_daily_count(self, student_id: str) -> None:
        try:
            today = date.today()
            existing = self.db.table("daily_message_counts").select("count").eq("student_id", student_id).eq("date", today.isoformat()).execute()
            if existing.data:
                self.db.table("daily_message_counts").update({"count": existing.data[0]["count"] + 1}).eq("student_id", student_id).eq("date", today.isoformat()).execute()
            else:
                self.db.table("daily_message_counts").insert({"student_id": student_id, "date": today.isoformat(), "count": 1}).execute()
        except Exception as e: logger.warning(f"Daily count failed: {e}")
    
    async def can_use_feature(self, student_id: str, feature: str) -> bool:
        tier = await self.get_student_tier(student_id)
        features = tier.get("features", {})
        if isinstance(features, str): features = json.loads(features)
        return features.get(feature, False)
    
    async def get_upgrade_message(self, feature: str) -> str:
        feature_messages = {
            "waec_practice": "WAEC practice requires the Student Plan (₦800/month) or higher.",
            "jamb_practice": "JAMB practice requires the Student Plan (₦800/month) or higher.",
            "study_plan": "Personalized study plans require the Student Plan (₦800/month) or higher.",
            "voice_responses": "Voice responses are a Premium feature (₦2,000/month).",
            "parent_reports": "Parent reports are a Premium feature (₦2,000/month).",
        }
        base = feature_messages.get(feature, "This feature requires a paid subscription.")
        return f"{base}\n\nTo upgrade, reply: UPGRADE\n\nOr keep using the free tier — 30 messages per day, your progress is always saved."
    
    async def _ensure_free_subscription(self, student_id: str) -> None:
        try:
            existing = self.db.table("student_subscriptions").select("id").eq("student_id", student_id).execute()
            if not existing.data:
                self.db.table("student_subscriptions").insert({"student_id": student_id, "tier_id": "free", "is_active": True}).execute()
        except Exception: pass
    
    async def _get_free_tier(self) -> Dict:
        if "free" not in self._tier_cache:
            try:
                tier = self.db.table("subscription_tiers").select("*").eq("id", "free").execute()
                if tier.data: self._tier_cache["free"] = tier.data[0]
            except Exception: pass
        return self._tier_cache.get("free", {"id": "free", "name": "Free", "daily_message_limit": 30, "features": {"basic_teaching": True}})
    
    async def _expire_subscription(self, subscription_id: str) -> None:
        try:
            student = self.db.table("student_subscriptions").select("student_id").eq("id", subscription_id).execute()
            self.db.table("student_subscriptions").update({"is_active": False}).eq("id", subscription_id).execute()
            if student.data:
                self.db.table("student_subscriptions").insert({"student_id": student.data[0]["student_id"], "tier_id": "free", "is_active": True}).execute()
        except Exception: pass
