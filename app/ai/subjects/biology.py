"""
WaxPrep Biology Intelligence Module
Nigerian curriculum-specific teaching intelligence for Biology
Exams: WAEC, NECO, JAMB, BECE
"""

from typing import Dict, List

# Common Nigerian student misconceptions in Biology
NIGERIAN_BIOLOGY_MISCONCEPTIONS = {
    "cell_biology": [
        "All cells look the same (they have different structures for different functions)",
        "Plant cells have cell walls, animal cells don't (true, but students often think animal cells have no structure)",
        "The nucleus is the brain of the cell (it's the control center, but cells don't 'think')",
        "Viruses are living organisms (they can only reproduce inside host cells)"
    ],
    "genetics": [
        "Acquired characteristics can be inherited (Lamarckism - disproven)",
        "Dominant alleles are 'stronger' or more common (dominance is about expression, not frequency)",
        "Males always determine the sex of offspring (actually, males provide X or Y, females always X)",
        "Cloning produces identical adults (clones have identical DNA but environmental factors differ)",
        "Genetically modified organisms are always dangerous (GM has benefits and risks)"
    ],
    "ecology": [
        "Humans are not part of food webs (we are apex consumers)",
        "Decomposers are not important (they recycle nutrients - essential!)",
        "The pyramid of numbers is always upright (it can be inverted for parasites/trees)",
        "More species diversity means stronger ecosystem (usually true, but context matters)",
        "Ecological succession always leads to forest (climax community depends on climate)"
    ],
    "physiology": [
        "Respiration is breathing (breathing is ventilation, respiration is energy release)",
        "Plants only take in CO2 and give out O2 (they do both respiration and photosynthesis)",
        "The heart creates blood (it pumps blood made in bone marrow)",
        "Arteries always carry oxygenated blood (pulmonary artery carries deoxygenated blood)",
        "Urine is formed by filtering blood only (selective reabsorption also occurs)"
    ],
    "reproduction": [
        "Menstruation is removing 'bad blood' (it's the uterine lining when no pregnancy occurs)",
        "Fertilization happens in the uterus (it happens in the fallopian tube)",
        "Twins always skip a generation (fraternal twins depend on mother's ovulation)",
        "Contraception is the same as abortion (contraception prevents pregnancy, abortion ends it)"
    ]
}

# Nigerian-context biology examples
NIGERIAN_BIOLOGY_CONTEXT = {
    "photosynthesis": "Cassava farming is important in Nigeria. Explain how cassava plants use sunlight to produce starch.",
    "ecology": "The Niger Delta mangrove forests are being destroyed by oil pollution. Explain the impact on local food chains.",
    "genetics": "Sickle cell disease is common in Nigeria. Using a Punnett square, explain the probability of a child having the disease if both parents are carriers (AS x AS).",
    "nutrition": "Compare the nutritional value of garri (cassava flakes) and rice as staple foods in Nigerian diet.",
    "reproduction": "Explain the importance of family planning in reducing Nigeria's population growth rate.",
    "health": "Malaria is endemic in Nigeria. Describe the life cycle of the Plasmodium parasite and control measures.",
    "respiration": "Explain why athletes training in Jos (high altitude) have better stamina when competing in Lagos.",
    "microorganisms": "Explain how fermentation is used in making ogi (pap) and garri from cassava."
}

# Socratic questions for biology
BIOLOGY_SOCRATIC = {
    "photosynthesis": [
        "Why are plants green? What would happen if they were black?",
        "Why does photosynthesis only happen during the day?",
        "What would happen to life on Earth if all plants disappeared?",
        "Why do plants need both chlorophyll and light?"
    ],
    "genetics": [
        "Why does sickle cell trait persist in Nigeria despite the disease?",
        "If identical twins have the same DNA, why might they look slightly different?",
        "Why can't a man with blood group O be the father of a child with AB (if mother is A)?",
        "How does DNA determine what you look like?"
    ],
    "ecology": [
        "What would happen if all mosquitoes in Nigeria were eliminated?",
        "Why is biodiversity important for agriculture?",
        "How does deforestation in the north lead to desertification?",
        "Why can't a food chain have more than 5 trophic levels?"
    ],
    "human_health": [
        "Why does the body produce antibodies after vaccination?",
        "How does HIV weaken the immune system specifically?",
        "Why can't antibiotics cure malaria?",
        "What makes a balanced diet different from just eating enough calories?"
    ]
}

