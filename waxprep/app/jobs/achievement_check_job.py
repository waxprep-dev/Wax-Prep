from loguru import logger
from waxprep.app.database.client import get_db_client
from waxprep.app.gamification.achievement_engine import AchievementEngine

async def run_periodic_achievement_checks():
    try:
        db = get_db_client()
        engine = AchievementEngine()
        active_students = db.table("students").select("id").eq("status", "active").limit(100).execute()
        total_awarded = 0
        for student in (active_students.data or []):
            new = await engine.check_and_award_achievements(student_id=student["id"], event_type="periodic_check", event_data={"source": "scheduled"})
            total_awarded += len(new)
        if total_awarded > 0: logger.info(f"Achievement job awarded {total_awarded} achievements")
    except Exception as e: logger.error(f"Achievement check job failed: {e}")
