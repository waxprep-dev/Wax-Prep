"""
WaxPrep Mathematics Intelligence Module
Nigerian curriculum-specific teaching intelligence for Mathematics
Exams: WAEC, NECO, JAMB, BECE
"""

import json
import os
from typing import Dict, List, Optional

# WAEC Mathematics topic frequency patterns
WAEC_HIGH_FREQUENCY_TOPICS = [
    "simultaneous_equations", "quadratic_equations", "logarithms", "trigonometry",
    "mensuration", "statistics", "probability", "differentiation", "integration",
    "circle_geometry", "coordinate_geometry", "vectors", "sequences_series",
    "algebraic_fractions", "indices", "surds", "bearing", "sets"
]

# Common Nigerian student misconceptions in Mathematics
NIGERIAN_MATH_MISCONCEPTIONS = {
    "algebra": [
        "Thinking (a+b)^2 = a^2 + b^2 (forgetting 2ab)",
        "Confusing expansion with factorization",
        "Believing x + x = x^2 instead of 2x",
        "Difficulty with sign changes when moving terms across equals sign"
    ],
    "trigonometry": [
        "Using SOHCAHTOA in non-right triangles instead of sine/cosine rule",
        "Confusing angles of elevation with depression",
        "Forgetting to check calculator mode (deg vs rad)",
        "Using Pythagoras where trig ratios are needed"
    ],
    "logarithms": [
        "log(a+b) = log(a) + log(b) - WRONG",
        "Forgetting log(1) = 0 and log(base) = 1",
        "Incorrect change of base formula application",
        "Confusing antilog with reciprocal"
    ],
    "differentiation": [
        "d(uv) = du * dv (product rule confusion)",
        "Forgetting chain rule for composite functions",
        "Confusing increasing/decreasing with max/min",
        "Setting dy/dx = 0 without checking nature of stationary point"
    ],
    "statistics": [
        "Using mean when median is more appropriate (skewed data)",
        "Confusing class boundaries with class limits",
        "Forgetting to order data before finding median",
        "Using n instead of (n-1) in standard deviation"
    ]
}

# Nigerian-relevant math examples
NIGERIAN_CONTEXT_EXAMPLES = {
    "percentage": "If a trader in Onitsha market buys garri for N5000 and wants 25% profit, what should be the selling price?",
    "ratio": "If 3 farmers in Kano share fertilizer in ratio 2:3:5 and total is 100 bags, how many does each get?",
    "simultaneous_eq": "A bus from Lagos to Ibadan carries 60 passengers. Children's fare is N200, adult is N500. Total fare collected is N21,000. How many children and adults?",
    "trigonometry": "A GSM mast in Abuja casts a shadow 15m long when the angle of elevation of the sun is 40 degrees. Find the height of the mast.",
    "mensuration": "A circular fish pond in Delta State has radius 7m. Find the area and circumference (take pi = 22/7).",
    "statistics": "The ages of 10 JSS3 students in a Lagos school are: 12, 13, 11, 14, 12, 13, 12, 11, 13, 12. Find the mean, median, and mode."
}

# Socratic starter questions for math topics
SOCRATIC_QUESTIONS = {
    "quadratic_equations": [
        "What does it mean to 'solve' a quadratic equation?",
        "Why do we sometimes get two answers?",
        "Can a quadratic equation have no real solutions? When?",
        "What's the relationship between the graph and the roots?"
    ],
    "differentiation": [
        "What does the gradient of a curve tell us at any point?",
        "Why do we set dy/dx = 0 to find maximum/minimum?",
        "How would you know if a point is maximum or minimum?",
        "Where in real life do we need to find maximum or minimum values?"
    ],
    "trigonometry": [
        "Why does SOHCAHTOA only work for right-angled triangles?",
        "What would you use for a non-right triangle?",
        "What's the difference between angle of elevation and depression?",
        "Why do bearings use three figures (e.g., 060 not 60)?"
    ],
    "logarithms": [
        "Why were logarithms invented before calculators?",
        "What does log(100) = 2 actually mean?",
        "Why can't we take log of a negative number?",
        "How do logarithms turn multiplication into addition?"
    ]
}

