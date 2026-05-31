"""Chemistry subject intelligence — placeholder for curriculum-specific teaching context."""


def get_chemistry_intelligence(topic: str, class_level: str) -> str:
    """Return teaching intelligence context for chemistry topics.

    Args:
        topic: The chemistry topic being taught
        class_level: Student's class level (e.g., JSS1, SS1)

    Returns:
        Teaching context string or empty string if no specific intelligence available
    """
    topic_lower = topic.lower().replace(" ", "_")

    if "periodic" in topic_lower or "element" in topic_lower or "atom" in topic_lower:
        return (
            "PERIODIC TABLE & ATOMIC STRUCTURE TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Electronic configuration, group/period trends, "
            "identifying elements from configuration.\n"
            "JAMB Pattern: 2-3 questions. Atomic number, mass number, isotopes, periodic trends.\n"
            "Key: Groups = columns (similar properties), Periods = rows (same electron shells)\n"
            "Common error: Confusing atomic number with mass number. Forgetting that group number "
            "equals valence electrons for main group elements.\n"
            "Starter: 'Sodium is in Group 1, Period 3. How many electron shells does it have? "
            "How many valence electrons? What does that tell you about its reactivity?'"
        )

    if "chemical" in topic_lower or "equation" in topic_lower or "balancing" in topic_lower:
        return (
            "CHEMICAL EQUATIONS & BALANCING TEACHING CONTEXT:\n"
            "WAEC Pattern: 1-2 questions. Balance given equations, write equations from descriptions.\n"
            "JAMB Pattern: 1-2 questions. Often combined with stoichiometry or reaction types.\n"
            "Key: Conservation of mass — same number of each atom on both sides.\n"
            "Method: Count atoms → balance metals → non-metals → hydrogen → oxygen last.\n"
            "Common error: Changing subscripts instead of coefficients. Subscripts define the compound; "
            "coefficients balance the equation.\n"
            "Starter: 'Balance this: __Fe + __O₂ → __Fe₂O₃. Walk me through atom by atom.'"
        )

    if "mole" in topic_lower or "stoich" in topic_lower or "calcul" in topic_lower:
        return (
            "MOLE CONCEPT & STOICHIOMETRY TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Molar mass, mole-volume relationships, limiting reagents.\n"
            "JAMB Pattern: 2-3 questions. Often disguised as practical calculations.\n"
            "Key: n = m/M (moles = mass/molar mass), n = V/22.4 (at STP), n = N/Nₐ\n"
            "Common error: Forgetting 22.4 dm³/mol only applies at STP (0°C, 1 atm). "
            "Confusing molar mass (g/mol) with molecular mass (unitless).\n"
            "Starter: 'How many moles are in 11.2g of iron? (Fe = 56). How many atoms is that?'"
        )

    if "acid" in topic_lower or "base" in topic_lower or "salt" in topic_lower or "pH" in topic:
        return (
            "ACIDS, BASES & SALTS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. pH calculations, neutralization reactions, salt preparation methods.\n"
            "JAMB Pattern: 2 questions. Indicators, conjugate acid-base pairs, buffer solutions.\n"
            "Key: pH = -log[H⁺], pOH = -log[OH⁻], pH + pOH = 14 (at 25°C)\n"
            "Strong acids: HCl, HNO₃, H₂SO₄. Strong bases: NaOH, KOH.\n"
            "Common error: Thinking dilution changes strong acid to weak acid. "
            "Dilution changes concentration, not strength.\n"
            "Starter: 'What is the pH of 0.001 M HCl solution? What about 0.001 M NaOH?'"
        )

    if "organic" in topic_lower or "alkane" in topic_lower or "alkene" in topic_lower or "alcohol" in topic_lower:
        return (
            "ORGANIC CHEMISTRY TEACHING CONTEXT:\n"
            "WAEC Pattern: 3-4 questions. Naming, isomerism, reactions of alkanes/alkenes/alcohols.\n"
            "JAMB Pattern: 3-4 questions. Functional groups, homologous series, polymerization.\n"
            "Key: Alkanes (CₙH₂ₙ₊₂, single bonds), Alkenes (CₙH₂ₙ, double bonds), Alcohols (-OH group)\n"
            "Common error: Confusing structural formula with molecular formula. "
            "Forgetting that cracking breaks long alkanes into shorter ones + alkenes.\n"
            "Starter: 'What is the difference between C₅H₁₂ and C₅H₁₀? Which homologous series does each belong to?'"
        )

    if "electroly" in topic_lower or "electropl" in topic_lower:
        return (
            "ELECTROLYSIS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Products at anode/cathode for molten and aqueous electrolytes.\n"
            "JAMB Pattern: 1-2 questions. Faraday's laws, electroplating calculations.\n"
            "Key: Anode = oxidation (lose electrons), Cathode = reduction (gain electrons)\n"
            "For aqueous: consider H⁺/OH⁻ from water competing with electrolyte ions.\n"
            "Common error: Assuming metal always deposits at cathode in aqueous solutions. "
            "Active metals (Na, K) don't deposit — H₂ gas forms instead.\n"
            "Starter: 'During electrolysis of dilute H₂SO₄ with platinum electrodes, what forms at each electrode?'"
        )

    return ""
