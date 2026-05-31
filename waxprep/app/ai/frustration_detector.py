from typing import Dict, Any, List, Tuple
from datetime import datetime
from loguru import logger
from waxprep.app.database.client import get_db_client

FRUSTRATION_SIGNALS = [
    "bro", "please", "i don't get it", "i don't understand",
    "this is hard", "i'm confused", "confusing", "not understanding",
    "too much", "tired", "bye", "later", "i give up", "forget it",
    "whatever", "okay bye", "its too hard", "nope", "no i don't",
    "i dont know", "negative", "zero confidence", "0/10",
    "hopeless", "useless", "what is this", "huh", "???"
]

ESCALATION_LEVELS = {
    0: "normal",
    1: "mild_frustration",
    2: "moderate_frustration",
    3: "high_frustration",
    4: "about_to_leave",
}

STRATEGY_FOR_LEVEL = {
    0: "normal",
    1: "simplify_and_encourage",
    2: "change_approach_completely",
    3: "offer_break_or_switch",
    4: "acknowledge_and_offer_exit",
}

class FrustrationDetector:
    def __init__(self):
        self.db = get_db_client()
        self._frustration_cache: Dict[str, Dict] = {}

    def analyze_message(self, student_id: str, message: str, intent: str) -> Dict[str, Any]:
        message_lower = message.lower().strip()

        current = self._frustration_cache.get(student_id, {
            "level": 0,
            "consecutive_confusion": 0,
            "consecutive_frustration": 0,
            "last_message": "",
            "escalation_history": [],
            "messages_since_success": 0,
        })

        signals_found = []
        for signal in FRUSTRATION_SIGNALS:
            if signal in message_lower:
                signals_found.append(signal)

        is_very_short = len(message.strip()) <= 5 and not message.strip().isdigit()
        is_question_mark_only = message.strip() in ["?", "??", "???", "huh?"]
        is_goodbye = any(w in message_lower for w in ["bye", "later", "i'm done", "forget it", "okay bye"])
        is_confusion_intent = intent in ["confusion", "CONFUSION"]
        is_emotional = intent in ["emotional_expression", "EMOTIONAL_EXPRESSION"]

        frustration_score = 0
        if signals_found:
            frustration_score += len(signals_found) * 2
        if is_very_short:
            frustration_score += 1
        if is_question_mark_only:
            frustration_score += 3
        if is_goodbye:
            frustration_score += 5
        if is_confusion_intent:
            frustration_score += 2
            current["consecutive_confusion"] += 1
        else:
            current["consecutive_confusion"] = max(0, current["consecutive_confusion"] - 1)

        if is_emotional:
            current["consecutive_frustration"] += 1
        else:
            current["consecutive_frustration"] = max(0, current["consecutive_frustration"] - 1)

        if frustration_score >= 5:
            current["level"] = min(4, current["level"] + 2)
        elif frustration_score >= 3:
            current["level"] = min(4, current["level"] + 1)
        elif frustration_score == 0 and intent not in ["confusion", "CONFUSION", "emotional_expression", "EMOTIONAL_EXPRESSION"]:
            current["level"] = max(0, current["level"] - 1)

        if current["consecutive_confusion"] >= 2:
            current["level"] = max(current["level"], 2)
        if current["consecutive_confusion"] >= 3:
            current["level"] = max(current["level"], 3)
        if is_goodbye:
            current["level"] = 4

        strategy = STRATEGY_FOR_LEVEL[current["level"]]

        if current["level"] >= 1:
            current["escalation_history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "level": current["level"],
                "trigger": message[:100],
            })
            current["escalation_history"] = current["escalation_history"][-10:]

        current["last_message"] = message
        self._frustration_cache[student_id] = current

        return {
            "frustration_level": current["level"],
            "level_name": ESCALATION_LEVELS[current["level"]],
            "strategy": strategy,
            "consecutive_confusion": current["consecutive_confusion"],
            "is_about_to_leave": is_goodbye,
            "signals": signals_found,
            "should_change_approach": current["level"] >= 2,
            "should_offer_break": current["level"] >= 3,
        }

    def record_success(self, student_id: str) -> None:
        current = self._frustration_cache.get(student_id, {"level": 0, "consecutive_confusion": 0, "consecutive_frustration": 0})
        current["level"] = max(0, current["level"] - 1)
        current["consecutive_confusion"] = 0
        current["consecutive_frustration"] = 0
        self._frustration_cache[student_id] = current

    def get_strategy_instruction(self, frustration_analysis: Dict[str, Any], current_topic: str) -> str:
        level = frustration_analysis.get("frustration_level", 0)
        strategy = frustration_analysis.get("strategy", "normal")

        if strategy == "normal":
            return ""

        elif strategy == "simplify_and_encourage":
            return (
                "FRUSTRATION LEVEL 1 — MILD: The student is showing early signs of difficulty. "
                "Drop to the most fundamental level of explanation. "
                "Use a very simple analogy from everyday Nigerian life. "
                "Make them feel the small win immediately — ask something you know they can answer."
            )

        elif strategy == "change_approach_completely":
            return (
                f"FRUSTRATION LEVEL 2 — MODERATE: This student has struggled with this topic {frustration_analysis.get('consecutive_confusion', 2)} times. "
                "Do NOT continue with the same explanation. "
                "Change approach completely — use a different method, a completely different analogy, or a concrete physical example. "
                "Explicitly acknowledge: 'Let me try explaining this differently...' or 'I think I was making this too complicated.'"
            )

        elif strategy == "offer_break_or_switch":
            return (
                f"FRUSTRATION LEVEL 3 — HIGH: This student is genuinely frustrated with {current_topic}. "
                "Acknowledge their frustration directly but briefly. "
                "Offer two options: a completely different approach to the same topic, OR switching to a different topic entirely. "
                "Do not push them further on the same approach. "
                "Something like: 'I can see this isn't clicking the way I'm explaining it. Two options — I try a completely different way, or we step away from this for now and come back to it.'"
            )

        elif strategy == "offer_exit":
            return (
                "FRUSTRATION LEVEL 4 — CRITICAL: This student is about to leave. "
                "Do not continue teaching. "
                "Acknowledge their experience genuinely and briefly. "
                "Give them permission to leave and make it easy to come back. "
                "Something like: 'That's fair — this was a tough session. When you come back we'll try a completely different starting point for this.' "
                "Do not guilt them. Do not beg them to stay."
            )

        return ""

    def reset_frustration(self, student_id: str) -> None:
        if student_id in self._frustration_cache:
            del self._frustration_cache[student_id]
