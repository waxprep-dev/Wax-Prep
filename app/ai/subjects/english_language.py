"""
WaxPrep English Language Intelligence Module
Nigerian curriculum-specific teaching intelligence for English
Exams: WAEC, NECO, JAMB, BECE
"""

from typing import Dict, List

# Common Nigerian English errors and correct forms
NIGERIAN_ENGLISH_ERRORS = {
    "grammar": [
        "'I am coming' used to mean 'I will be back' (Nigerianism - teach when it's appropriate)",
        "'He has gone' instead of 'He has left' (present perfect confusion)",
        "'Off the light' instead of 'Turn off the light' (missing verb)",
        "'I am hearing you' instead of 'I can hear you' (state verb misuse)",
        "'Installmentally' instead of 'By installment' (word formation error)",
        "'Opportuned' instead of 'Has the opportunity' (false cognate)",
        "'I have a running stomach' instead of 'I have diarrhea' (euphemism vs standard)",
        "'You are welldone' instead of 'Thank you' or 'Well done' (context confusion)"
    ],
    "lexis": [
        "'Trafficator' instead of 'Indicator/turn signal' (Nigerian English - note in exams)",
        "'Okada' instead of 'Motorcycle taxi' (local context acceptable in comprehension)",
        "'Danfo' instead of 'Minibus' (local context)",
        "'Chop' instead of 'Eat' (informal only)",
        "'K-leg' instead of 'Complication/problem' (slang)",
        "'Gist' instead of 'Chat/gossip' (informal)",
        "'Sef' as intensifier (informal, avoid in formal writing)"
    ],
    "register_errors": [
        "Using contractions in formal letters (e.g., 'I'm', 'don't')",
        "Using informal closings in formal letters (e.g., 'Yours faithfully' for known addressee)",
        "Mixing formal and informal language in essays",
        "Using SMS language in exam answers (e.g., 'u' for 'you')",
        "Overusing 'Dear Sir/Ma' without proper address block"
    ]
}

# Essay writing guidance
ESSAY_GUIDANCE = {
    "argumentative": {
        "structure": ["Introduction with thesis statement", "Body paragraphs with PEEL (Point, Evidence, Explanation, Link)", "Counter-argument", "Conclusion restating position"],
        "common_topics": [
            "Should education be free in Nigeria?",
            "Is social media beneficial or harmful to Nigerian youth?",
            "Should school uniforms be compulsory?",
            "Is boarding school better than day school?"
        ]
    },
    "formal_letter": {
        "structure": ["Sender's address (top right)", "Date", "Recipient's address", "Salutation (Dear Sir/Madam)", "Title", "Body (3-4 paragraphs)", "Closing (Yours faithfully)", "Signature and name"],
        "common_topics": [
            "Letter to local government chairman about bad roads",
            "Letter to school principal about lack of facilities",
            "Letter to Commissioner of Education about exam malpractice",
            "Letter to newspaper editor about youth unemployment"
        ]
    },
    "informal_letter": {
        "structure": ["Address (optional)", "Date", "Salutation (Dear [name], My dear [name])", "Body (chatty but coherent)", "Closing (Yours lovingly/sincerely/affectionately)", "First name only"],
        "common_topics": [
            "Letter to friend about your SS3 experience",
            "Letter to cousin about your holiday plans",
            "Letter to friend who lost a parent",
            "Letter advising a friend about exam preparation"
        ]
    },
    "narrative_essay": {
        "structure": ["Introduction (setting the scene)", "Build-up of events", "Climax", "Resolution/Conclusion"],
        "tips": ["Use dialogue sparingly but effectively", "Show don't tell", "Use time markers", "Include sensory details"]
    },
    "descriptive_essay": {
        "structure": ["Overall impression", "Spatial organization", "Sensory details", "Figurative language"],
        "tips": ["Use the five senses", "Create a dominant impression", "Use vivid adjectives and adverbs", "Organize spatially"]
    }
}

# Comprehension strategies
COMPREHENSION_STRATEGIES = [
    "Read the questions FIRST before the passage",
    "Skim for main idea, then scan for details",
    "Look for topic sentences in each paragraph",
    "Use context clues for vocabulary questions",
    "For inference questions, read between the lines",
    "Always support answers with evidence from the text",
    "Use your own words for explanation questions",
    "Watch out for distractors in objective questions"
]