# Key formulas students must memorize
ESSENTIAL_FORMULAS = {
    "quadratic_formula": "x = [-b ± sqrt(b² - 4ac)] / 2a",
    "sine_rule": "a/sinA = b/sinB = c/sinC",
    "cosine_rule": "c² = a² + b² - 2ab cosC",
    "area_triangle_trig": "Area = (1/2)ab sinC",
    "circle_area": "A = πr²",
    "cylinder_volume": "V = πr²h",
    "sphere_volume": "V = (4/3)πr³",
    "differentiation_power_rule": "d/dx(x^n) = nx^(n-1)",
    "integration_power_rule": "∫x^n dx = x^(n+1)/(n+1) + C",
    "ap_nth_term": "T_n = a + (n-1)d",
    "ap_sum": "S_n = n/2[2a + (n-1)d]",
    "gp_nth_term": "T_n = ar^(n-1)",
    "laws_of_indices": "a^m × a^n = a^(m+n), a^m ÷ a^n = a^(m-n), (a^m)^n = a^(mn)"
}


def get_mathematics_intelligence(topic: str, class_level: str) -> Dict:
    """
    Returns comprehensive teaching intelligence for a mathematics topic.
    
    Args:
        topic: The mathematics topic (e.g., 'quadratic_equations', 'trigonometry')
        class_level: The class level (JSS1-3, SS1-3)
    
    Returns:
        Dictionary containing teaching context, misconceptions, examples, and questions
    """
    intelligence = {
        "subject": "Mathematics",
        "topic": topic,
        "class_level": class_level,
        "exam_relevance": _get_exam_relevance(class_level),
        "waec_frequency": _get_waec_frequency(topic),
        "misconceptions": NIGERIAN_MATH_MISCONCEPTIONS.get(topic, []),
        "nigerian_examples": _get_examples_for_topic(topic),
        "socratic_questions": SOCRATIC_QUESTIONS.get(topic, []),
        "essential_formulas": _get_formulas_for_topic(topic),
        "teaching_notes": _generate_teaching_notes(topic, class_level),
        "difficulty_level": _assess_difficulty(topic, class_level),
        "prerequisites": _get_prerequisites(topic, class_level)
    }
    return intelligence


def _get_exam_relevance(class_level: str) -> List[str]:
    """Determine which exams are relevant for this class level."""
    if class_level.startswith("JSS"):
        return ["BECE", "Junior WAEC"]
    elif class_level.startswith("SS"):
        return ["WAEC", "NECO", "JAMB"]
    return []


def _get_waec_frequency(topic: str) -> str:
    """Determine how frequently this topic appears in WAEC."""
    high_freq = ["simultaneous_equations", "quadratic", "logarithms", "trigonometry",
                 "mensuration", "statistics", "probability", "differentiation", "integration"]
    medium_freq = ["sets", "surds", "indices", "sequences", "circle_geometry", "vectors"]
    
    for hf in high_freq:
        if hf in topic.lower():
            return "high"
    for mf in medium_freq:
        if mf in topic.lower():
            return "medium"
    return "low"


def _get_examples_for_topic(topic: str) -> List[str]:
    """Get Nigerian-context examples for a topic."""
    examples = []
    topic_lower = topic.lower()
    
    if any(word in topic_lower for word in ["simultaneous", "equation", "algebra"]):
        examples.append(NIGERIAN_CONTEXT_EXAMPLES.get("simultaneous_eq"))
    if any(word in topic_lower for word in ["percentage", "profit", "loss"]):
        examples.append(NIGERIAN_CONTEXT_EXAMPLES.get("percentage"))
    if any(word in topic_lower for word in ["ratio", "proportion"]):
        examples.append(NIGERIAN_CONTEXT_EXAMPLES.get("ratio"))
    if any(word in topic_lower for word in ["trig", "elevation", "bearing"]):
        examples.append(NIGERIAN_CONTEXT_EXAMPLES.get("trigonometry"))
    if any(word in topic_lower for word in ["area", "volume", "mensuration"]):
        examples.append(NIGERIAN_CONTEXT_EXAMPLES.get("mensuration"))
    if any(word in topic_lower for word in ["mean", "median", "mode", "statistics"]):
        examples.append(NIGERIAN_CONTEXT_EXAMPLES.get("statistics"))
    
    return [e for e in examples if e]


