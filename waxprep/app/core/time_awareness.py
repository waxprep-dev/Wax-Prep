from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz

NIGERIA_TZ = pytz.timezone("Africa/Lagos")

def get_nigeria_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(NIGERIA_TZ)

def get_time_context_string() -> str:
    now = get_nigeria_now()
    hour = now.hour
    day_name = now.strftime("%A")
    time_str = now.strftime("%I:%M %p")
    if 0 <= hour < 5: period = "very late at night"
    elif 5 <= hour < 9: period = "early morning"
    elif 9 <= hour < 12: period = "morning"
    elif 12 <= hour < 14: period = "midday"
    elif 14 <= hour < 17: period = "afternoon"
    elif 17 <= hour < 20: period = "evening"
    elif 20 <= hour < 23: period = "night"
    else: period = "late night"
    return f"Nigerian time: {time_str} WAT on {day_name} ({period})."

def get_session_gap_context(last_active_at: Optional[str]) -> str:
    if not last_active_at: return ""
    try:
        last = datetime.fromisoformat(last_active_at.replace("Z", "+00:00"))
        gap_hours = (datetime.now(timezone.utc) - last.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if gap_hours < 1: return "Continuing same session."
        elif gap_hours < 24: return f"Student last messaged {int(gap_hours)} hours ago."
        elif gap_hours < 48: return "Student was away for about a day."
        elif gap_hours < 168: return f"Student has been away for {int(gap_hours/24)} days."
        else: return f"Student has been away for {int(gap_hours/24)} days."
    except: return ""

def format_exam_countdown(exam_date: Optional[str]) -> str:
    if not exam_date: return ""
    try:
        exam_dt = datetime.fromisoformat(str(exam_date))
        if exam_dt.tzinfo is None: exam_dt = exam_dt.replace(tzinfo=timezone.utc)
        days = (exam_dt - datetime.now(timezone.utc)).days
        if days < 0: return ""
        elif days == 0: return "EXAM IS TODAY."
        elif days == 1: return "EXAM TOMORROW."
        elif days <= 7: return f"Exam in {days} days."
        elif days <= 30: return f"Exam in {days} days."
        return ""
    except: return ""
