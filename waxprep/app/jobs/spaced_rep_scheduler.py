from loguru import logger
from waxprep.app.database.client import get_db_client
from waxprep.app.memory.spaced_repetition import SpacedRepetitionEngine

async def schedule_due_reviews():
    try:
        db = get_db_client()
        engine = SpacedRepetitionEngine()

        active_students = (
            db.table("students")
            .select("id, platform_whatsapp, platform_telegram")
            .eq("status", "active")
            .execute()
        )

        if not active_students.data:
            return

        total_scheduled = 0
        for student in active_students.data:
            platform = "whatsapp" if student.get("platform_whatsapp") else "telegram"
            count = await engine.schedule_review_notifications(
                student_id=student["id"],
                platform=platform,
            )
            total_scheduled += count

        if total_scheduled > 0:
            logger.info(f"Scheduled {total_scheduled} spaced repetition reviews")

    except Exception as e:
        logger.error(f"Spaced rep scheduler job failed: {e}")
