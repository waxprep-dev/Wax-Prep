import httpx
from typing import Optional, List, Dict, Any
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from waxprep.app.core.config import settings
from waxprep.app.core.exceptions import MessageSendError


WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppSender:

    def __init__(self):
        self.base_url = f"{WHATSAPP_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_text(self, to: str, text: str) -> Dict[str, Any]:
        if len(text) > 4096:
            parts = self._split_message(text)
            results = []
            for part in parts:
                result = await self._send_text_single(to, part)
                results.append(result)
            return results[-1]
        return await self._send_text_single(to, text)

    async def _send_text_single(self, to: str, text: str) -> Dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.debug(f"WhatsApp message sent to {to}: {result}")
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"WhatsApp send failed: {e.response.status_code} — {e.response.text}")
                raise MessageSendError(f"WhatsApp API error: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.error(f"WhatsApp send timeout for {to}")
                raise MessageSendError("WhatsApp send timeout")

    async def send_reaction(self, to: str, message_id: str, emoji: str) -> Dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Failed to send reaction: {e}")
                return {}

    async def mark_as_read(self, message_id: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=self.headers)
                response.raise_for_status()
            except Exception as e:
                logger.warning(f"Failed to mark as read: {e}")

    def _split_message(self, text: str, max_length: int = 4000) -> List[str]:
        if len(text) <= max_length:
            return [text]

        parts = []
        paragraphs = text.split("\n\n")
        current_part = ""

        for paragraph in paragraphs:
            if len(current_part) + len(paragraph) + 2 <= max_length:
                current_part += paragraph + "\n\n"
            else:
                if current_part:
                    parts.append(current_part.strip())
                if len(paragraph) > max_length:
                    sentences = paragraph.split(". ")
                    current_part = ""
                    for sentence in sentences:
                        if len(current_part) + len(sentence) + 2 <= max_length:
                            current_part += sentence + ". "
                        else:
                            if current_part:
                                parts.append(current_part.strip())
                            current_part = sentence + ". "
                else:
                    current_part = paragraph + "\n\n"

        if current_part:
            parts.append(current_part.strip())

        return parts if parts else [text[:max_length]]
