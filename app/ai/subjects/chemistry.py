"""
WaxPrep Chemistry Intelligence Module
Nigerian curriculum-specific teaching intelligence for Chemistry
Exams: WAEC, NECO, JAMB
"""

from typing import Dict, List

# Common Nigerian student misconceptions in Chemistry
NIGERIAN_CHEMISTRY_MISCONCEPTIONS = {
    "atomic_structure": [
        "Electrons orbit the nucleus like planets (Bohr model is simplified)",
        "The nucleus takes up most of the atom's space (it's mostly empty space!)",
        "Atomic number is the number of neutrons (it's protons)",
        "Isotopes have different chemical properties (chemical properties depend on electrons)"
    ],
    "chemical_bonding": [
        "Ionic bonds are weaker than covalent bonds (ionic bonds in crystal lattice are very strong)",
        "Covalent compounds always have low melting points (diamond and SiO2 have very high melting points)",
        "Hydrogen bonding is a type of covalent bond (it's intermolecular, not intramolecular)",
        "Polar molecules must have polar bonds (molecular geometry matters too)"
    ],
    "organic_chemistry": [
        "Organic chemistry only studies living things (it's carbon compounds, natural and synthetic)",
        "All organic compounds come from plants/animals (many are synthesized)",
        "Saturated means the compound is full of water (it means only single bonds exist)",
        "Benzene has alternating single and double bonds (it has delocalized electrons)"
    ],
    "electrochemistry": [
        "Oxidation always involves oxygen (it's loss of electrons)",
        "Reduction means reducing mass (it's gain of electrons)",
        "OIL RIG mnemonic is confusing (Oxidation Is Loss, Reduction Is Gain of electrons)",
        "Electrolysis and electrochemical cells work the same way (electrolysis uses external power, cells generate power)"
    ],
    "stoichiometry": [
        "1 mole of gas is always 22.4 dm³ (only at STP!)",
        "Concentration and strength are the same (concentration is amount/volume, strength is degree of ionization)",
        "Limiting reagent is the one with smallest mass (it's about mole ratio)",
        "Theoretical yield is always the actual yield (side reactions and losses reduce actual yield)"
    ]
}

# Nigerian-context chemistry examples
NIGERIAN_CHEMISTRY_CONTEXT = {
    "stoichiometry": "A bottle of concentrated HCl from a Lagos chemical store has density 1.18 g/cm³ and 36% by mass. Calculate the molarity.",
    "organic": "Kerosene (a mixture of hydrocarbons) is used for cooking in many Nigerian homes. Explain why complete combustion is important.",
    "electrochemistry": "Explain why iron roofs in Port Harrust (coastal area) rust faster than those in Kano (dry climate).",
    "acids_bases": "Calabar chalk (nzu) contains calcium carbonate. Write the equation for its reaction with stomach acid (HCl).",
    "metals": "Aluminium is used for making pots and roofing sheets in Nigeria. Explain two properties that make it suitable.",
    "water": "Explain why boiling water before drinking is recommended in rural Nigerian communities."
}

# Socratic questions for chemistry
CHEMISTRY_SOCRATIC = {
    "atomic_structure": [
        "If atoms are mostly empty space, why do solid objects feel solid?",
        "Why does the atomic number determine an element's identity, not mass number?",
        "What would happen if electrons stopped moving?",
        "How can isotopes of the same element behave identically chemically but differ physically?"
    ],
    "organic": [
        "Why can alkanes burn but not decolorize bromine water?",
        "What makes ethanol drinkable but methanol poisonous?",
        "Why does ethene turn bromine water colorless but ethane doesn't?",
        "How does soap clean? (connect to saponification)"
    ],
    "electrochemistry": [
        "Why does zinc protect iron from rusting when they're in contact?",
        "What happens at each electrode during electrolysis of brine?",
        "Why can't you use AC for electrolysis effectively?",
        "How does a car battery recharge?"
    ],
    "chemical_equilibrium": [
        "Why does increasing pressure favor the side with fewer gas moles?",
        "What happens to equilibrium if you remove a product?",
        "Why does a catalyst not change equilibrium position?",
        "How does Le Chatelier's principle apply to blood oxygen transport?"
    ]
}

# Essential chemistry formulas
CHEMISTRY_FORMULAS = {
    "mole_concept": "n = mass/Mr = volume/24 (gas at rtp) = concentration × volume",
    "concentration": "C = n/V (mol/dm³)",
    "percentage_yield": "% yield = (actual yield/theoretical yield) × 100",
    "gas_laws": "PV = nRT, P₁V₁/T₁ = P₂V₂/T₂",
    "molar_gas_volume": "V_m = 22.4 dm³ at STP, 24 dm³ at room temperature",
    "pH": "pH = -log[H⁺], pOH = -log[OH⁻], pH + pOH = 14 (at 25°C)",
    "equilibrium_constant": "K_c = [products]/[reactants] (coefficients as powers)",
    "enthalpy": "ΔH = mcΔT (calorimetry)",
    "electrolysis": "Q = It, mass = (Q × M_r)/(n × 96500)",
    " oxidation_number_rules": "O in compounds is -2 (except peroxides), H is +1 (except metal hydrides), Group 1 is +1"
}


