import re
from typing import Optional, Tuple, List
from loguru import logger
from waxprep.app.core.config import settings

SUBJECT_KEYWORDS = {
    "mathematics": [
        "mathematics", "maths", "math", "algebra", "geometry", "trigonometry",
        "quadratic", "equation", "circle theorem", "cycle theorem", "logarithm",
        "indices", "simultaneous", "statistics", "probability", "calculus",
        "differentiation", "integration", "matrix", "matrices", "vector",
        "sequence", "series", "permutation", "combination", "binomial",
        "fraction", "decimal", "number base", "binary", "bodmas",
        "factorize", "factorise", "expand", "simplify maths",
        "graph", "coordinate", "gradient", "locus"
    ],
    "physics": [
        "physics", "force", "motion", "velocity", "acceleration", "newton",
        "energy", "work", "power", "momentum", "waves", "light", "optics",
        "electricity", "circuit", "voltage", "current", "resistance",
        "magnetic", "nuclear", "radioactive", "heat", "temperature",
        "pressure", "density", "projectile", "friction", "inertia"
    ],
    "chemistry": [
        "chemistry", "atom", "molecule", "element", "compound", "bond",
        "ionic", "covalent", "periodic table", "acid", "base", "salt",
        "reaction", "equation chemistry", "mole", "titration", "electrolysis",
        "organic", "alkane", "alkene", "functional group", "polymer",
        "oxidation", "reduction", "catalyst", "isotope"
    ],
    "biology": [
        "biology", "cell", "tissue", "organ", "photosynthesis", "respiration",
        "skeleton", "joint", "muscle", "blood", "heart", "kidney",
        "reproduction", "genetics", "ecology", "evolution", "taxonomy",
        "nutrition", "excretion", "hormone", "nerve", "brain", "virus",
        "bacteria", "fungi", "plant", "animal", "ecosystem", "food chain"
    ],
    "english": [
        "english", "grammar", "comprehension", "essay", "vocabulary",
        "spelling", "punctuation", "tense", "verb", "noun", "pronoun",
        "adjective", "adverb", "sentence", "paragraph", "composition",
        "summary", "literature", "poem", "poetry", "prose", "novel",
        "report writing", "letter writing", "speech", "oral english",
        "phonetics", "stress", "intonation", "rhyme"
    ],
    "economics": [
        "economics", "demand", "supply", "market", "price", "inflation",
        "gdp", "national income", "trade", "banking", "money", "fiscal",
        "monetary", "production", "cost", "revenue", "profit",
        "opportunity cost", "scarcity", "elasticity", "consumer",
        "producer", "government spending", "tax", "subsidy"
    ],
    "government": [
        "government", "politics", "constitution", "democracy", "election",
        "parliament", "legislature", "executive", "judiciary", "federalism",
        "citizenship", "human rights", "political party", "sovereignty",
        "arms of government", "cabinet", "senate", "house of representatives",
        "inec", "local government", "geopolitical", "colonialism",
        "nationalism", "military rule", "coup"
    ],
    "literature": [
        "literature", "things fall apart", "achebe", "soyinka",
        "the lion and the jewel", "adichie", "purple hibiscus",
        "weep not child", "ngugi", "novel", "drama", "play",
        "characterization", "theme", "setting", "plot", "conflict",
        "protagonist", "antagonist", "metaphor", "simile", "symbolism"
    ],
    "further_mathematics": [
        "further maths", "further mathematics", "partial fraction",
        "complex number", "polynomial", "vectors 3d", "mechanics",
        "calculus further", "differential equation", "maclaurin"
    ],
}

