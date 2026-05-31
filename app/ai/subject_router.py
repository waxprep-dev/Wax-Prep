"""
WaxPrep Subject Router
Routes teaching requests to the appropriate subject intelligence module.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from subjects.mathematics import get_mathematics_intelligence
from subjects.physics import get_physics_intelligence
from subjects.chemistry import get_chemistry_intelligence
from subjects.english_language import get_english_intelligence
from subjects.biology import get_biology_intelligence

# Subject routing map - maps subject names to their intelligence functions
SUBJECT_ROUTER = {
    # Mathematics variants
    "mathematics": get_mathematics_intelligence,
    "maths": get_mathematics_intelligence,
    "math": get_mathematics_intelligence,
    "further_mathematics": get_mathematics_intelligence,
    "further_maths": get_mathematics_intelligence,
    "general_mathematics": get_mathematics_intelligence,
    
    # Physics variants
    "physics": get_physics_intelligence,
    
    # Chemistry variants
    "chemistry": get_chemistry_intelligence,
    
    # English variants
    "english": get_english_intelligence,
    "english_language": get_english_intelligence,
    "english_studies": get_english_intelligence,
    "literature": get_english_intelligence,
    "literature_in_english": get_english_intelligence,
    
    # Biology variants
    "biology": get_biology_intelligence,
    "basic_science": get_biology_intelligence,  # JSS basic science covers biology concepts
    
    # Additional subjects can be added here as modules are created
    # "government": get_government_intelligence,
    # "economics": get_economics_intelligence,
    # "commerce": get_commerce_intelligence,
    # "accounting": get_accounting_intelligence,
    # "geography": get_geography_intelligence,
    # "agricultural_science": get_agricultural_intelligence,
    # "civic_education": get_civic_intelligence,
    # "christian_religious_studies": get_crs_intelligence,
    # "history": get_history_intelligence,
    # "computer_studies": get_computer_intelligence,
}

# Subject categories for grouping
SCIENCE_SUBJECTS = ["mathematics", "physics", "chemistry", "biology", "further_mathematics"]
ARTS_SUBJECTS = ["english", "literature", "history", "christian_religious_studies"]
COMMERCIAL_SUBJECTS = ["economics", "commerce", "accounting"]
SOCIAL_SCIENCE_SUBJECTS = ["government", "geography", "civic_education"]
TECHNICAL_SUBJECTS = ["computer_studies", "agricultural_science"]


def get_teaching_intelligence(subject: str, topic: str, class_level: str) -> dict:
    """
    Main routing function to get teaching intelligence for any subject.
    
    Args:
        subject: Subject name (e.g., 'mathematics', 'physics', 'english')
        topic: Specific topic within the subject
        class_level: Student's class level (JSS1-3, SS1-3)
    
    Returns:
        Dictionary containing teaching intelligence for the subject/topic
    
    Raises:
        ValueError: If subject is not recognized
    """
    # Normalize subject name
    subject_key = subject.lower().strip().replace(" ", "_")
    
    # Route to appropriate handler
    if subject_key in SUBJECT_ROUTER:
        return SUBJECT_ROUTER[subject_key](topic, class_level)
    
    # Try common aliases
    alias_map = {
        "bio": "biology",
        "chem": "chemistry",
        "phys": "physics",
        "eng": "english",
        "lit": "english",
        "math": "mathematics",
        "further_math": "further_mathematics",
        "fm": "further_mathematics",
        "crs": "christian_religious_studies",
        "crk": "christian_religious_studies",
        "civic": "civic_education",
        "govt": "government",
        "econs": "economics",
        "acct": "accounting",
        "geo": "geography",
        "agric": "agricultural_science",
        "comp": "computer_studies",
        "basic_tech": "basic_technology",
        "pvs": "prevocational_studies",
        "cca": "cultural_creative_arts",
        "phe": "physical_health_education",
        "bst": "basic_science_technology",
        "irs": "islamic_religious_studies",
        "arabic": "arabic_language",
        "french": "french_language",
        "hausa": "hausa_language",
        "igbo": "igbo_language",
        "yoruba": "yoruba_language",
        "marketing": "marketing",
        "insurance": "insurance",
        "food_nutrition": "food_and_nutrition",
        "clothing_textile": "clothing_and_textiles",
        "home_management": "home_management",
        "technical_drawing": "technical_drawing",
    }
    
    if subject_key in alias_map:
        mapped_key = alias_map[subject_key]
        if mapped_key in SUBJECT_ROUTER:
            return SUBJECT_ROUTER[mapped_key](topic, class_level)
    
    # Return helpful error with available subjects
    available = sorted(set(SUBJECT_ROUTER.keys()))
    raise ValueError(
        f"Subject '{subject}' not recognized. Available subjects: {', '.join(available)}. "
        f"Please use one of the supported subject names."
    )


def list_available_subjects() -> list:
    """Returns list of all available subjects."""
    return sorted(set(SUBJECT_ROUTER.keys()))


def get_subjects_by_category(category: str) -> list:
    """
    Get subjects by category.
    
    Args:
        category: One of 'science', 'arts', 'commercial', 'social_science', 'technical'
    """
    categories = {
        "science": SCIENCE_SUBJECTS,
        "arts": ARTS_SUBJECTS,
        "commercial": COMMERCIAL_SUBJECTS,
        "social_science": SOCIAL_SCIENCE_SUBJECTS,
        "technical": TECHNICAL_SUBJECTS,
    }
    return categories.get(category.lower(), [])


def is_subject_available(subject: str) -> bool:
    """Check if a subject has an intelligence module."""
    return subject.lower().strip().replace(" ", "_") in SUBJECT_ROUTER


# Quick test function
def test_router():
    """Test the subject router with sample topics."""
    test_cases = [
        ("mathematics", "quadratic_equations", "SS2"),
        ("physics", "electric_circuits", "SS3"),
        ("chemistry", "organic_chemistry", "SS2"),
        ("english", "essay_writing", "SS3"),
        ("biology", "photosynthesis", "SS1"),
    ]
    
    for subject, topic, level in test_cases:
        try:
            result = get_teaching_intelligence(subject, topic, level)
            print(f"SUCCESS: {subject} - {topic} ({level})")
            print(f"  Misconceptions: {len(result.get('misconceptions', []))} items")
            print(f"  Socratic questions: {len(result.get('socratic_questions', []))} items")
        except Exception as e:
            print(f"ERROR: {subject} - {topic}: {e}")


if __name__ == "__main__":
    test_router()
