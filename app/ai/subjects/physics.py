"""
WaxPrep Physics Intelligence Module
Nigerian curriculum-specific teaching intelligence for Physics
Exams: WAEC, NECO, JAMB
"""

from typing import Dict, List

# WAEC Physics topic frequency
WAEC_HIGH_FREQUENCY_PHYSICS = [
    "projectiles", "equilibrium_of_forces", "simple_harmonic_motion",
    "electric_circuits", "electromagnetic_induction", "atomic_physics",
    "radioactivity", "optics", "heat_energy", "waves"
]

# Common Nigerian student misconceptions in Physics
NIGERIAN_PHYSICS_MISCONCEPTIONS = {
    "mechanics": [
        "Force is needed to keep an object moving (Aristotelian view)",
        "Heavier objects fall faster than light ones",
        "Action and reaction forces cancel each other out (they act on different bodies!)",
        "Centripetal force is a separate force, not just the net force toward center"
    ],
    "electricity": [
        "Current is used up as it flows through resistors",
        "Voltage flows through a circuit (current flows, voltage is the push)",
        "Batteries supply constant current regardless of circuit",
        "Transformers work with DC as well as AC"
    ],
    "heat": [
        "Heat and temperature are the same thing",
        "Cold is a substance that flows into objects",
        "Wool warms because it generates heat (it insulates!)",
        "Metal feels colder because it IS colder (it conducts heat away faster)"
    ],
    "waves": [
        "Sound travels faster than light (it's the opposite!)",
        "All waves need a medium (electromagnetic waves don't)",
        "Frequency changes when wave crosses boundary (wavelength changes, frequency stays)",
        "Loudness is the same as pitch"
    ],
    "modern_physics": [
        "Radioactivity makes things radioactive (radiation passes through, contamination stays)",
        "Nuclear fission and fusion are the same",
        "All radiation is dangerous (background radiation is natural)",
        "Electrons orbit the nucleus like planets (quantum model is more accurate)"
    ]
}

# Nigerian-context physics examples
NIGERIAN_PHYSICS_CONTEXT = {
    "projectiles": "A football kicked by Victor Osimhen at an angle of 30 degrees with initial velocity 20 m/s. Calculate the maximum height and range.",
    "electricity": "In a Nigerian home with 220V supply, three bulbs (60W, 100W, 40W) are connected in parallel. Calculate total current drawn and monthly cost at N50 per kWh if used 6 hours daily.",
    "heat": "A 2kg pot of egusi soup cools from 100°C to 40°C. Calculate heat lost (specific heat capacity = 4200 J/kgK).",
    "waves": "A thunderstorm in Lagos is seen 3 seconds before the thunder is heard. Estimate the distance to the storm (speed of sound = 330 m/s).",
    "pressure": "Calculate the pressure at the bottom of a 10m deep well in Kaduna (density of water = 1000 kg/m³, g = 10 m/s²).",
    "optics": "A concave mirror of focal length 15cm is used as a shaving mirror. Where should the face be placed for a magnified image?"
}

# Socratic questions for physics
PHYSICS_SOCRATIC = {
    "newtons_laws": [
        "If you kick a football on the street in Lagos, why does it eventually stop?",
        "Is there a force acting on the ball after it leaves your foot?",
        "Why doesn't the Earth move up when you jump?",
        "Why do you feel pushed back into your seat when a Danfo bus accelerates?"
    ],
    "electric_circuits": [
        "What would happen to the brightness of bulbs if you add more in series?",
        "Why are house appliances connected in parallel, not series?",
        "What happens to total resistance when you add parallel resistors?",
        "Why does a short circuit cause fire?"
    ],
    "radioactivity": [
        "Why do doctors leave the room during X-rays?",
        "How can radiation be both dangerous and useful?",
        "Why does half-life not mean all radiation is gone?",
        "How do nuclear power plants generate electricity?"
    ],
    "heat_energy": [
        "Why does metal feel colder than wood at the same temperature?",
        "Why do we use wool blankets rather than metal sheets?",
        "What happens to temperature during a phase change?",
        "Why does sweating cool the body?"
    ]
}

# Essential physics formulas
PHYSICS_FORMULAS = {
    "v_final": "v = u + at",
    "s_uvt": "s = ut + (1/2)at²",
    "v_squared": "v² = u² + 2as",
    "ohms_law": "V = IR",
    "power_electrical": "P = IV = I²R = V²/R",
    "resistors_series": "R_total = R₁ + R₂ + R₃",
    "resistors_parallel": "1/R_total = 1/R₁ + 1/R₂ + 1/R₃",
    "pressure": "P = F/A = hρg",
    "density": "ρ = m/V",
    "speed_wave": "v = fλ",
    "kinetic_energy": "KE = (1/2)mv²",
    "potential_energy": "PE = mgh",
    "work_done": "W = Fs cosθ",
    "power": "P = W/t = Fv",
    "hookes_law": "F = ke",
    "gas_pressure": "PV = nRT",
    "heat_capacity": "Q = mcΔT",
    "latent_heat": "Q = mL",
    "lens_formula": "1/f = 1/u + 1/v",
    "magnification": "m = v/u"
}


