from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import pytz

NIGERIA_TZ = pytz.timezone("Africa/Lagos")
WEST_AFRICA_TZ = pytz.timezone("Africa/Abidjan")

def get_nigeria_now() -> datetime:
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(NIGERIA_TZ)

def get_time_context_string() -> str:
    now = get_nigeria_now()
    hour = now.hour
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    if 0 <= hour < 5:
        time_of_day = "very late at night"
        time_note = "It is after midnight in Nigeria right now"
    elif 5 <= hour < 9:
        time_of_day = "early morning"
        time_note = "It is early morning in Nigeria"
    elif 9 <= hour < 12:
        time_of_day = "morning"
        time_note = "It is morning in Nigeria"
    elif 12 <= hour < 14:
        time_of_day = "midday"
        time_note = "It is around midday in Nigeria"
    elif 14 <= hour < 17:
        time_of_day = "afternoon"
        time_note = "It is afternoon in Nigeria"
    elif 17 <= hour < 20:
        time_of_day = "evening"
        time_note = "It is evening in Nigeria"
    elif 20 <= hour < 23:
        time_of_day = "night"
        time_note = "It is night in Nigeria"
    else:
        time_of_day = "late night"
        time_note = "It is late at night in Nigeria"

    context = f"Current Nigerian time: {time_str} WAT on {day_name}, {date_str}. {time_note}."

    if hour >= 23 or hour < 5:
        context += " The student is messaging very late — acknowledge this briefly and naturally, the way a teacher would ('Still up this late?') but do not dwell on it."
    elif hour >= 20:
        context += " The student is messaging in the evening/night."
    elif 5 <= hour < 7:
        context += " The student is messaging very early in the morning."

    if day_name in ["Saturday", "Sunday"]:
        context += " It is the weekend."

    return context

def get_session_gap_context(last_active_at: Optional[str]) -> str:
    if not last_active_at:
        return ""

    try:
        last_active = datetime.fromisoformat(last_active_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        gap = now - last_active.replace(tzinfo=timezone.utc)
        hours = gap.total_seconds() / 3600
        days = gap.days

        if hours < 1:
            return "The student last messaged less than an hour ago — this is a continuation of the same session."
        elif hours < 4:
            return f"The student last messaged about {int(hours)} hours ago."
        elif hours < 24:
            return f"The student last messaged about {int(hours)} hours ago — same day."
        elif days == 1:
            return "The student last messaged yesterday."
        elif days <= 3:
            return f"The student last messaged {days} days ago — a short break."
        elif days <= 7:
            return f"The student has been away for {days} days — about a week."
        elif days <= 30:
            return f"The student has been away for {days} days — more than a week."
        else:
            return f"The student has been away for {days} days — a very long gap."

    except Exception:
        return ""

def format_exam_countdown(exam_date: Optional[str]) -> str:
    if not exam_date:
        return ""

    try:
        exam_dt = datetime.fromisoformat(exam_date)
        now = datetime.now(timezone.utc)
        if exam_dt.tzinfo is None:
            exam_dt = exam_dt.replace(tzinfo=timezone.utc)

        days = (exam_dt - now).days

        if days < 0:
            return ""
        elif days == 0:
            return "EXAM IS TODAY — treat this student with extra care and encouragement."
        elif days == 1:
            return "EXAM IS TOMORROW — focus on confidence and light revision only."
        elif days <= 7:
            return f"Exam is in {days} days — very close. Focus on revision and confidence."
        elif days <= 30:
            return f"Exam is in {days} days — one month window. Prioritize weak areas."
        elif days <= 90:
            return f"Exam is in {days} days — 3 months. Still time for thorough coverage."
        else:
            return f"Exam is in {days} days."

    except Exception:
        return ""
