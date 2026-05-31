from loguru import logger
from waxprep.app.reports.parent_report import ParentReportGenerator

async def schedule_parent_reports():
    try:
        generator = ParentReportGenerator()
        count = await generator.schedule_monthly_reports()
        if count > 0: logger.info(f"Parent report job scheduled for {count} students")
    except Exception as e: logger.error(f"Parent report job failed: {e}")
