from enum import Enum


class Platform(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


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


class SessionState(str, Enum):
    ONBOARDING = "onboarding"
    TEACHING = "teaching"
    ASSESSMENT = "assessment"
    REVISION = "revision"
    FREE_EXPLORATION = "free_exploration"
    EMOTIONAL_SUPPORT = "emotional_support"
    EXAM_PREP = "exam_prep"
    IDLE = "idle"


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
    COMMAND = "command"


class Intent(str, Enum):
    TEACHING_REQUEST = "teaching_request"
    NEW_TOPIC_REQUEST = "new_topic_request"
    CLARIFICATION_REQUEST = "clarification_request"
    EXAMPLE_REQUEST = "example_request"
    ASSESSMENT_RESPONSE = "assessment_response"
    CORRECT_ANSWER = "correct_answer"
    INCORRECT_ANSWER = "incorrect_answer"
    I_DONT_KNOW = "i_dont_know"
    PROGRESS_CHECK = "progress_check"
    EMOTIONAL_EXPRESSION = "emotional_expression"
    CASUAL_CONVERSATION = "casual_conversation"
    PLATFORM_COMMAND = "platform_command"
    META_QUESTION = "meta_question"
    GREETING = "greeting"
    CONFUSION = "confusion"
    TOPIC_CHANGE = "topic_change"
    UNKNOWN = "unknown"


class TeachingStrategy(str, Enum):
    SOCRATIC = "socratic"
    DIRECT_INSTRUCTION = "direct_instruction"
    ANALOGICAL = "analogical"
    WORKED_EXAMPLE = "worked_example"
    RETRIEVAL_PRACTICE = "retrieval_practice"
    ERROR_ANALYSIS = "error_analysis"
    ELABORATIVE_INTERROGATION = "elaborative_interrogation"
    EMOTIONAL_SUPPORT = "emotional_support"


class Subject(str, Enum):
    MATHEMATICS = "mathematics"
    ENGLISH = "english"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ECONOMICS = "economics"
    GOVERNMENT = "government"
    LITERATURE = "literature"
    GEOGRAPHY = "geography"
    FURTHER_MATHEMATICS = "further_mathematics"
    ACCOUNTING = "accounting"
    COMMERCE = "commerce"
    CRS = "crs"
    IRS = "irs"
    BASIC_SCIENCE = "basic_science"
    SOCIAL_STUDIES = "social_studies"
    DATA_PROCESSING = "data_processing"
    YORUBA = "yoruba"
    IGBO = "igbo"
    HAUSA = "hausa"


WAX_CODE_PREFIX = "WAX"
WAX_CODE_WHATSAPP_SUFFIX = "W"
WAX_CODE_TELEGRAM_SUFFIX = "T"

DEFAULT_REGION_CODE = "NG"

MAX_MESSAGE_LENGTH_WHATSAPP = 4096
MAX_MESSAGE_LENGTH_TELEGRAM = 4096
PREFERRED_MESSAGE_LENGTH = 800

ONBOARDING_COMPLETE_THRESHOLD = 3

FORGETTING_CURVE_INITIAL_INTERVAL_DAYS = 1
FORGETTING_CURVE_EASE_FACTOR_DEFAULT = 2.5
FORGETTING_CURVE_EASE_FACTOR_MIN = 1.3

KNOWLEDGE_MASTERY_THRESHOLD_DEEP = 90
KNOWLEDGE_MASTERY_THRESHOLD_FUNCTIONAL = 70
KNOWLEDGE_MASTERY_THRESHOLD_PARTIAL = 40

MEMORY_COLD_STORAGE_THRESHOLD = 0.25
MEMORY_CLEANUP_RUN_HOUR = 3
