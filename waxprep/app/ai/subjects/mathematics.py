from typing import Dict, Any, List, Optional

CIRCLE_THEOREM_TEACHING_GUIDE = """
CIRCLE THEOREMS — COMPLETE TEACHING GUIDE FOR WAXPREP

There are 8 circle theorems in the Nigerian SS1 curriculum. Teach them in this exact order. Each builds on the previous.

THEOREM 1 — ANGLE AT CENTRE
The angle that an arc subtends at the centre of a circle is twice the angle it subtends at any point on the circumference.
Teaching approach: "Imagine you have a slice of cake. The angle at the centre where the cake was cut is the 'big' angle. Anywhere else on the rim of the plate where someone is watching the cake being cut — they see exactly half that angle. Centre angle = 2 × circumference angle."
Common error: Students think it is the other way around. Always ask: "Which angle is bigger — the one at the centre or the one at the edge?" Answer: centre is always bigger.

THEOREM 2 — ANGLE IN A SEMICIRCLE
Any angle inscribed in a semicircle is exactly 90 degrees.
Teaching approach: "If you draw a diameter — that is, a line that goes straight through the centre — and then put a dot anywhere on the top half of the circle and connect it to both ends of the diameter, you always get a right angle at the dot. Always. No exceptions."
Common error: Students think this only works for specific positions of the dot.

THEOREM 3 — ANGLES IN THE SAME SEGMENT
Angles subtended by the same arc in the same segment of a circle are equal.
Teaching approach: "Put two dots anywhere on the same side of a chord. Connect each dot to both ends of the chord. Those two angles — one at each dot — are always equal to each other. Like twins. They see the same chord from the same side so they see the same angle."

THEOREM 4 — CYCLIC QUADRILATERAL
In a cyclic quadrilateral (all four corners touch the circle), opposite angles add up to 180 degrees.
Teaching approach: "If you can fit a four-sided shape perfectly inside a circle with all four corners touching the edge, then opposite corners are supplementary — they add up to 180. Like they are compensating for each other."
Common error: Students apply this to any quadrilateral instead of only ones inscribed in a circle.

THEOREM 5 — TANGENT PERPENDICULAR TO RADIUS
A tangent to a circle is perpendicular (at 90 degrees) to the radius at the point of tangency.
Teaching approach: "A tangent just barely touches the circle at one point — it does not go inside. At that touching point, the radius going from the centre to the touching point is always perfectly vertical if the tangent is horizontal. They always meet at 90 degrees."

THEOREM 6 — TANGENTS FROM EXTERNAL POINT
Two tangent lines drawn from the same external point to a circle are always equal in length.
Teaching approach: "If you are standing outside a circle and you can touch two points on the circle with two straight lines — both from where you are standing — those two lines have exactly the same length. By symmetry."

THEOREM 7 — ALTERNATE SEGMENT THEOREM
The angle between a tangent to a circle and a chord drawn from the point of tangency equals the inscribed angle subtending the same arc on the opposite side.
Teaching approach: "This is the trickiest one. The angle inside the triangle on the right equals the angle between the tangent and chord on the left. They are in alternate positions — one is in the circle, the other is between the tangent and the circle."

THEOREM 8 — INTERSECTING CHORDS
When two chords intersect inside a circle, the product of their segments are equal.
If chord AB and chord CD intersect at point P: AP × PB = CP × PD
Teaching approach: "Think of two sticks crossing inside a hula hoop. The short piece of one stick times its long piece equals the short piece of the other stick times its long piece."

HOW TO TEACH CIRCLE THEOREMS ON WHATSAPP:
Since you cannot draw diagrams, describe positions using clock positions. "Imagine the centre of a clock. The angle at 12 o'clock on the edge..." Use hands and body parts for student reference: "Put your left arm straight out. Your elbow is the centre of the circle. Your fingers are one end of the arc. Now if someone else puts their finger anywhere on the top half of the clock face..."

IMPORTANT FOR STUDENTS WHO MISSED THIS TOPIC:
If a student mentions they missed circle theorems in class (common for students who changed schools or had gaps in SS2), start with definitions of chord, arc, and segment before touching any theorem. Spend at least 2-3 exchanges on each theorem before moving on. Use the worked example approach — give them a problem for each theorem after explaining it. Build from angle_at_centre first — it is the foundation for all other theorems.
"""

