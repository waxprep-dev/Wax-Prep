"""Physics subject intelligence — placeholder for curriculum-specific teaching context."""


def get_physics_intelligence(topic: str, class_level: str) -> str:
    """Return teaching intelligence context for physics topics.

    Args:
        topic: The physics topic being taught
        class_level: Student's class level (e.g., JSS1, SS1)

    Returns:
        Teaching context string or empty string if no specific intelligence available
    """
    topic_lower = topic.lower().replace(" ", "_")

    if "motion" in topic_lower or "kinematic" in topic_lower or "speed" in topic_lower or "velocity" in topic_lower:
        return (
            "MOTION / KINEMATICS TEACHING CONTEXT:\n"
            "WAEC Pattern: Usually 2-3 questions. Common: calculate final velocity, displacement, "
            "or time given initial conditions. SUVAT equations are essential.\n"
            "JAMB Pattern: 2-3 questions. Often tests understanding of graphs (velocity-time, displacement-time).\n"
            "Key equations: v = u + at, s = ut + ½at², v² = u² + 2as\n"
            "Common error: Students confuse scalars and vectors — speed vs velocity, distance vs displacement.\n"
            "Starter question: 'If a car starts from rest and accelerates at 2 m/s² for 5 seconds, "
            "how far does it travel? Walk me through your thinking.'"
        )

    if "force" in topic_lower or "newton" in topic_lower:
        return (
            "FORCES & NEWTON'S LAWS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Common: calculate resultant force, apply F=ma, "
            "or identify action-reaction pairs.\n"
            "JAMB Pattern: 2-3 questions. Conceptual questions about Newton's three laws are very common.\n"
            "Key: F = ma, Newton's 1st (inertia), 2nd (F=ma), 3rd (action-reaction)\n"
            "Common error: Students think force is needed to maintain motion (Aristotelian misconception).\n"
            "Starter: 'If you kick a ball in space (no friction), what happens to it after your foot leaves?'"
        )

    if "energy" in topic_lower or "work" in topic_lower or "power" in topic_lower:
        return (
            "ENERGY, WORK & POWER TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Often combined with mechanics. Conservation of energy problems common.\n"
            "JAMB Pattern: 2-3 questions. Efficiency calculations, kinetic vs potential energy conversions.\n"
            "Key: W = F×d, P = W/t, KE = ½mv², PE = mgh, Conservation: KE₁ + PE₁ = KE₂ + PE₂\n"
            "Common error: Confusing power (rate) with work (total). Forgetting g = 10 m/s² for WAEC/JAMB.\n"
            "Starter: 'A 2kg ball is dropped from 10m. How fast is it going just before it hits the ground?'"
        )

    if "electric" in topic_lower or "circuit" in topic_lower or "ohm" in topic_lower or "current" in topic_lower:
        return (
            "ELECTRICITY & CIRCUITS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2-3 questions. Circuit calculations with Ohm's Law, series/parallel resistors, "
            "domestic wiring.\n"
            "JAMB Pattern: 2-3 questions. Often conceptual — what happens to current when resistance changes?\n"
            "Key: V = IR, P = IV, series: R_total = R₁+R₂+R₃, parallel: 1/R_total = 1/R₁+1/R₂+1/R₃\n"
            "Common error: Adding parallel resistances directly instead of using reciprocal formula.\n"
            "Starter: 'Three 6-ohm resistors are connected in parallel. What is the total resistance?'"
        )

    if "wave" in topic_lower or "sound" in topic_lower or "light" in topic_lower:
        return (
            "WAVES, SOUND & LIGHT TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Wave equation v = fλ, echo calculations, refraction.\n"
            "JAMB Pattern: 2 questions. Electromagnetic spectrum properties, wave types (transverse/longitudinal).\n"
            "Key: v = fλ, echo: total distance = v×t/2 (divide by 2 for one-way distance)\n"
            "Common error: Forgetting to divide echo time by 2. Confusing frequency with amplitude.\n"
            "Starter: 'What is the difference between a longitudinal wave and a transverse wave? Give an example of each.'"
        )

    if "heat" in topic_lower or "temperature" in topic_lower or "therm" in topic_lower:
        return (
            "HEAT & THERMODYNAMICS TEACHING CONTEXT:\n"
            "WAEC Pattern: 2 questions. Specific heat capacity calculations, latent heat, thermal expansion.\n"
            "JAMB Pattern: 1-2 questions. Gas laws (Boyle's, Charles's, Pressure law).\n"
            "Key: Q = mcΔθ, Q = mL, Boyle's Law: P₁V₁ = P₂V₂, Charles's Law: V₁/T₁ = V₂/T₂\n"
            "Common error: Using Celsius instead of Kelvin in gas law calculations.\n"
            "Starter: 'Why does the Kelvin scale start at -273°C? What does that temperature represent?'"
        )

    return ""
