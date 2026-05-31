from loguru import logger
from waxprep.app.database.client import get_db_client
from waxprep.app.data.fine_tuning_pipeline import FineTuningPipeline

async def extract_fine_tuning_samples():
    try:
        db = get_db_client()
        pipeline = FineTuningPipeline()
        unprocessed = db.table("conversations").select("id, student_id").eq("is_active", False).not_.is_("summary", "null").limit(20).execute()
        if not unprocessed.data: return
        total_extracted = 0
        for conv in unprocessed.data:
            student = db.table("students").select("wax_code").eq("id", conv["student_id"]).execute()
            wax_code = student.data[0]["wax_code"] if student.data else "UNKNOWN"
            extracted = await pipeline.extract_from_session(conversation_id=conv["id"], student_wax_code=wax_code)
            total_extracted += extracted
        if total_extracted > 0: logger.info(f"FT job extracted {total_extracted} samples from {len(unprocessed.data)} sessions")
    except Exception as e: logger.error(f"FT extraction job failed: {e}")
