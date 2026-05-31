import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai
from waxprep.app.core.config import settings
from waxprep.app.core.exceptions import AIModelError, AIModelUnavailableError

BANNED_OPENERS = [
    "Certainly! ", "Of course! ", "Absolutely! ", "Sure! ", "Sure thing! ",
    "Great question! ", "That's a great question! ", "Excellent question! ",
    "Wonderful! ", "Fantastic! ", "Amazing! ",
    "I'm glad you asked! ", "I'm happy to help! ",
    "I'd be happy to ", "I'd be glad to ", "Allow me to ",
    "As an AI", "As WaxPrep, I", "I should note that I am",
]

BANNED_PHRASES = [
    "I'm glad you're back", "I'm so glad to see you",
    "I'm super excited", "You're absolutely right again",
    "I'm proud of you for that", "That's absolutely correct",
    "You've got this!", "Believe in yourself",
]

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
]

GROQ_FAST_MODELS = [
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

class WaxPrepAIEngine:
    def __init__(self):
        self._init_clients()
        self._groq_model_index = 0
        self._groq_fast_index = 0
        self._gemini_available = True
        self._request_count = 0

    def _init_clients(self):
        self._groq_keys = []
        for i in range(1, 6):
            key_attr = f"groq_api_key_{i}" if i > 1 else "groq_api_key"
            key = getattr(settings, key_attr, None)
            if key and key != "":
                self._groq_keys.append(key)

        if not self._groq_keys:
            raise ValueError("No Groq API keys configured")

        self._groq_clients = [Groq(api_key=k) for k in self._groq_keys]
        self._current_key_index = 0
        logger.info(f"WaxPrepAIEngine initialized with {len(self._groq_keys)} Groq keys")

        try:
            genai.configure(api_key=settings.gemini_api_key)
            self._gemini_model = genai.GenerativeModel(settings.gemini_model or "gemini-1.5-flash")
        except Exception:
            self._gemini_available = False

    def _get_groq_client(self) -> Groq:
        self._request_count += 1
        if self._request_count % 50 == 0:
            self._current_key_index = (self._current_key_index + 1) % len(self._groq_clients)
        return self._groq_clients[self._current_key_index]

    def _rotate_key(self):
        self._current_key_index = (self._current_key_index + 1) % len(self._groq_clients)
        logger.info(f"Rotated to Groq key index {self._current_key_index}")

    def _get_primary_model(self) -> str:
        return GROQ_MODELS[self._groq_model_index % len(GROQ_MODELS)]

    def _get_fast_model(self) -> str:
        return GROQ_FAST_MODELS[self._groq_fast_index % len(GROQ_FAST_MODELS)]

    async def generate_teaching_response_from_prompt(self, system_prompt: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        start = time.time()
        response_text = None
        model_used = None
        tokens_used = 0

        for attempt in range(len(self._groq_keys) * 2):
            try:
                client = self._get_groq_client()
                model = self._get_primary_model()
                all_messages = [{"role": "system", "content": system_prompt}] + messages
                response = client.chat.completions.create(model=model, messages=all_messages, max_tokens=1024, temperature=0.7)
                response_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
                model_used = model
                break
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str:
                    self._rotate_key()
                    await asyncio.sleep(1)
                elif "503" in error_str or "unavailable" in error_str:
                    self._groq_model_index += 1
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"Groq attempt {attempt + 1} failed: {e}")
                    self._rotate_key()

        if response_text is None and self._gemini_available:
            try:
                full_prompt = system_prompt + "\n\n"
                for msg in messages[:-1]:
                    role_label = "Student" if msg["role"] == "user" else "WaxPrep"
                    full_prompt += f"{role_label}: {msg['content']}\n"
                if messages:
                    full_prompt += f"\nStudent: {messages[-1]['content']}\n\nWaxPrep:"
                response = self._gemini_model.generate_content(full_prompt)
                response_text = response.text
                model_used = "gemini-fallback"
            except Exception as e:
                logger.error(f"Gemini fallback failed: {e}")

        if response_text is None:
            response_text = self._get_fallback_response()
            model_used = "hardcoded-fallback"

        processing_time = int((time.time() - start) * 1000)
        response_text = self._post_process_response(response_text)

        return {"response": response_text, "model_used": model_used, "tokens_used": tokens_used, "processing_time_ms": processing_time}

    async def classify_intent(self, message: str, recent_context: str = "") -> str:
        from waxprep.app.ai.prompts import build_intent_classification_prompt
        prompt = build_intent_classification_prompt(message, recent_context[:150])
        for attempt in range(len(self._groq_keys)):
            try:
                client = self._get_groq_client()
                model = self._get_fast_model()
                response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=20, temperature=0.1)
                intent_raw = response.choices[0].message.content.strip().upper()
                valid_intents = ["GREETING", "TEACHING_REQUEST", "CLARIFICATION_REQUEST", "EXAMPLE_REQUEST", "ASSESSMENT_RESPONSE", "PROGRESS_CHECK", "EMOTIONAL_EXPRESSION", "CASUAL_CONVERSATION", "TOPIC_CHANGE", "CONFUSION", "META_QUESTION", "PLATFORM_COMMAND", "UNKNOWN"]
                for valid in valid_intents:
                    if valid in intent_raw: return valid.lower()
                return "unknown"
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str:
                    self._rotate_key()
                    self._groq_fast_index += 1
                    await asyncio.sleep(0.5)
                else:
                    logger.warning(f"Intent classification attempt {attempt + 1} failed: {e}")
                    self._rotate_key()
        return "unknown"

    async def generate_from_single_prompt(self, prompt: str) -> str:
        for attempt in range(len(self._groq_keys)):
            try:
                client = self._get_groq_client()
                response = client.chat.completions.create(model=self._get_primary_model(), messages=[{"role": "user", "content": prompt}], max_tokens=400, temperature=0.6)
                return self._post_process_response(response.choices[0].message.content)
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str:
                    self._rotate_key()
                    await asyncio.sleep(1)
                else:
                    logger.warning(f"Single prompt attempt {attempt + 1} failed: {e}")
                    self._rotate_key()
        if self._gemini_available:
            try:
                response = self._gemini_model.generate_content(prompt)
                return self._post_process_response(response.text)
            except Exception: pass
        return self._get_fallback_response()

    def _post_process_response(self, response: str) -> str:
        if not response: return self._get_fallback_response()
        response = response.strip()
        for opener in BANNED_OPENERS:
            if response.startswith(opener):
                response = response[len(opener):]
                if response: response = response[0].upper() + response[1:]
        for phrase in BANNED_PHRASES:
            response = response.replace(phrase, "")
        response = response.strip()
        while "  " in response: response = response.replace("  ", " ")
        while "\n\n\n" in response: response = response.replace("\n\n\n", "\n\n")
        if len(response) > 4000:
            last_period = response[:3900].rfind(".")
            if last_period > 3000: response = response[:last_period + 1]
        if response and response[0].islower(): response = response[0].upper() + response[1:]
        return response.strip()

    def _get_fallback_response(self) -> str:
        return "I'm having a quick technical moment — try your message again."
