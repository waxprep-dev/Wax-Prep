from fastapi import APIRouter, HTTPException, Header, Query, Depends
from typing import Optional, List
from loguru import logger
from waxprep.app.database.client import get_db_client
import hashlib
import hmac

router = APIRouter()

def verify_school_api_key(x_school_api_key: str = Header(...)):
    if not x_school_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    school = get_db_client().table("school_partners").select("id, name, api_key_hash, is_active").execute()
    for s in (school.data or []):
        expected_hash = hashlib.sha256(x_school_api_key.encode()).hexdigest()
        if hmac.compare_digest(expected_hash, s.get("api_key_hash", "")):
            if s.get("is_active"): return s
    raise HTTPException(status_code=401, detail="Invalid API key")

@router.get("/school/students")
async def get_school_students(school: dict = Depends(verify_school_api_key), class_level: Optional[str] = None, limit: int = Query(default=50, le=200)):
    try:
        db = get_db_client()
        query = db.table("school_student_links").select("*, students(wax_code, inferred_class_level, last_active_at, session_count), student_profiles(student_name, current_subject, study_streak_current)").eq("school_id", school["id"])
        if class_level: query = query.eq("class_level", class_level)
        response = query.limit(limit).execute()
        return {"school": school["name"], "students": response.data or []}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/school/class-analytics")
async def get_class_analytics(school: dict = Depends(verify_school_api_key), class_level: Optional[str] = None, subject: Optional[str] = None):
    try:
        db = get_db_client()
        student_ids_response = db.table("school_student_links").select("student_id").eq("school_id", school["id"]).execute()
        if not student_ids_response.data: return {"analytics": {}, "message": "No students enrolled"}
        student_ids = [s["student_id"] for s in student_ids_response.data]
        km_query = db.table("knowledge_maps").select("concept_id, subject, mastery_score, student_id").in_("student_id", student_ids[:50])
        if subject: km_query = km_query.eq("subject", subject)
        km_response = km_query.execute()
        concept_stats = {}
        for k in (km_response.data or []):
            key = f"{k['subject']}:{k['concept_id']}"
            if key not in concept_stats: concept_stats[key] = {"scores": [], "subject": k["subject"], "concept": k["concept_id"]}
            concept_stats[key]["scores"].append(k["mastery_score"])
        analytics = []
        for key, data in concept_stats.items():
            scores = data["scores"]
            avg = sum(scores) / len(scores) if scores else 0
            analytics.append({"subject": data["subject"], "concept": data["concept"].replace("_", " "), "average_mastery": round(avg, 1), "students_tracked": len(scores), "students_mastered": sum(1 for s in scores if s >= 70), "students_struggling": sum(1 for s in scores if s < 40)})
        analytics.sort(key=lambda x: x["average_mastery"])
        return {"school": school["name"], "class_level": class_level, "subject_filter": subject, "total_students": len(student_ids), "concept_analytics": analytics, "weakest_concepts": analytics[:5], "strongest_concepts": analytics[-5:]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.get("/school/student/{wax_code}")
async def get_student_detail(wax_code: str, school: dict = Depends(verify_school_api_key)):
    try:
        db = get_db_client()
        student_response = db.table("students").select("id, wax_code, inferred_class_level, last_active_at, session_count, primary_exam_target").eq("wax_code", wax_code).execute()
        if not student_response.data: raise HTTPException(status_code=404, detail="Student not found")
        student = student_response.data[0]
        link_check = db.table("school_student_links").select("id").eq("school_id", school["id"]).eq("student_id", student["id"]).execute()
        if not link_check.data: raise HTTPException(status_code=403, detail="Student not enrolled at this school")
        profile = db.table("student_profiles").select("student_name, current_subject, current_topic, study_streak_current, emotional_state_current").eq("student_id", student["id"]).execute()
        knowledge = db.table("knowledge_maps").select("concept_id, subject, mastery_score").eq("student_id", student["id"]).order("mastery_score", desc=False).execute()
        misconceptions = db.table("misconceptions").select("description, subject, status").eq("student_id", student["id"]).in_("status", ["active", "resolving"]).execute()
        return {"student": student, "profile": profile.data[0] if profile.data else {}, "knowledge_map": knowledge.data or [], "active_misconceptions": misconceptions.data or []}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/school/enroll")
async def enroll_student(wax_code: str, class_level: str, school: dict = Depends(verify_school_api_key)):
    try:
        db = get_db_client()
        student_response = db.table("students").select("id").eq("wax_code", wax_code).execute()
        if not student_response.data: raise HTTPException(status_code=404, detail="Student WAX code not found")
        student_id = student_response.data[0]["id"]
        db.table("school_student_links").insert({"school_id": school["id"], "student_id": student_id, "class_level": class_level}).execute()
        db.table("student_subscriptions").insert({"student_id": student_id, "tier_id": "school", "is_active": True}).execute()
        return {"message": f"Student {wax_code} enrolled", "school": school["name"]}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
