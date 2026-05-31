from enum import Enum

class Platform(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB = "web"

class ClassLevel(str, Enum):
    JSS1 = "JSS1"
    JSS2 = "JSS2"
    JSS3 = "JSS3"
    SS1 = "SS1"
    SS2 = "SS2"
    SS3 = "SS3"
    UNI_100 = "UNI_100"
    UNI_200 = "UNI_200"
    UNI_300 = "UNI_300"
    UNI_400 = "UNI_400"
    OUT_OF_SCHOOL = "OUT_OF_SCHOOL"
    UNKNOWN = "UNKNOWN"

class ExamTarget(str, Enum):
    WAEC = "WAEC"
    NECO = "NECO"
    JAMB = "JAMB"
    POST_UTME = "POST_UTME"
    BECE = "BECE"
    NONE = "NONE"

class StudentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"
    INACTIVE = "inactive"

class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class MessageType(str, Enum):
    TEXT = "text"
    ASSESSMENT_QUESTION = "assessment_question"
    ASSESSMENT_RESPONSE = "assessment_response"
    TEACHING = "teaching"
    ONBOARDING = "onboarding"
    EMOTIONAL_SUPPORT = "emotional_support"
    NOTIFICATION = "notification"
    SYSTEM = "system"

class Intent(str, Enum):
    TEACHING_REQUEST = "teaching_request"
    CLARIFICATION_REQUEST = "clarification_request"
    EXAMPLE_REQUEST = "example_request"
    ASSESSMENT_RESPONSE = "assessment_response"
    PROGRESS_CHECK = "progress_check"
    EMOTIONAL_EXPRESSION = "emotional_expression"
    CASUAL_CONVERSATION = "casual_conversation"
    TOPIC_CHANGE = "topic_change"
    CONFUSION = "confusion"
    GREETING = "greeting"
    META_QUESTION = "meta_question"
    PLATFORM_COMMAND = "platform_command"
    UNKNOWN = "unknown"

WAX_CODE_PREFIX = "WAX"
DEFAULT_REGION_CODE = "NG"
