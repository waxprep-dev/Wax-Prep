from loguru import logger
from waxprep.app.memory.session_summary import SessionSummaryGenerator

async def close_expired_sessions():
    try:
        generator = SessionSummaryGenerator()
        closed = await generator.check_and_close_inactive_sessions()
        if closed > 0:
            logger.info(f"Closed {closed} expired sessions with summaries generated")
    except Exception as e:
        logger.error(f"Session closer job failed: {e}")