def get_chemistry_intelligence(topic: str, class_level: str) -> Dict:
    """Returns comprehensive teaching intelligence for a chemistry topic."""
    return {
        "subject": "Chemistry",
        "topic": topic,
        "class_level": class_level,
        "exam_relevance": ["WAEC", "NECO", "JAMB"] if class_level.startswith("SS") else ["BECE"],
        "waec_frequency": _get_chem_waec_freq(topic),
        "misconceptions": NIGERIAN_CHEMISTRY_MISCONCEPTIONS.get(
            _categorize_chem_topic(topic), []
        ),
        "nigerian_examples": [NIGERIAN_CHEMISTRY_CONTEXT.get(topic, "")] if topic in NIGERIAN_CHEMISTRY_CONTEXT else [],
        "socratic_questions": CHEMISTRY_SOCRATIC.get(topic, [
            f"Why is {topic} important in everyday Nigerian life?",
            f"Can you think of a Nigerian industry that depends on {topic}?",
            f"What safety precautions are needed when dealing with {topic}?"
        ]),
        "essential_formulas": _get_chem_formulas(topic),
        "practical_skills": _get_chem_practical(topic),
        "teaching_notes": _generate_chem_notes(topic, class_level),
        "safety_notes": _get_safety_notes(topic)
    }


def _categorize_chem_topic(topic: str) -> str:
    t = topic.lower()
    if any(x in t for x in ["atom", "electron", "proton", "isotope"]):
        return "atomic_structure"
    if any(x in t for x in ["bond", "ionic", "covalent", "metallic"]):
        return "chemical_bonding"
    if any(x in t for x in ["organic", "alkane", "alkene", "alcohol", "acid", "ester", "hydrocarbon"]):
        return "organic_chemistry"
    if any(x in t for x in ["electrolysis", "redox", "electrochemical", "cell"]):
        return "electrochemistry"
    if any(x in t for x in ["mole", "stoichiometry", "calculation", "titration"]):
        return "stoichiometry"
    return "general"


def _get_chem_waec_freq(topic: str) -> str:
    high = ["organic", "electrolysis", "titration", "gas_law", "redox", "atomic", "bonding"]
    for h in high:
        if h in topic.lower():
            return "high"
    return "medium"


def _get_chem_formulas(topic: str) -> Dict:
    t = topic.lower()
    relevant = {}
    if any(x in t for x in ["mole", "stoichiom", "calculation"]):
        relevant["mole_concept"] = CHEMISTRY_FORMULAS["mole_concept"]
        relevant["concentration"] = CHEMISTRY_FORMULAS["concentration"]
    if any(x in t for x in ["equilibrium"]):
        relevant["K_c"] = CHEMISTRY_FORMULAS["equilibrium_constant"]
    if any(x in t for x in ["acid", "base", "pH"]):
        relevant["pH"] = CHEMISTRY_FORMULAS["pH"]
    if any(x in t for x in ["electrolysis"]):
        relevant["electrolysis"] = CHEMISTRY_FORMULAS["electrolysis"]
    if any(x in t for x in ["gas"]):
        relevant["gas_laws"] = CHEMISTRY_FORMULAS["gas_laws"]
    if any(x in t for x in ["enthalpy", "thermo", "heat"]):
        relevant["calorimetry"] = CHEMISTRY_FORMULAS["enthalpy"]
    return relevant


def _get_chem_practical(topic: str) -> List[str]:
    t = topic.lower()
    if "titration" in t:
        return ["Use pipette and burette", "Read meniscus at eye level", "Use indicator correctly", "Record to 2 decimal places"]
    if "qualitative" in t:
        return ["Use clean test tubes", "Add reagents drop by drop", "Record observations carefully", "Test for gases correctly"]
    if "organic" in t:
        return ["Test for unsaturation (bromine water)", "Distinguish aldehyde from ketone", "Perform esterification", "Test for alcohols"]
    return ["Handle chemicals safely", "Read measurements accurately", "Record observations", "Clean apparatus after use"]


def _generate_chem_notes(topic: str, class_level: str) -> str:
    return f"""Teaching Chemistry - {topic} at {class_level}:
1. Start with Nigerian-context examples (local industries, common substances)
2. Emphasize safety in all practical work
3. Use mnemonics for memorization (OIL RIG, PPP, etc.)
4. Connect organic chemistry to Nigerian products (palm oil, petroleum, soap)
5. Practice calculation-heavy questions regularly"""


def _get_safety_notes(topic: str) -> str:
    t = topic.lower()
    if any(x in t for x in ["acid", "base", "titration"]):
        return "ALWAYS: Wear goggles, use pipette filler, add acid to water (not water to acid), have bicarbonate nearby"
    if "organic" in t:
        return "ALWAYS: Work in fume cupboard, no open flames with volatile solvents, wash hands after handling"
    if "electrolysis" in t:
        return "ALWAYS: Check DC supply, don't touch electrodes while current flows, use low voltage"
    return "ALWAYS: Wear lab coat and goggles, tie back hair, know location of fire extinguisher and eye wash"
