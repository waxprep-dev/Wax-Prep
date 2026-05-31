import json
from typing import Dict, Any, Optional, List
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings

YORUBA_CONCEPTS = {
    "photosynthesis": "Ifunpa Oorun-Edekun (ilana ti eweko fi n se ounje won pelu imole oorun, omi, ati afefe CO2)",
    "mitosis": "Ipinya Seli — nigbati seli kan pin di meji to jora",
    "atom": "Atomi — apakan ti o kere julo ti oro eyikeyi",
    "democracy": "Ijoba-Eniyan — ijoba ti eniyan yan, ti eniyan se, fun anfaani eniyan",
    "fraction": "Ida — apakan ti nkan kan. Bi apere: idaji (1/2) tumo si pe oun kan pin si meji",
    "gravity": "Ipa aarin ile — ipa ti o fa ohun gbogbo sori ile",
    "enzyme": "Emi-sile — nkan pataki ti ara wa n se lati ran ise kemi lo",
    "chromosome": "Kromo-som — igo jiini ti o wa laarin arin seli",
}

IGBO_CONCEPTS = {
    "photosynthesis": "Ihe a na-eji ihe anyanwu meputa nri (anughi anwu di ka anwu na-eme n'ime leaves)",
    "mitosis": "Nguko cell - mgbe cell otu kewaa abuo",
    "atom": "Atom - obere ihe kacha nta nke ihe obula",
    "democracy": "Ochichi nke ndi mmadu - ulo oru ochichi ndi mmadu hooro",
    "fraction": "Odikwa akuku - akuku ihe. Omaatutu: okara (1/2) putara ihe otu kewara abuo",
    "gravity": "Ike mmiri ala - ihe na-adoko ihe niile ala",
    "enzyme": "Enzyme - ihe oru di n'ime ahu na-enyere oru chemical aka",
}

HAUSA_CONCEPTS = {
    "photosynthesis": "Hotunar Rana (tsarin da tsire-tsire ke yin abinci ta hanyar amfani da hasken rana, ruwa, da gas CO2)",
    "mitosis": "Raba sel - lokacin da sel guda daya ya raba zuwa biyu masu kama da juna",
    "atom": "Atom - dan abu mafi kankanta na duk wani abu",
    "democracy": "Dimokiradiyya - tsarin mulki da jama'a ke zaba, jama'a ke aiwatarwa",
    "fraction": "Kaso - bangare na abu. Misali: rabin (1/2) yana nufin abu daya ya rabu biyu",
    "gravity": "Nauyi - karfi da ke jan abubuwa duk zuwa kasa",
    "enzyme": "Enzyme - abin da jikin dan Adam ke yin don taimakawa ayyukan sinadarai",
}

LANGUAGE_BRIDGE_PROMPT = """You are WaxPrep, an AI teacher for Nigerian students. A student has requested an explanation in {language}.

The concept to explain: {concept}
Subject: {subject}
Class level: {class_level}

Provide a brief bridge explanation in {language} that helps the student understand this concept in their mother tongue. Then provide the full explanation in English.

Important rules:
1. Never invent words for scientific terms — use the English term with a description in the local language
2. Never sacrifice accuracy for language preference
3. After the mother-tongue bridge, say "In English:" and give the complete proper explanation
4. This bridge helps students understand English scientific terms — it is not a replacement for English learning

Explanation:"""

class LanguageBridge:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.concept_dictionaries = {
            "yoruba": YORUBA_CONCEPTS,
            "igbo": IGBO_CONCEPTS,
            "hausa": HAUSA_CONCEPTS,
        }
    
    def detect_language_request(self, message: str) -> Optional[str]:
        message_lower = message.lower()
        yoruba_signals = ["explain in yoruba", "yoruba", "fi yoruba han mi", "se ni yoruba"]
        igbo_signals = ["explain in igbo", "igbo", "koo ya igbo", "explain igbo"]
        hausa_signals = ["explain in hausa", "hausa", "bayyana a hausa", "fassara hausa"]
        pidgin_signals = ["explain for pidgin", "pidgin english", "use pidgin", "for pidgin"]
        for signal in yoruba_signals:
            if signal in message_lower: return "yoruba"
        for signal in igbo_signals:
            if signal in message_lower: return "igbo"
        for signal in hausa_signals:
            if signal in message_lower: return "hausa"
        for signal in pidgin_signals:
            if signal in message_lower: return "pidgin"
        return None
    
    async def provide_language_bridge(self, concept, language, subject, class_level) -> str:
        if language == "pidgin":
            return await self._generate_pidgin_explanation(concept, subject, class_level)
        predefined = self.concept_dictionaries.get(language, {})
        concept_lower = concept.lower()
        for key, translation in predefined.items():
            if key in concept_lower or concept_lower in key:
                prefix = f"*{language.capitalize()} Bridge:* {translation}\n\n*In English:*\n"
                full_explanation = await self._generate_full_english(concept, subject, class_level)
                return prefix + full_explanation
        return await self._generate_ai_bridge(concept, language, subject, class_level)
    
    async def _generate_ai_bridge(self, concept, language, subject, class_level) -> str:
        try:
            prompt = LANGUAGE_BRIDGE_PROMPT.format(concept=concept, language=language.capitalize(), subject=subject, class_level=class_level)
            response = self.groq_client.chat.completions.create(model=settings.groq_primary_model, messages=[{"role": "user", "content": prompt}], max_tokens=400, temperature=0.5)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Language bridge failed: {e}")
            return f"I'll explain {concept} in English:\n\n" + await self._generate_full_english(concept, subject, class_level)
    
    async def _generate_pidgin_explanation(self, concept, subject, class_level) -> str:
        try:
            prompt = f"Explain this concept in Nigerian Pidgin English for a student:\n\nConcept: {concept}\nSubject: {subject}\nClass level: {class_level}\n\nUse natural Nigerian Pidgin. After the Pidgin explanation, give the proper English explanation so they learn both. Pidgin explanation first, then 'Now properly in English:', then the full explanation:"
            response = self.groq_client.chat.completions.create(model=settings.groq_primary_model, messages=[{"role": "user", "content": prompt}], max_tokens=350, temperature=0.6)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Pidgin failed: {e}")
            return f"Make I explain this {concept} thing for you in English..."
    
    async def _generate_full_english(self, concept, subject, class_level) -> str:
        try:
            prompt = f"Explain {concept} ({subject}, {class_level}) in clear, simple English in 2-3 sentences:"
            response = self.groq_client.chat.completions.create(model=settings.groq_fast_model, messages=[{"role": "user", "content": prompt}], max_tokens=150, temperature=0.5)
            return response.choices[0].message.content.strip()
        except Exception:
            return f"{concept} is an important concept in {subject}."
