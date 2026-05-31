import httpx
import tempfile
import os
from typing import Optional
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings

class VoiceTranscriber:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.whatsapp_headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}"
        }

    async def transcribe_whatsapp_audio(self, media_id: str) -> Optional[str]:
        try:
            audio_bytes = await self._download_whatsapp_audio(media_id)
            if not audio_bytes:
                return None
            return await self._transcribe_bytes(audio_bytes, filename="audio.ogg")
        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            return None

    async def _download_whatsapp_audio(self, media_id: str) -> Optional[bytes]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                media_url_response = await client.get(
                    f"https://graph.facebook.com/v21.0/{media_id}",
                    headers=self.whatsapp_headers,
                )
                media_url_response.raise_for_status()
                media_url = media_url_response.json().get("url")
                if not media_url:
                    return None
                audio_response = await client.get(media_url, headers=self.whatsapp_headers)
                audio_response.raise_for_status()
                return audio_response.content
            except Exception as e:
                logger.error(f"Failed to download WhatsApp audio: {e}")
                return None

    async def _transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.ogg") -> Optional[str]:
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=(filename, audio_file, "audio/ogg"),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                    language="en",
                )
            return transcription.strip() if transcription else None
        except Exception as e:
            logger.warning(f"Groq Whisper transcription failed: {e}")
            return None
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