# Practical biology skills
BIOLOGY_PRACTICALS = {
    "food_tests": [
        "Starch test: Add iodine solution → blue-black color",
        "Reducing sugar test: Benedict's solution + heat → brick-red precipitate",
        "Protein test: Biuret reagent → purple/violet color",
        "Fat test: Translucent spot on paper / emulsion test",
        "Vitamin C test: DCPIP decolorization"
    ],
    "microscope": [
        "Start with lowest magnification",
        "Use coarse adjustment first, then fine",
        "Center specimen before increasing magnification",
        "Calculate magnification: eyepiece × objective"
    ],
    "osmosis": [
        "Set up potato cylinder in different concentrations",
        "Measure initial and final length/mass",
        "Plot graph of concentration vs % change",
        "Determine isotonic concentration"
    ],
    "respiration": [
        "Use germinating seeds (active respiration)",
        "Use limewater to detect CO2 (turns cloudy)",
        "Use hydrogencarbonate indicator (yellow = more CO2)",
        "Compare boiled (control) vs living seeds"
    ]
}

# Essential biology diagrams students must know
ESSENTIAL_DIAGRAMS = [
    "Plant and animal cells (label all organelles)",
    "Structure of the heart (including valves and blood vessels)",
    "Human digestive system",
    "Human respiratory system",
    "Structure of a leaf (cross-section)",
    "Male and female reproductive systems",
    "Kidney nephron",
    "Food web (Nigerian savanna example)",
    "Carbon cycle",
    "DNA double helix structure"
]


def get_biology_intelligence(topic: str, class_level: str) -> Dict:
    """Returns comprehensive teaching intelligence for Biology."""
    return {
        "subject": "Biology",
        "topic": topic,
        "class_level": class_level,
        "exam_relevance": ["WAEC", "NECO", "JAMB"] if class_level.startswith("SS") else ["BECE"],
        "waec_frequency": _get_bio_waec_freq(topic),
        "misconceptions": NIGERIAN_BIOLOGY_MISCONCEPTIONS.get(
            _categorize_bio_topic(topic), []
        ),
        "nigerian_examples": [NIGERIAN_BIOLOGY_CONTEXT.get(topic, "")] if topic in NIGERIAN_BIOLOGY_CONTEXT else [],
        "socratic_questions": BIOLOGY_SOCRATIC.get(topic, [
            "How does this process work in everyday Nigerian life?",
            "What would happen if this system failed?",
            "How can this knowledge help Nigerians?"
        ]),
        "practical_skills": BIOLOGY_PRACTICALS.get(topic, []),
        "essential_diagrams": ESSENTIAL_DIAGRAMS if class_level.startswith("SS") else ESSENTIAL_DIAGRAMS[:6],
        "teaching_notes": _generate_bio_notes(topic, class_level)
    }


def _categorize_bio_topic(topic: str) -> str:
    t = topic.lower()
    if any(x in t for x in ["cell", "organelle", "membrane", "division"]):
        return "cell_biology"
    if any(x in t for x in ["genetic", "inheritance", "dna", "gene", "mendel", "evolution"]):
        return "genetics"
    if any(x in t for x in ["ecosystem", "food chain", "succession", "pyramid", "habitat"]):
        return "ecology"
    if any(x in t for x in ["heart", "blood", "digestion", "respiration", "excretion", "kidney", "nerve"]):
        return "physiology"
    if any(x in t for x in ["reproduction", "menstrual", "pregnancy", "contraception"]):
        return "reproduction"
    return "general"


def _get_bio_waec_freq(topic: str) -> str:
    high = ["photosynthesis", "genetics", "ecology", "physiology", "cell", "evolution", "reproduction"]
    for h in high:
        if h in topic.lower():
            return "high"
    return "medium"


def _generate_bio_notes(topic: str, class_level: str) -> str:
    return f"""Teaching Biology - {topic} at {class_level}:
1. Connect to Nigerian health and agricultural contexts
2. Use local examples (malaria, cassava, yam, oil pollution)
3. Address common misconceptions directly
4. Emphasize diagram drawing practice (WAEC requires labeled diagrams)
5. Connect theory to practical experiments
6. Use Socratic questioning to develop critical thinking
7. Practice past question analysis regularly"""