def get_physics_intelligence(topic: str, class_level: str) -> Dict:
    """Returns comprehensive teaching intelligence for a physics topic."""
    return {
        "subject": "Physics",
        "topic": topic,
        "class_level": class_level,
        "exam_relevance": ["WAEC", "NECO", "JAMB"] if class_level.startswith("SS") else ["BECE"],
        "waec_frequency": _get_physics_waec_freq(topic),
        "misconceptions": NIGERIAN_PHYSICS_MISCONCEPTIONS.get(
            _categorize_topic(topic), []
        ),
        "nigerian_examples": [NIGERIAN_PHYSICS_CONTEXT.get(topic, "")] if topic in NIGERIAN_PHYSICS_CONTEXT else [],
        "socratic_questions": PHYSICS_SOCRATIC.get(topic, [
            f"Why does {topic} matter in everyday Nigerian life?",
            f"Can you give an example of {topic} you have experienced?",
            f"What would happen if {topic} worked differently?"
        ]),
        "essential_formulas": _get_physics_formulas(topic),
        "teaching_notes": _generate_physics_notes(topic, class_level),
        "difficulty": "advanced" if any(x in topic for x in ["modern", "quantum", "nuclear"]) else "intermediate" if any(x in topic for x in ["electromagnetic", "thermodynamics"]) else "basic",
        "practical_skills": _get_practical_skills(topic)
    }


def _categorize_topic(topic: str) -> str:
    topic_l = topic.lower()
    if any(x in topic_l for x in ["force", "motion", "projectile", "equilibrium", "newton"]):
        return "mechanics"
    if any(x in topic_l for x in ["electric", "circuit", "current", "resistance"]):
        return "electricity"
    if any(x in topic_l for x in ["heat", "temperature", "thermo", "latent"]):
        return "heat"
    if any(x in topic_l for x in ["wave", "sound", "light", "optics"]):
        return "waves"
    if any(x in topic_l for x in ["atom", "nuclear", "radioactive", "quantum"]):
        return "modern_physics"
    return "general"


def _get_physics_waec_freq(topic: str) -> str:
    high = ["electric", "heat", "wave", "radioactive", "projectile", "optics", "shm"]
    for h in high:
        if h in topic.lower():
            return "high"
    return "medium"


def _get_physics_formulas(topic: str) -> Dict:
    topic_l = topic.lower()
    relevant = {}
    if any(x in topic_l for x in ["motion", "projectile", "kinematic"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["v_final", "s_uvt", "v_squared"]})
    if any(x in topic_l for x in ["electric", "circuit", "current"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["ohms_law", "power_electrical", "resistors_series", "resistors_parallel"]})
    if any(x in topic_l for x in ["heat", "latent", "specific"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["heat_capacity", "latent_heat"]})
    if any(x in topic_l for x in ["wave", "sound"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["speed_wave"]})
    if any(x in topic_l for x in ["pressure", "fluid"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["pressure", "density"]})
    if any(x in topic_l for x in ["energy", "work", "power"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["kinetic_energy", "potential_energy", "work_done", "power"]})
    if any(x in topic_l for x in ["lens", "mirror", "optics"]):
        relevant.update({k: v for k, v in PHYSICS_FORMULAS.items() if k in ["lens_formula", "magnification"]})
    return relevant


def _generate_physics_notes(topic: str, class_level: str) -> str:
    return f"""Teaching Physics - {topic} at {class_level}:
1. Connect to real Nigerian examples (electricity in homes, transport, weather)
2. Use demonstrations where possible
3. Emphasize formula application with units
4. Address common misconceptions directly
5. Practice with WAEC/NECO past questions"""


def _get_practical_skills(topic: str) -> List[str]:
    topic_l = topic.lower()
    if "electric" in topic_l:
        return ["Connect circuits", "Read ammeters and voltmeters", "Determine resistance"]
    if "heat" in topic_l:
        return ["Measure specific heat capacity", "Determine latent heat", "Use calorimeter"]
    if "optics" in topic_l or "lens" in topic_l or "mirror" in topic_l:
        return ["Determine focal length", "Draw ray diagrams", "Locate images"]
    if "wave" in topic_l:
        return ["Measure wavelength", "Determine frequency", "Use ripple tank"]
    return ["Take accurate measurements", "Plot graphs", "Analyze data"]
