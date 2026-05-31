import re
from typing import Tuple, Optional
from loguru import logger

BLOCKED_PATTERNS = [
    r'\b(sex|sexual|naked|nude|porn|pornography)\b',
    r'\b(drug|cocaine|heroin|marijuana|weed|substance abuse)\b',
    r'\b(kill yourself|suicide|self.?harm|cutting)\b',
    r'\b(terrorist|bomb|weapon|violence|attack|kill)\b',
]

SENSITIVE_PATTERNS = [
    r'\b(i want to die|i hate my life|nobody cares about me)\b',
    r'\b(depressed|depression|anxiety|mental health)\b',
    r'\b(abuse|abused|hurt me|hitting me)\b',
]

EDUCATIONAL_EXCEPTIONS = [
    "nuclear bomb physics",
    "explosive chemistry waec",
    "violence in literature",
    "suicide in things fall apart",
    "mental health awareness",
    "drug abuse awareness",
]

MENTAL_HEALTH_RESPONSE = """I can hear that things are really difficult right now. WaxPrep is here for learning, but what you're describing sounds more important than any subject.

Please talk to someone who can actually help:
- Suicide Helpline Nigeria: 0800 100 0000 (free, 24/7)
- You can also talk to a trusted adult — a parent, teacher, or relative.

When you're ready to study, I'm here. But right now, please reach out to someone who can support you properly."""

class ContentSafetyFilter:
    def __init__(self):
        self.blocked = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]
        self.sensitive = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]
    
    def check_message(self, message: str) -> Tuple[bool, Optional[str], str]:
        message_lower = message.lower()
        is_educational_context = any(exc in message_lower for exc in EDUCATIONAL_EXCEPTIONS)
        
        if not is_educational_context:
            for pattern in self.blocked:
                if pattern.search(message):
                    return False, "blocked_content", "I can't help with that topic, but I'm here to help you with your studies. What subject do you want to work on?"
        
        for pattern in self.sensitive:
            if pattern.search(message):
                return True, "sensitive_distress", MENTAL_HEALTH_RESPONSE
        
        return True, None, ""
    
    def filter_response(self, response: str) -> str:
        for pattern in self.blocked:
            if pattern.search(response):
                logger.warning("Blocked content in AI response — filtered")
                return "I want to make sure I give you accurate information. Let me rephrase that for you."
        return response