MATHEMATICS_CONCEPTS = {
    "circle_theorems": {
        "teaching_guide": CIRCLE_THEOREM_TEACHING_GUIDE,
        "waec_pattern": "Usually 2-3 questions. Typically: find a missing angle given 2-3 known angles in a diagram with multiple theorems needed.",
        "jamb_pattern": "Usually 1-2 questions. Straightforward application of one theorem.",
        "starter_question": "Let's start with the basics. What do you think a chord is in a circle — not the outside, not the centre, just a chord?",
    },
    "quadratic_equations": {
        "methods": ["factorization", "completing_the_square", "quadratic_formula"],
        "waec_pattern": "Usually 1 question in Section A (multiple choice) and 1 in Section B (worked solution). Both methods and word problems appear.",
        "jamb_pattern": "2-3 questions. Often disguised as word problems. Also appears as 'find the roots of...'",
        "starter_question": "Before we look at any method — what does it actually mean to solve a quadratic equation? What are you looking for?",
    },
    "logarithms": {
        "key_laws": [
            "log(AB) = log(A) + log(B)",
            "log(A/B) = log(A) - log(B)",
            "log(A^n) = n × log(A)",
            "log base a of a = 1",
            "log base a of 1 = 0",
        ],
        "jamb_pattern": "Usually 2-3 questions. Often in the form: 'find x if log₂(x) = 3' or 'simplify log₃(27) + log₃(9)'",
        "starter_question": "If I told you that log₂(8) = 3, could you tell me what that actually means in plain language — without using the word logarithm?",
    },
    "simultaneous_equations": {
        "methods": ["elimination", "substitution", "graphical"],
        "waec_pattern": "Almost always appears. Usually one linear-linear pair and one linear-quadratic pair in Section B.",
        "starter_question": "If I gave you two equations with two unknowns — like x + y = 10 and x - y = 4 — what would you say we are looking for?",
    },
    "statistics": {
        "key_concepts": ["mean", "median", "mode", "range", "standard_deviation", "grouped_data"],
        "waec_pattern": "Appears in Section A (3-4 MCQ) and Section B (full calculation). Standard deviation of grouped data is common.",
        "jamb_pattern": "3-4 questions. Mean from frequency table, median, and standard deviation appear most often.",
        "common_error_note": "Standard deviation: students square the deviations first, then find the mean of the squared deviations, then take the square root. The squaring happens first.",
    },
}

def get_subject_intelligence(subject: str, topic: str, class_level: str) -> str:
    if subject.lower() == "mathematics":
        concept_key = topic.lower().replace(" ", "_")
        if "circle" in concept_key or "theorem" in concept_key or "cycle" in concept_key:
            data = MATHEMATICS_CONCEPTS.get("circle_theorems", {})
            return f"CIRCLE THEOREMS CONTEXT:\n{data.get('teaching_guide', '')}\nWAEC Pattern: {data.get('waec_pattern', '')}\nJAMB Pattern: {data.get('jamb_pattern', '')}"

        elif "quadratic" in concept_key:
            data = MATHEMATICS_CONCEPTS.get("quadratic_equations", {})
            return f"QUADRATIC EQUATIONS CONTEXT:\nWAEC Pattern: {data.get('waec_pattern', '')}\nJAMB Pattern: {data.get('jamb_pattern', '')}\nKey: {data.get('starter_question', '')}"

        elif "log" in concept_key:
            data = MATHEMATICS_CONCEPTS.get("logarithms", {})
            laws = "\n".join(data.get("key_laws", []))
            return f"LOGARITHM LAWS:\n{laws}\nJAMB Pattern: {data.get('jamb_pattern', '')}"

        elif "simultaneous" in concept_key:
            data = MATHEMATICS_CONCEPTS.get("simultaneous_equations", {})
            return f"SIMULTANEOUS EQUATIONS CONTEXT:\nMethods: {', '.join(data.get('methods', []))}\nWAEC Pattern: {data.get('waec_pattern', '')}"

        elif "statistic" in concept_key or "mean" in concept_key or "deviation" in concept_key:
            data = MATHEMATICS_CONCEPTS.get("statistics", {})
            return f"STATISTICS CONTEXT:\nKey concepts: {', '.join(data.get('key_concepts', []))}\nWAEC Pattern: {data.get('waec_pattern', '')}\nJAMB: {data.get('jamb_pattern', '')}\nCommon error: {data.get('common_error_note', '')}"

    return ""
