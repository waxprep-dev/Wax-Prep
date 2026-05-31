from loguru import logger
from waxprep.app.notifications.re_engagement import ReEngagementSystem

async def run_re_engagement_check():
    try:
        system = ReEngagementSystem()
        scheduled = await system.find_and_schedule_re_engagements()
        if scheduled > 0:
            logger.info(f"Re-engagement check complete: {scheduled} messages scheduled")
    except Exception as e:
        logger.error(f"Re-engagement job failed: {e}")
