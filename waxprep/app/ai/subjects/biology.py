"""Biology subject intelligence — placeholder for curriculum-specific teaching context."""


def get_biology_intelligence(topic: str, class_level: str) -> str:
    """Return teaching intelligence context for biology topics.

    Args:
        topic: The biology topic being taught
        class_level: Student's class level (e.g., JSS1, SS1)

    Returns:
        Teaching context string or empty string if no specific intelligence available
    """
    topic_lower = topic.lower().replace(" ", "_")

    if "cell" in topic_lower or "organelle" in topic_lower or "membrane" in topic_lower:
        return (
            "CELL BIOLOGY TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Cell structure identification, functions of organelles, "
            "differences between plant and animal cells.\n"
            "JAMB Pattern: 2-3 questions. Often tests understanding of cell division (mitosis vs meiosis).\n"
            "Key organelles: Nucleus (control centre), Mitochondria (energy/respiration), "
            "Ribosomes (protein synthesis), Chloroplasts (photosynthesis — plant only), "
            "Cell membrane (selective permeability), Cell wall (plants — cellulose).\n"
            "Common error: Confusing cell wall with cell membrane, thinking animal cells have cell walls, "
            "or that chloroplasts exist in animal cells.\n"
            "Starter: 'Name three structures found in a plant cell but NOT in an animal cell. Why are they needed?'"
        )

    if "photosynthesis" in topic_lower or "chlorophyll" in topic_lower:
        return (
            "PHOTOSYNTHESIS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Equation balancing, factors affecting rate, "
            "light-dependent vs light-independent reactions.\n"
            "JAMB Pattern: 1-2 questions. Often tests limiting factors and experimental design.\n"
            "Key equation: 6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂ (with light and chlorophyll)\n"
            "Limiting factors: Light intensity, CO₂ concentration, Temperature (enzyme-dependent)\n"
            "Common error: Thinking plants only do photosynthesis (they also respire 24/7). "
            "Confusing the inputs and outputs — CO₂ goes IN, O₂ comes OUT.\n"
            "Starter: 'If you put a plant in complete darkness, what happens to photosynthesis? Does the plant die? Why or why not?'"
        )

    if "respiration" in topic_lower or "aerobic" in topic_lower or "anaerobic" in topic_lower:
        return (
            "RESPIRATION TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Equations, comparison of aerobic vs anaerobic, "
            "respiratory substrates, respiratory quotient.\n"
            "JAMB Pattern: 1-2 questions. Often combined with energy flow or gas exchange.\n"
            "Aerobic: C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + 38ATP (or ~30 ATP in eukaryotes)\n"
            "Anaerobic in animals: C₆H₁₂O₆ → 2C₃H₆O₃ (lactic acid) + 2ATP\n"
            "Anaerobic in yeast: C₆H₁₂O₆ → 2C₂H₅OH + 2CO₂ + 2ATP\n"
            "Common error: Thinking respiration is just breathing. Breathing = gas exchange; "
            "Respiration = chemical energy release in cells.\n"
            "Starter: 'Why does a sprinter's muscle hurt after a 100m race? What is building up in their muscles?'"
        )

    if "genetic" in topic_lower or "DNA" in topic or "heredity" in topic_lower or "inherit" in topic_lower:
        return (
            "GENETICS & INHERITANCE TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Monohybrid and dihybrid crosses, Punnett squares, "
            "genotype vs phenotype ratios.\n"
            "JAMB Pattern: 2-3 questions. Often tests probability and blood group inheritance.\n"
            "Key: Genotype = genetic makeup (TT, Tt, tt), Phenotype = physical appearance\n"
            "Dominant allele expressed when present (T), Recessive only when homozygous (tt)\n"
            "Monohybrid ratio: 3:1 (dominant:recessive), Test cross: 1:1\n"
            "Common error: Confusing genotype with phenotype. Forgetting that carriers (heterozygous) "
            "don't show the recessive trait but can pass it on.\n"
            "Starter: 'If a heterozygous tall plant (Tt) is crossed with a short plant (tt), "
            "what percentage of offspring will be tall? Show me the Punnett square.'"
        )

    if "ecosystem" in topic_lower or "food chain" in topic_lower or "food web" in topic_lower or "trophic" in topic_lower:
        return (
            "ECOLOGY & ECOSYSTEMS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Food chains/webs, energy flow, pyramids of numbers/energy/biomass.\n"
            "JAMB Pattern: 1-2 questions. Ecological succession, population dynamics, nitrogen/carbon cycles.\n"
            "Key: Producers → Primary consumers → Secondary consumers → Tertiary consumers\n"
            "Energy transfer: Only ~10% passes between trophic levels (90% lost as heat)\n"
            "Common error: Putting decomposers at the 'end' of a food chain (they act at ALL levels). "
            "Thinking energy is recycled (matter cycles, energy flows through — it does not cycle).\n"
            "Starter: 'In a food chain Grass → Grasshopper → Frog → Snake, if the grass has 10,000 kJ of energy, "
            "roughly how much reaches the snake?'"
        )

    if "reproduction" in topic_lower or "reproduct" in topic_lower:
        return (
            "REPRODUCTION TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Male/female reproductive structures, menstrual cycle, "
            "asexual vs sexual reproduction, pollination in plants.\n"
            "JAMB Pattern: 1-2 questions. Often tests plant reproduction and reproductive hormones.\n"
            "Key: Asexual = one parent, identical offspring (binary fission, budding, cuttings)\n"
            "Sexual = two parents, genetic variation (meiosis produces gametes, fertilization restores diploid)\n"
            "Common error: Thinking pollination = fertilization. Pollination is transfer of pollen; "
            "fertilization is fusion of male and female gametes (happens AFTER pollination).\n"
            "Starter: 'What is the main advantage of sexual reproduction over asexual reproduction? "
            "What is the main disadvantage?'"
        )

    return ""
