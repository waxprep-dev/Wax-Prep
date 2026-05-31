from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client

async def update_study_streaks():
    try:
        db = get_db_client()

        active_students = (
            db.table("students")
            .select("id, last_active_at")
            .eq("status", "active")
            .execute()
        )

        if not active_students.data:
            return

        yesterday_threshold = datetime.utcnow() - timedelta(days=2)

        for student in active_students.data:
            try:
                last_active_str = student.get("last_active_at", "")
                if not last_active_str:
                    continue

                last_active = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                last_active_naive = last_active.replace(tzinfo=None)

                if last_active_naive < yesterday_threshold:
                    db.table("student_profiles").update({
                        "study_streak_current": 0
                    }).eq("student_id", student["id"]).execute()

            except Exception as e:
                logger.warning(f"Streak update failed for {student['id']}: {e}")

        logger.info("Study streaks updated")

    except Exception as e:
        logger.error(f"Streak updater job failed: {e}")
