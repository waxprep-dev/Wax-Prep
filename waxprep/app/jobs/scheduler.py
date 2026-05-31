from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

scheduler = AsyncIOScheduler()

def setup_scheduler():
    from waxprep.app.jobs.session_closer import close_expired_sessions
    from waxprep.app.jobs.notification_dispatcher import dispatch_pending_notifications
    from waxprep.app.jobs.spaced_rep_scheduler import schedule_due_reviews
    from waxprep.app.jobs.streak_updater import update_study_streaks
    from waxprep.app.jobs.re_engagement_job import run_re_engagement_check
    from waxprep.app.jobs.fine_tuning_job import extract_fine_tuning_samples
    from waxprep.app.jobs.achievement_check_job import run_periodic_achievement_checks
    from waxprep.app.jobs.parent_report_job import schedule_parent_reports

    scheduler.add_job(close_expired_sessions, trigger=IntervalTrigger(minutes=5), id="close_expired_sessions", replace_existing=True, misfire_grace_time=60)
    scheduler.add_job(dispatch_pending_notifications, trigger=IntervalTrigger(minutes=10), id="dispatch_notifications", replace_existing=True, misfire_grace_time=120)
    scheduler.add_job(schedule_due_reviews, trigger=CronTrigger(hour=8, minute=0), id="schedule_reviews", replace_existing=True)
    scheduler.add_job(update_study_streaks, trigger=CronTrigger(hour=0, minute=5), id="update_streaks", replace_existing=True)
    scheduler.add_job(run_re_engagement_check, trigger=CronTrigger(hour=9, minute=0), id="re_engagement", replace_existing=True)
    scheduler.add_job(extract_fine_tuning_samples, trigger=CronTrigger(hour=4, minute=0), id="fine_tuning_extraction", replace_existing=True)
    scheduler.add_job(run_periodic_achievement_checks, trigger=IntervalTrigger(hours=6), id="achievement_checks", replace_existing=True, misfire_grace_time=300)
    scheduler.add_job(schedule_parent_reports, trigger=CronTrigger(day=1, hour=10, minute=0), id="parent_reports", replace_existing=True)

    scheduler.start()
    logger.info("WaxPrep background scheduler started with 8 jobs")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")