def _get_formulas_for_topic(topic: str) -> Dict[str, str]:
    """Get essential formulas for a topic."""
    topic_lower = topic.lower()
    relevant = {}
    
    if "quadratic" in topic_lower:
        relevant["quadratic_formula"] = ESSENTIAL_FORMULAS["quadratic_formula"]
    if "trig" in topic_lower:
        relevant["sine_rule"] = ESSENTIAL_FORMULAS["sine_rule"]
        relevant["cosine_rule"] = ESSENTIAL_FORMULAS["cosine_rule"]
        relevant["area_triangle_trig"] = ESSENTIAL_FORMULAS["area_triangle_trig"]
    if "mensuration" in topic_lower or "area" in topic_lower or "volume" in topic_lower:
        relevant["circle_area"] = ESSENTIAL_FORMULAS["circle_area"]
        relevant["cylinder_volume"] = ESSENTIAL_FORMULAS["cylinder_volume"]
        relevant["sphere_volume"] = ESSENTIAL_FORMULAS["sphere_volume"]
    if "differentiation" in topic_lower or "calculus" in topic_lower:
        relevant["power_rule"] = ESSENTIAL_FORMULAS["differentiation_power_rule"]
    if "integration" in topic_lower:
        relevant["power_rule"] = ESSENTIAL_FORMULAS["integration_power_rule"]
    if "sequence" in topic_lower or "series" in topic_lower or "ap" in topic_lower or "gp" in topic_lower:
        relevant["ap_nth_term"] = ESSENTIAL_FORMULAS["ap_nth_term"]
        relevant["ap_sum"] = ESSENTIAL_FORMULAS["ap_sum"]
        relevant["gp_nth_term"] = ESSENTIAL_FORMULAS["gp_nth_term"]
    if "indices" in topic_lower or "log" in topic_lower:
        relevant["laws_of_indices"] = ESSENTIAL_FORMULAS["laws_of_indices"]
    
    return relevant


def _generate_teaching_notes(topic: str, class_level: str) -> str:
    """Generate teaching notes for a topic."""
    notes = f"Teaching {topic} at {class_level} level:\n\n"
    notes += f"1. Start with Nigerian-context examples to engage students\n"
    notes += f"2. Address common misconceptions early\n"
    notes += f"3. Use Socratic questioning to develop understanding\n"
    notes += f"4. Connect to {_get_exam_relevance(class_level)} exam patterns\n"
    notes += f"5. Provide ample practice with past questions\n"
    return notes


def _assess_difficulty(topic: str, class_level: str) -> str:
    """Assess difficulty level of topic for class."""
    advanced_topics = ["differentiation", "integration", "vectors", "mechanics", 
                       "conic_sections", "complex_numbers", "matrices"]
    if any(at in topic.lower() for at in advanced_topics):
        return "advanced"
    intermediate_topics = ["trigonometry", "logarithms", "circle_geometry", "probability"]
    if any(it in topic.lower() for it in intermediate_topics):
        return "intermediate"
    return "basic"


def _get_prerequisites(topic: str, class_level: str) -> List[str]:
    """Get prerequisite topics."""
    prereqs = {
        "differentiation": ["algebra", "functions", "limits"],
        "integration": ["differentiation", "algebra"],
        "trigonometry": ["pythagoras", "angles", "ratios"],
        "logarithms": ["indices", "exponentials"],
        "simultaneous_equations": ["linear_equations", "algebraic_manipulation"],
        "quadratic_equations": ["factorization", "linear_equations"],
        "circle_geometry": ["angles", "triangles", "pythagoras"],
        "vectors": ["coordinate_geometry", "trigonometry"]
    }
    return prereqs.get(topic.lower(), ["basic_arithmetic", "basic_algebra"])
