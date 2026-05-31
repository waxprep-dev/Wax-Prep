import httpx
import tempfile
import os
from typing import Optional, Tuple
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings

NIGERIAN_VOICE_INSTRUCTION = """You are WaxPrep speaking to a Nigerian student. 
Speak in a warm, natural Nigerian English accent. 
Sound like an educated, friendly Nigerian teacher — not a robotic text-to-speech system. 
Speak at a natural pace, not too fast. 
When you emphasize a point, let that come through naturally in your voice.
Never sound like you are reading from a script."""

class VoiceGenerator:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self._voice_enabled = True
    
    async def generate_voice_response(
        self, 
        text: str,
        max_length: int = 500,
    ) -> Optional[bytes]:
        if not self._voice_enabled:
            return None
        
        if len(text) > max_length:
            text = self._trim_for_voice(text, max_length)
        
        text = self._prepare_text_for_speech(text)
        
        try:
            return await self._generate_with_groq_tts(text)
        except Exception as e:
            logger.warning(f"Groq TTS failed: {e}")
            return None
    
    async def _generate_with_groq_tts(self, text: str) -> Optional[bytes]:
        try:
            response = self.groq_client.audio.speech.create(
                model="playai-tts",
                voice="Celeste-PlayAI",
                input=text,
                response_format="mp3",
            )
            
            audio_bytes = b""
            for chunk in response.iter_bytes():
                audio_bytes += chunk
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Groq TTS generation failed: {e}")
            return None
    
    def _trim_for_voice(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        
        last_period = text[:max_length].rfind(".")
        if last_period > max_length * 0.6:
            return text[:last_period + 1]
        
        last_question = text[:max_length].rfind("?")
        if last_question > max_length * 0.6:
            return text[:last_question + 1]
        
        return text[:max_length] + "..."
    
    def _prepare_text_for_speech(self, text: str) -> str:
        text = text.replace("*", "")
        text = text.replace("_", "")
        text = text.replace("#", "")
        text = text.replace("→", "gives")
        text = text.replace("≤", "less than or equal to")
        text = text.replace("≥", "greater than or equal to")
        text = text.replace("²", " squared")
        text = text.replace("³", " cubed")
        text = text.replace("√", "square root of")
        text = text.replace("π", "pi")
        text = text.replace("%", " percent")
        text = text.replace("°", " degrees")
        
        import re
        text = re.sub(r'https?://\S+', '', text)
        
        text = text.replace("\n\n", ". ")
        text = text.replace("\n", ". ")
        
        return text.strip()
    
    def should_send_voice(
        self,
        student_preferences: dict,
        message_length: int,
        is_explanation: bool,
        student_sent_voice: bool,
    ) -> bool:
        if student_preferences.get("voice_preferred") is True:
            return True
        
        if student_preferences.get("voice_preferred") is False:
            return False
        
        if student_sent_voice:
            return True
        
        if is_explanation and message_length > 200 and message_length < 600:
            return True
        
        return False
