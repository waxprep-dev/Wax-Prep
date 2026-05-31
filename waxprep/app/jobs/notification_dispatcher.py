from datetime import datetime
from loguru import logger
from waxprep.app.database.client import get_db_client
from waxprep.app.core.constants import Platform

async def dispatch_pending_notifications():
    try:
        db = get_db_client()
        pending = (
            db.table("scheduled_notifications")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", datetime.utcnow().isoformat())
            .limit(20)
            .execute()
        )

        if not pending.data:
            return

        dispatched = 0
        for notification in pending.data:
            try:
                student = (
                    db.table("students")
                    .select("platform_whatsapp, platform_telegram, status")
                    .eq("id", notification["student_id"])
                    .execute()
                )

                if not student.data or student.data[0]["status"] != "active":
                    db.table("scheduled_notifications").update({
                        "status": "cancelled"
                    }).eq("id", notification["id"]).execute()
                    continue

                student_data = student.data[0]
                platform = notification["platform"]
                content = notification["content"]

                if platform == "whatsapp" and student_data.get("platform_whatsapp"):
                    from waxprep.app.gateways.whatsapp.sender import WhatsAppSender
                    sender = WhatsAppSender()
                    await sender.send_text(student_data["platform_whatsapp"], content)

                elif platform == "telegram" and student_data.get("platform_telegram"):
                    from waxprep.app.gateways.telegram.sender import TelegramSender
                    sender = TelegramSender()
                    await sender.send_text(student_data["platform_telegram"], content)

                db.table("scheduled_notifications").update({
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                }).eq("id", notification["id"]).execute()

                dispatched += 1

            except Exception as e:
                logger.error(f"Failed to dispatch notification {notification['id']}: {e}")
                db.table("scheduled_notifications").update({
                    "status": "failed",
                    "error_message": str(e)[:200],
                }).eq("id", notification["id"]).execute()

        if dispatched > 0:
            logger.info(f"Dispatched {dispatched} notifications")

    except Exception as e:
        logger.error(f"Notification dispatcher job failed: {e}")