TOPIC_KEYWORDS = {
    "circle_theorems": [
        "circle theorem", "cycle theorem", "cyclic", "inscribed angle",
        "tangent circle", "chord", "arc", "sector", "segment circle",
        "alternate segment", "angle subtended", "cyclic quadrilateral"
    ],
    "quadratic_equations": [
        "quadratic", "completing the square", "quadratic formula",
        "roots of equation", "discriminant", "factorize quadratic"
    ],
    "logarithms": [
        "logarithm", "log", "antilog", "log table", "natural log", "ln"
    ],
    "simultaneous_equations": [
        "simultaneous", "two equations", "two unknowns", "elimination method",
        "substitution method"
    ],
    "differentiation": [
        "differentiate", "differentiation", "dy/dx", "gradient function",
        "turning point", "maximum minimum calculus"
    ],
    "integration": [
        "integrate", "integration", "area under curve", "definite integral",
        "indefinite integral"
    ],
    "matrices": [
        "matrix", "matrices", "determinant", "inverse matrix",
        "2x2 matrix", "singular matrix"
    ],
    "trigonometry": [
        "sohcahtoa", "sine rule", "cosine rule", "trigonometry",
        "angle of elevation", "angle of depression", "bearing"
    ],
    "statistics": [
        "mean", "median", "mode", "standard deviation", "variance",
        "frequency table", "histogram", "cumulative frequency",
        "ogive", "quartile", "percentile"
    ],
    "number_bases": [
        "binary", "base 2", "base 8", "octal", "number base",
        "convert to binary", "hexadecimal"
    ],
    "ionic_bonding": [
        "ionic bond", "ionic bonding", "ionic compound", "transfer electron"
    ],
    "covalent_bonding": [
        "covalent bond", "covalent bonding", "sharing electron", "dative bond"
    ],
    "photosynthesis": [
        "photosynthesis", "light reaction", "dark reaction", "calvin cycle",
        "chloroplast", "chlorophyll"
    ],
    "joints": [
        "joint", "ball and socket", "hinge joint", "synovial", "cartilage",
        "tendon", "ligament"
    ],
    "equations_of_motion": [
        "suvat", "equations of motion", "uniform acceleration",
        "v equals u plus at", "s equals ut"
    ],
    "forces": [
        "newton's law", "newton law", "F equals ma", "friction force",
        "resultant force", "equilibrium"
    ],
}

TOPIC_TO_SUBJECT = {
    "circle_theorems": "mathematics",
    "quadratic_equations": "mathematics",
    "logarithms": "mathematics",
    "simultaneous_equations": "mathematics",
    "differentiation": "mathematics",
    "integration": "mathematics",
    "matrices": "mathematics",
    "trigonometry": "mathematics",
    "statistics": "mathematics",
    "number_bases": "mathematics",
    "ionic_bonding": "chemistry",
    "covalent_bonding": "chemistry",
    "photosynthesis": "biology",
    "joints": "biology",
    "equations_of_motion": "physics",
    "forces": "physics",
    "voice_on": [
        "send me voice", "voice note please", "i prefer voice",
        "respond with voice", "voice response", "talk to me",
        "send audio", "i like voice",
    ],
    "voice_off": [
        "text only", "no voice", "stop sending voice", "just text",
        "text please", "no audio",
    ],
}

def detect_subject_from_message(message: str) -> Optional[str]:
    message_lower = message.lower()
    for subject, keywords in SUBJECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return subject
    return None

def detect_topic_from_message(message: str) -> Optional[str]:
    message_lower = message.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return topic.replace("_", " ")
    return None

def detect_subject_and_topic(message: str) -> Tuple[Optional[str], Optional[str]]:
    subject = detect_subject_from_message(message)
    topic = detect_topic_from_message(message)

    if topic and not subject:
        topic_key = topic.replace(" ", "_")
        if topic_key in TOPIC_TO_SUBJECT:
            subject = TOPIC_TO_SUBJECT[topic_key]

    return subject, topic

def is_topic_switch_intent(message: str) -> bool:
    message_lower = message.lower()
    switch_phrases = [
        "teach me", "let's do", "let me learn", "i want to learn",
        "can we do", "can we learn", "start with", "begin with",
        "move to", "switch to", "let's switch", "let's move to",
        "explain", "let's try", "show me how", "help me with",
        "i want to understand", "i need help with",
        "what about", "how about", "can you explain",
    ]
    return any(phrase in message_lower for phrase in switch_phrases)

VOICE_ON_PHRASES = [
    "send me voice", "voice note please", "i prefer voice",
    "respond with voice", "voice response", "talk to me",
    "send audio", "i like voice",
]

VOICE_OFF_PHRASES = [
    "text only", "no voice", "stop sending voice", "just text",
    "text please", "no audio",
]

def detect_voice_preference(message: str) -> Optional[bool]:
    message_lower = message.lower()
    if any(p in message_lower for p in VOICE_ON_PHRASES):
        return True
    if any(p in message_lower for p in VOICE_OFF_PHRASES):
        return False
    return None
