from typing import Dict, Any, Optional, List
from loguru import logger
from waxprep.app.curriculum.navigator import CurriculumNavigator
from waxprep.app.ai.subjects.mathematics import get_subject_intelligence as get_math_intelligence

navigator = CurriculumNavigator()

async def get_teaching_intelligence(
    subject: str,
    topic: str,
    class_level: str,
    misconceptions: List[str] = None,
) -> str:
    try:
        subject_lower = subject.lower() if subject else ""
        topic_lower = topic.lower() if topic else ""
        intelligence_parts = []

        if subject_lower == "mathematics" or subject_lower == "maths":
            math_intel = get_math_intelligence(subject_lower, topic_lower, class_level)
            if math_intel:
                intelligence_parts.append(math_intel)

        curriculum = navigator.load_curriculum(subject_lower, class_level)
        if curriculum:
            waec_topics = curriculum.get("waec_high_priority_topics", [])
            if waec_topics:
                intelligence_parts.append(f"WAEC high priority topics in this subject: {', '.join(waec_topics[:5])}")

            for t in curriculum.get("topics", []):
                for st in t.get("subtopics", []):
                    if topic_lower in st.get("title", "").lower():
                        topic_misconceptions = st.get("common_misconceptions", [])
                        if topic_misconceptions:
                            intelligence_parts.append(
                                f"Common misconceptions to watch for in this topic:\n" +
                                "\n".join([f"- {m}" for m in topic_misconceptions[:3]])
                            )
                        teaching_note = st.get("teaching_note", "")
                        if teaching_note:
                            intelligence_parts.append(f"Teaching note: {teaching_note}")
                        break

        if misconceptions:
            active = [m for m in misconceptions if "active" in str(m).lower()]
            if active:
                intelligence_parts.append(
                    "This student has active misconceptions that need correction: " +
                    ", ".join(active[:3])
                )

        return "\n\n".join(intelligence_parts) if intelligence_parts else ""

    except Exception as e:
        logger.warning(f"Subject intelligence router failed: {e}")
        return ""

async def should_suggest_assessment(
    subject: str,
    topic: str,
    message_count_since_last_assessment: int,
) -> bool:
    if message_count_since_last_assessment < 8:
        return False

    assessment_subjects = ["mathematics", "maths", "physics", "chemistry", "biology", "economics"]
    if subject and subject.lower() in assessment_subjects:
        return True

    return False

async def get_worked_problem_topics(subject: str, class_level: str) -> List[str]:
    worked_problem_subjects = {
        "mathematics": [
            "quadratic equations",
            "simultaneous equations",
            "circle theorems",
            "trigonometry",
            "logarithms",
            "matrices",
            "differentiation",
        ],
        "physics": [
            "equations of motion",
            "newton's second law calculations",
            "work energy power",
            "electric circuits",
        ],
        "chemistry": [
            "balancing equations",
            "mole calculations",
            "stoichiometry",
        ],
    }
    return worked_problem_subjects.get(subject.lower() if subject else "", [])

async def get_neco_supplement(subject: str, topic: str) -> str:
    neco_notes = {
        "circle_theorems": "For NECO, circle theorem questions are usually more direct than WAEC. NECO typically tests one theorem per question rather than combining multiple theorems.",
        "quadratic_equations": "NECO usually asks for the quadratic formula method specifically. Mention the formula by name.",
        "statistics": "NECO statistics questions tend to give you the data in table format already organized. WAEC sometimes requires you to organize the data yourself first.",
        "genetics": "NECO genetics questions are more likely to ask you to draw the Punnett square explicitly rather than just stating the ratio.",
        "photosynthesis": "NECO frequently asks to 'state the conditions necessary for photosynthesis' as a separate question from 'write the equation'.",
    }
    topic_lower = topic.lower().replace("_", " ") if topic else ""
    for topic_key, note in neco_notes.items():
        if topic_key.replace("_", " ") in topic_lower:
            return f"NECO-specific note: {note}"
    return ""
