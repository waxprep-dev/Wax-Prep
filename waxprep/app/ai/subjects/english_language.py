"""English Language subject intelligence — placeholder for curriculum-specific teaching context."""


def get_english_language_intelligence(topic: str, class_level: str) -> str:
    """Return teaching intelligence context for English language topics.

    Args:
        topic: The English topic being taught
        class_level: Student's class level (e.g., JSS1, SS1)

    Returns:
        Teaching context string or empty string if no specific intelligence available
    """
    topic_lower = topic.lower().replace(" ", "_")

    if "comprehension" in topic_lower or "reading" in topic_lower or "passage" in topic_lower:
        return (
            "COMPREHENSION SKILLS TEACHING CONTEXT:\n"
            "WAEC Pattern: 1 passage with 10-15 questions. Tests literal, inferential, and evaluative understanding.\n"
            "JAMB Pattern: 1-2 passages with 10 questions each. Time-pressed — students must read efficiently.\n"
            "Key strategies: Skim for main idea first, read questions before detailed re-read, "
            "underline key phrases, eliminate obviously wrong options.\n"
            "Common error: Selecting answers that use exact words from passage (often distractors) "
            "instead of paraphrased correct answers.\n"
            "Starter: 'Read the first and last paragraph of any passage. What is the author mainly trying to do?'"
        )

    if "grammar" in topic_lower or "tense" in topic_lower or "verb" in topic_lower:
        return (
            "GRAMMAR & TENSES TEACHING CONTEXT:\n"
            "WAEC Pattern: 10-15 objective questions. Error spotting, sentence correction, gap filling.\n"
            "JAMB Pattern: 10 questions. Often tests subtle distinctions (present perfect vs past simple).\n"
            "Key tenses: Present simple (habits), Present continuous (now), Past simple (completed), "
            "Present perfect (past → present link), Future (will vs going to).\n"
            "Common error: Using present continuous for permanent situations ('I am living in Lagos' vs 'I live in Lagos').\n"
            "Starter: 'What is the difference between: I have lived here for 5 years / I lived here for 5 years?'"
        )

    if "essay" in topic_lower or "writing" in topic_lower or "composition" in topic_lower:
        return (
            "ESSAY WRITING TEACHING CONTEXT:\n"
            "WAEC Pattern: 1 essay (450 words minimum). Types: narrative, descriptive, argumentative, expository, article.\n"
            "JAMB Pattern: Comprehension and summary rather than full essay, but good writing matters in all sections.\n"
            "Key structure: Introduction (thesis + outline), Body (2-3 paragraphs with topic sentences), "
            "Conclusion (restate + final thought).\n"
            "Common error: No clear thesis statement, paragraphs without topic sentences, "
            "conclusion that introduces new points.\n"
            "Starter: 'Give me a thesis statement for: \"Social media does more harm than good to Nigerian youth.\"'"
        )

    if "summary" in topic_lower:
        return (
            "SUMMARY WRITING TEACHING CONTEXT:\n"
            "WAEC Pattern: Summarize a passage in a specified number of sentences (usually 100-150 words).\n"
            "JAMB Pattern: Similar summary exercises, often combined with comprehension.\n"
            "Key: Identify main points only, use your own words, stick to word limit, "
            "do not include examples or illustrations from original.\n"
            "Common error: Copying phrases directly from passage, including minor details, "
            "exceeding word count, adding personal opinions.\n"
            "Starter: 'If a passage has 5 paragraphs, how many main points should your summary ideally have? Why?'"
        )

    if "figure" in topic_lower or "speech" in topic_lower or "literary" in topic_lower or "idiom" in topic_lower:
        return (
            "FIGURES OF SPEECH TEACHING CONTEXT:\n"
            "WAEC Pattern: 5-8 questions identifying/simile, metaphor, personification, irony, hyperbole.\n"
            "JAMB Pattern: 5-6 questions. Often in context — identify the figure used in a given sentence.\n"
            "Key: Simile (like/as), Metaphor (is/was), Personification (human traits to objects), "
            "Hyperbole (exaggeration), Irony (opposite of literal meaning), Alliteration (repeated initial sounds).\n"
            "Common error: Confusing simile with metaphor ('like' or 'as' = simile). "
            "Missing irony because it requires reading between the lines.\n"
            "Starter: '\"The classroom was an oven.\" — What figure of speech is this? How do you know?'"
        )

    if "vocabulary" in topic_lower or "word" in topic_lower or "antonym" in topic_lower or "synonym" in topic_lower:
        return (
            "VOCABULARY, SYNONYMS & ANTONYMS TEACHING CONTEXT:\n"
            "WAEC Pattern: 5-10 questions. Word closest in meaning, opposite in meaning, word formation.\n"
            "JAMB Pattern: 5-8 questions. Often tests words in context rather than isolated definitions.\n"
            "Key strategy: Read the sentence context — the surrounding words give clues. "
            "Break words into roots/prefixes/suffixes.\n"
            "Common error: Choosing answers based on partial word recognition without reading context.\n"
            "Starter: 'What is the nearest in meaning to ABHOR in this sentence: \"She abhors dishonesty in any form\"?'"
        )

    return ""
