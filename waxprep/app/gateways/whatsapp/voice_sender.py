import httpx
import tempfile
import os
from typing import Optional
from loguru import logger
from waxprep.app.core.config import settings
from waxprep.app.core.exceptions import MessageSendError

WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"

class WhatsAppVoiceSender:
    def __init__(self):
        self.media_upload_url = f"{WHATSAPP_API_BASE}/{settings.whatsapp_phone_number_id}/media"
        self.messages_url = f"{WHATSAPP_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
        }
    
    async def send_voice_message(self, to: str, audio_bytes: bytes) -> bool:
        try:
            media_id = await self._upload_audio(audio_bytes)
            if not media_id:
                return False
            return await self._send_audio_message(to, media_id)
        except Exception as e:
            logger.error(f"Voice message send failed: {e}")
            return False
    
    async def _upload_audio(self, audio_bytes: bytes) -> Optional[str]:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(tmp_path, "rb") as audio_file:
                    response = await client.post(
                        self.media_upload_url,
                        headers=self.headers,
                        files={
                            "file": ("voice.mp3", audio_file, "audio/mpeg"),
                            "type": (None, "audio/mpeg"),
                            "messaging_product": (None, "whatsapp"),
                        }
                    )
                    response.raise_for_status()
                    return response.json().get("id")
        except Exception as e:
            logger.error(f"Audio upload failed: {e}")
            return None
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    async def _send_audio_message(self, to: str, media_id: str) -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "audio",
            "audio": {"id": media_id},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.messages_url,
                    json=payload,
                    headers={**self.headers, "Content-Type": "application/json"},
                )
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Audio message send failed: {e}")
                return False
