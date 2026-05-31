from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import os
from typing import Optional, List
from loguru import logger
from waxprep.app.database.client import get_db_client

router = APIRouter()

@router.get("/admin/students")
async def get_all_students(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    status: str = Query(default="active"),
):
    try:
        db = get_db_client()
        response = (
            db.table("student_learning_summary")
            .select("*")
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return {"students": response.data or [], "count": len(response.data or [])}
    except Exception as e:
        logger.error(f"Admin get students failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/students/{student_id}")
async def get_student_detail(student_id: str):
    try:
        db = get_db_client()

        student = db.table("students").select("*").eq("id", student_id).execute()
        if not student.data:
            raise HTTPException(status_code=404, detail="Student not found")

        profile = db.table("student_profiles").select("*").eq("student_id", student_id).execute()

        knowledge = (
            db.table("knowledge_maps")
            .select("concept_id, subject, mastery_score, last_assessed_at, next_review_due_at")
            .eq("student_id", student_id)
            .order("mastery_score", desc=True)
            .execute()
        )

        misconceptions = (
            db.table("misconceptions")
            .select("*")
            .eq("student_id", student_id)
            .execute()
        )

        recent_events = (
            db.table("learning_events")
            .select("event_type, subject, timestamp, details")
            .eq("student_id", student_id)
            .order("timestamp", desc=True)
            .limit(20)
            .execute()
        )

        recent_sessions = (
            db.table("conversations")
            .select("id, started_at, ended_at, message_count, session_state, summary")
            .eq("student_id", student_id)
            .order("started_at", desc=True)
            .limit(10)
            .execute()
        )

        memory = (
            db.table("memory_artifacts")
            .select("artifact_type, content, composite_score, last_accessed_at")
            .eq("student_id", student_id)
            .eq("status", "active")
            .order("composite_score", desc=True)
            .limit(15)
            .execute()
        )

        return {
            "student": student.data[0] if student.data else {},
            "profile": profile.data[0] if profile.data else {},
            "knowledge_map": knowledge.data or [],
            "misconceptions": misconceptions.data or [],
            "recent_events": recent_events.data or [],
            "recent_sessions": recent_sessions.data or [],
            "memory_artifacts": memory.data or [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin get student detail failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/students/{student_id}/messages")
async def get_student_messages(
    student_id: str,
    conversation_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    try:
        db = get_db_client()
        query = (
            db.table("messages")
            .select("direction, content, message_type, timestamp, intent_classified")
            .eq("student_id", student_id)
            .order("timestamp", desc=False)
            .limit(limit)
        )

        if conversation_id:
            query = query.eq("conversation_id", conversation_id)

        response = query.execute()
        return {"messages": response.data or []}

    except Exception as e:
        logger.error(f"Admin get messages failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/stats")
async def get_system_stats():
    try:
        db = get_db_client()

        total_students = db.table("students").select("id", count="exact").execute()
        active_students = db.table("students").select("id", count="exact").eq("status", "active").execute()
        total_messages = db.table("messages").select("id", count="exact").execute()
        total_sessions = db.table("conversations").select("id", count="exact").execute()
        total_concepts = db.table("knowledge_maps").select("id", count="exact").execute()
        total_misconceptions = db.table("misconceptions").select("id", count="exact").execute()
        pending_notifications = db.table("scheduled_notifications").select("id", count="exact").eq("status", "pending").execute()

        return {
            "total_students": total_students.count or 0,
            "active_students": active_students.count or 0,
            "total_messages": total_messages.count or 0,
            "total_sessions": total_sessions.count or 0,
            "total_concepts_tracked": total_concepts.count or 0,
            "total_misconceptions_logged": total_misconceptions.count or 0,
            "pending_notifications": pending_notifications.count or 0,
        }

    except Exception as e:
        logger.error(f"Admin stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/conversations/{conversation_id}/summary")
async def get_conversation_summary(conversation_id: str):
    try:
        db = get_db_client()
        conv = (
            db.table("conversations")
            .select("*")
            .eq("id", conversation_id)
            .execute()
        )

        if not conv.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"conversation": conv.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin get conversation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/notifications/broadcast")
async def send_broadcast(
    student_ids: List[str],
    message: str,
    platform: str = "whatsapp",
):
    try:
        db = get_db_client()
        from datetime import datetime

        inserted = 0
        for student_id in student_ids:
            db.table("scheduled_notifications").insert({
                "student_id": student_id,
                "notification_type": "broadcast",
                "scheduled_for": datetime.utcnow().isoformat(),
                "platform": platform,
                "content": message,
                "status": "pending",
            }).execute()
            inserted += 1

        return {"scheduled": inserted, "message": f"Broadcast scheduled for {inserted} students"}

    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/dashboard")
async def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "../../static/admin/index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found. Ensure app/static/admin/index.html exists."}

@router.get("/admin/jamb-questions-stats")
async def get_jamb_questions_stats():
    try:
        db = get_db_client()
        response = db.table("jamb_questions").select("subject, topic").execute()
        stats = {}
        for q in (response.data or []):
            subj = q["subject"]
            if subj not in stats:
                stats[subj] = {"total": 0, "topics": set()}
            stats[subj]["total"] += 1
            if q.get("topic"):
                stats[subj]["topics"].add(q["topic"])
        result = [
            {"subject": subj, "total": v["total"], "topics": ", ".join(list(v["topics"])[:5])}
            for subj, v in stats.items()
        ]
        return {"stats": result}
    except Exception as e:
        logger.error(f"JAMB stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/students/{student_id}/parent-report")
async def generate_parent_report(student_id: str, period_days: int = Query(default=30)):
    try:
        from waxprep.app.reports.parent_report import ParentReportGenerator
        generator = ParentReportGenerator()
        report = await generator.generate_report(student_id, period_days)
        if report:
            return {"report": report, "student_id": student_id}
        raise HTTPException(status_code=404, detail="Could not generate report")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/fine-tuning/stats")
async def get_fine_tuning_stats():
    try:
        from waxprep.app.data.fine_tuning_pipeline import FineTuningPipeline
        pipeline = FineTuningPipeline()
        return await pipeline.get_pipeline_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/fine-tuning/export")
async def export_fine_tuning_data(min_quality: float = Query(default=0.7), limit: int = Query(default=1000, le=10000)):
    try:
        from waxprep.app.data.fine_tuning_pipeline import FineTuningPipeline
        pipeline = FineTuningPipeline()
        dataset = await pipeline.export_dataset(min_quality=min_quality, limit=limit)
        return {"count": len(dataset), "samples": dataset[:10], "full_count": len(dataset)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/analytics/platform-health")
async def get_platform_health():
    try:
        from waxprep.app.analytics.advanced_analytics import AdvancedAnalyticsEngine
        engine = AdvancedAnalyticsEngine()
        return await engine.get_platform_health()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/analytics/difficulty-heatmap")
async def get_difficulty_heatmap():
    try:
        from waxprep.app.analytics.advanced_analytics import AdvancedAnalyticsEngine
        engine = AdvancedAnalyticsEngine()
        return {"heatmap": await engine.get_subject_difficulty_heatmap()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/analytics/retention")
async def get_retention():
    try:
        from waxprep.app.analytics.advanced_analytics import AdvancedAnalyticsEngine
        engine = AdvancedAnalyticsEngine()
        return await engine.get_retention_analysis()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/analytics/exam-readiness")
async def get_exam_readiness():
    try:
        from waxprep.app.analytics.advanced_analytics import AdvancedAnalyticsEngine
        engine = AdvancedAnalyticsEngine()
        return {"students": await engine.get_exam_readiness_overview()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