# Summary writing rules
SUMMARY_RULES = [
    "Read the passage twice - once for gist, once for details",
    "Identify and list main points (ignore examples and illustrations)",
    "Use your own words - DO NOT copy from passage",
    "Write in complete sentences, not note form",
    "Observe the word limit strictly (usually 80-100 words)",
    "Use connectors to link points smoothly",
    "Do not include your own opinions or examples",
    "Count your words to ensure compliance"
]

# Oral English vowel sounds common errors
VOWEL_COMMON_ERRORS = {
    "/i:/ vs /I/": "'Sheep' vs 'Ship' - Nigerians often don't distinguish these",
    "/u:/ vs /ʊ/": "'Food' vs 'Good' - lip rounding differs",
    "/æ/ vs /e/": "'Mat' vs 'Met' - Nigerians often use /e/ for both",
    "/ɑ:/ vs /ɒ/": "'Cart' vs 'Cot' - British vs American influence",
    "Diphthongs": "Nigerians often turn diphthongs into monophthongs e.g., 'gate' as 'get'"
}

# Socratic questions for English
ENGLISH_SOCRATIC = {
    "essay_writing": [
        "Who is your audience and what tone is appropriate?",
        "What is the strongest argument for the opposing view?",
        "Can you support this point with a Nigerian example?",
        "Why did you choose this organizational structure?"
    ],
    "comprehension": [
        "What is the writer's main purpose?",
        "Is there any bias in this passage?",
        "What can you infer from this paragraph?",
        "How does the writer create a particular effect?"
    ],
    "summary": [
        "Is this point essential or just an example?",
        "Can you say this more concisely?",
        "Have you used your own words?",
        "Does your summary capture the essence without details?"
    ]
}


def get_english_intelligence(topic: str, class_level: str) -> Dict:
    """Returns comprehensive teaching intelligence for English Language."""
    return {
        "subject": "English Language",
        "topic": topic,
        "class_level": class_level,
        "exam_relevance": ["WAEC", "NECO", "JAMB"] if class_level.startswith("SS") else ["BECE"],
        "waec_frequency": _get_english_waec_freq(topic),
        "nigerian_errors": _get_errors_for_topic(topic),
        "essay_guidance": ESSAY_GUIDANCE if "essay" in topic.lower() or "writing" in topic.lower() else {},
        "comprehension_strategies": COMPREHENSION_STRATEGIES if "comprehension" in topic.lower() else [],
        "summary_rules": SUMMARY_RULES if "summary" in topic.lower() else [],
        "socratic_questions": ENGLISH_SOCRATIC.get(topic.lower(), [
            "What is the main idea here?",
            "How does this connect to Nigerian context?",
            "Can you express this in another way?"
        ]),
        "vowel_sounds": VOWEL_COMMON_ERRORS if "oral" in topic.lower() or "vowel" in topic.lower() else {},
        "teaching_notes": _generate_english_notes(topic, class_level)
    }


def _get_english_waec_freq(topic: str) -> str:
    t = topic.lower()
    high = ["essay", "comprehension", "summary", "lexis", "structure", "oral"]
    for h in high:
        if h in t:
            return "high"
    return "medium"


def _get_errors_for_topic(topic: str) -> List[str]:
    t = topic.lower()
    errors = []
    if any(x in t for x in ["grammar", "tense", "structure"]):
        errors.extend(NIGERIAN_ENGLISH_ERRORS["grammar"])
    if any(x in t for x in ["lexis", "vocabulary", "word"]):
        errors.extend(NIGERIAN_ENGLISH_ERRORS["lexis"])
    if any(x in t for x in ["register", "essay", "letter", "writing"]):
        errors.extend(NIGERIAN_ENGLISH_ERRORS["register_errors"])
    return errors


def _generate_english_notes(topic: str, class_level: str) -> str:
    return f"""Teaching English - {topic} at {class_level}:
1. Address Nigerian English interference directly but respectfully
2. Use Nigerian-context passages for comprehension practice
3. Practice formal letter format rigorously (WAEC tests this heavily)
4. Emphasize summary word limits
5. Drill oral English sounds that Nigerians commonly confuse
6. Use past WAEC/NECO questions extensively"""
