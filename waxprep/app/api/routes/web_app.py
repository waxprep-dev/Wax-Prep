from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import hashlib
import secrets
import bcrypt
import os
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.database.client import get_db_client
from waxprep.app.identity.manager import IdentityManager
from waxprep.app.core.constants import Platform
from waxprep.app.gateways.normalizer import NormalizedMessage

router = APIRouter()
identity_manager = IdentityManager()

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str
    phone_number: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    db = get_db_client()
    session = (
        db.table("web_sessions")
        .select("*, web_users(*)")
        .eq("session_token", token)
        .gte("expires_at", datetime.utcnow().isoformat())
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return session.data[0]

@router.post("/web/register")
async def register(req: RegisterRequest):
    db = get_db_client()
    existing = db.table("web_users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    username_check = db.table("web_users").select("id").eq("username", req.username).execute()
    if username_check.data:
        raise HTTPException(status_code=400, detail="Username already taken")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    platform_id = req.phone_number or f"web_{generate_token(8)}"
    platform = Platform.WHATSAPP if req.phone_number else Platform.TELEGRAM
    student = await identity_manager.get_or_create_student(platform=platform, platform_user_id=platform_id)
    password_hash = hash_password(req.password)
    result = db.table("web_users").insert({
        "student_id": student["id"],
        "email": req.email,
        "password_hash": password_hash,
        "username": req.username,
        "verification_token": generate_token(),
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Registration failed")
    return {
        "message": "Registration successful",
        "user_id": result.data[0]["id"],
        "wax_code": student["wax_code"],
    }

@router.post("/web/login")
async def login(req: LoginRequest, request: Request):
    db = get_db_client()
    user = db.table("web_users").select("*").eq("email", req.email).execute()
    if not user.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_record = user.data[0]
    if not verify_password(req.password, user_record["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_token = generate_token(48)
    expires_at = datetime.utcnow() + timedelta(days=30)
    db.table("web_sessions").insert({
        "user_id": user_record["id"],
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:200],
    }).execute()
    db.table("web_users").update({
        "last_login": datetime.utcnow().isoformat()
    }).eq("id", user_record["id"]).execute()
    student = db.table("students").select("*").eq("id", user_record["student_id"]).execute()
    profile = db.table("student_profiles").select("*").eq("student_id", user_record["student_id"]).execute()
    return {
        "token": session_token,
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": user_record["id"],
            "email": user_record["email"],
            "username": user_record["username"],
        },
        "student": student.data[0] if student.data else {},
        "profile": profile.data[0] if profile.data else {},
    }

@router.post("/web/chat")
async def web_chat(req: ChatRequest, session=Depends(get_current_user)):
    try:
        student_id = session["web_users"]["student_id"]
        if not req.message or not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        normalized = NormalizedMessage(
            platform=Platform.TELEGRAM,
            platform_user_id=f"web_{student_id[:8]}",
            platform_message_id=f"web_{generate_token(8)}",
            content=req.message.strip(),
            message_type="text",
            timestamp=datetime.utcnow(),
            raw_payload={},
        )
        from waxprep.app.router.web_dispatcher import dispatch_web_message
        response_text = await dispatch_web_message(
            normalized_message=normalized,
            student_id=student_id,
        )
        return {
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat processing failed")

@router.get("/web/dashboard")
async def get_dashboard(session=Depends(get_current_user)):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    student = db.table("students").select("*").eq("id", student_id).execute()
    profile = db.table("student_profiles").select("*").eq("student_id", student_id).execute()
    knowledge = db.table("knowledge_maps").select("*").eq("student_id", student_id).execute()
    misconceptions = (
        db.table("misconceptions").select("*")
        .eq("student_id", student_id).eq("status", "active").execute()
    )
    achievements = (
        db.table("student_achievements").select("*, achievements(*)")
        .eq("student_id", student_id)
        .order("earned_at", desc=True).limit(10).execute()
    )
    xp = db.table("student_xp").select("*").eq("student_id", student_id).execute()
    recent_sessions = (
        db.table("conversations").select("*")
        .eq("student_id", student_id)
        .order("started_at", desc=True).limit(5).execute()
    )
    learning_events = (
        db.table("learning_events").select("event_type, subject, timestamp, details")
        .eq("student_id", student_id)
        .order("timestamp", desc=True).limit(20).execute()
    )
    return {
        "student": student.data[0] if student.data else {},
        "profile": profile.data[0] if profile.data else {},
        "knowledge_map": knowledge.data or [],
        "active_misconceptions": misconceptions.data or [],
        "recent_achievements": achievements.data or [],
        "xp_status": xp.data[0] if xp.data else {"total_xp": 0, "current_level": 1},
        "recent_sessions": recent_sessions.data or [],
        "recent_events": learning_events.data or [],
    }

@router.get("/web/chat-history")
async def get_chat_history(limit: int = 50, session=Depends(get_current_user)):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    conversations = (
        db.table("conversations").select("id")
        .eq("student_id", student_id)
        .order("started_at", desc=True).limit(1).execute()
    )
    if not conversations.data:
        return {"messages": []}
    messages = (
        db.table("messages")
        .select("direction, content, message_type, timestamp")
        .eq("conversation_id", conversations.data[0]["id"])
        .order("timestamp", desc=False).limit(limit).execute()
    )
    return {
        "messages": messages.data or [],
        "conversation_id": conversations.data[0]["id"],
    }

@router.get("/web/knowledge-map")
async def get_knowledge_map_visual(session=Depends(get_current_user)):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    km = db.table("knowledge_maps").select("*").eq("student_id", student_id).execute()
    subjects = {}
    for concept in (km.data or []):
        subj = concept["subject"]
        if subj not in subjects:
            subjects[subj] = {"subject": subj, "concepts": [], "avg_mastery": 0}
        subjects[subj]["concepts"].append({
            "id": concept["concept_id"],
            "name": concept["concept_id"].replace("_", " ").title(),
            "mastery": concept["mastery_score"],
            "next_review": concept.get("next_review_due_at"),
            "level": (
                "mastered" if concept["mastery_score"] >= 70
                else "partial" if concept["mastery_score"] >= 40
                else "needs_work"
            ),
        })
    for subj in subjects.values():
        concepts = subj["concepts"]
        if concepts:
            subj["avg_mastery"] = sum(c["mastery"] for c in concepts) / len(concepts)
    return {"subjects": list(subjects.values())}

@router.get("/web/study-plan")
async def get_study_plan(session=Depends(get_current_user)):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    student = (
        db.table("students").select("primary_exam_target, exam_date")
        .eq("id", student_id).execute()
    )
    if not student.data or not student.data[0].get("primary_exam_target"):
        return {"plan": None, "message": "No exam target set"}
    artifact = (
        db.table("memory_artifacts").select("content, created_at")
        .eq("student_id", student_id).eq("artifact_type", "study_plan")
        .order("created_at", desc=True).limit(1).execute()
    )
    return {
        "plan": artifact.data[0]["content"] if artifact.data else None,
        "exam_target": student.data[0].get("primary_exam_target"),
        "exam_date": student.data[0].get("exam_date"),
    }

@router.get("/web/profile")
async def get_web_profile(session=Depends(get_current_user)):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    profile = db.table("student_profiles").select("*").eq("student_id", student_id).execute()
    student = db.table("students").select("*").eq("id", student_id).execute()
    return {
        "profile": profile.data[0] if profile.data else {},
        "student": student.data[0] if student.data else {},
        "user": {
            "email": session["web_users"]["email"],
            "username": session["web_users"]["username"],
        },
    }

@router.post("/web/set-exam-target")
async def set_exam_target(
    exam: str,
    exam_date: Optional[str] = None,
    session=Depends(get_current_user),
):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    updates = {"primary_exam_target": exam.upper()}
    if exam_date:
        updates["exam_date"] = exam_date
    db.table("students").update(updates).eq("id", student_id).execute()
    return {"message": "Exam target updated", "exam": exam.upper()}

@router.get("/web/stats")
async def get_student_stats(session=Depends(get_current_user)):
    student_id = session["web_users"]["student_id"]
    db = get_db_client()
    student = db.table("students").select("session_count, total_messages_received, last_active_at").eq("id", student_id).execute()
    km_stats = db.table("knowledge_maps").select("mastery_score").eq("student_id", student_id).execute()
    concepts = km_stats.data or []
    mastered = len([c for c in concepts if c["mastery_score"] >= 70])
    partial = len([c for c in concepts if 40 <= c["mastery_score"] < 70])
    weak = len([c for c in concepts if c["mastery_score"] < 40])
    assessments = db.table("assessment_questions").select("final_score").eq("student_id", student_id).eq("status", "completed").execute()
    avg_score = 0
    if assessments.data:
        scores = [a["final_score"] for a in assessments.data if a.get("final_score")]
        avg_score = sum(scores) / len(scores) * 100 if scores else 0
    return {
        "sessions": student.data[0]["session_count"] if student.data else 0,
        "total_messages": student.data[0]["total_messages_received"] if student.data else 0,
        "concepts_total": len(concepts),
        "concepts_mastered": mastered,
        "concepts_partial": partial,
        "concepts_weak": weak,
        "avg_assessment_score": round(avg_score, 1),
        "assessments_completed": len(assessments.data) if assessments.data else 0,
    }

@router.post("/web/voice-transcribe")
async def transcribe_voice(request: Request, session=Depends(get_current_user)):
    try:
        body = await request.body()
        if len(body) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio too large (max 10MB)")
        import tempfile
        import os
        from groq import Groq
        from waxprep.app.core.config import settings
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(body)
            tmp_path = tmp.name
        try:
            client = Groq(api_key=settings.groq_api_key)
            with open(tmp_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=("audio.webm", f, "audio/webm"),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                    language="en",
                )
            return {"transcript": result.strip() if result else ""}
        finally:
            os.unlink(tmp_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")

@router.post("/web/logout")
async def logout(session=Depends(get_current_user)):
    db = get_db_client()
    db.table("web_sessions").update({
        "expires_at": datetime.utcnow().isoformat()
    }).eq("user_id", session["web_users"]["id"]).execute()
    return {"message": "Logged out successfully"}

@router.get("/web")
async def serve_web_app_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/web/index.html")
