import httpx
from typing import Dict, Any, Optional, List
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from waxprep.app.core.config import settings
from waxprep.app.core.exceptions import MessageSendError


TELEGRAM_API_BASE = f"https://api.telegram.org/bot"


class TelegramSender:

    def __init__(self):
        self.base_url = f"{TELEGRAM_API_BASE}{settings.telegram_bot_token}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_text(self, chat_id: str, text: str) -> Dict[str, Any]:
        if len(text) > 4096:
            parts = self._split_message(text)
            results = []
            for part in parts:
                result = await self._send_single(chat_id, part)
                results.append(result)
            return results[-1]
        return await self._send_single(chat_id, text)

    async def _send_single(self, chat_id: str, text: str) -> Dict[str, Any]:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    payload_plain = {"chat_id": chat_id, "text": text}
                    response = await client.post(f"{self.base_url}/sendMessage", json=payload_plain)
                    response.raise_for_status()
                    return response.json()
                logger.error(f"Telegram send failed: {e.response.status_code}")
                raise MessageSendError(f"Telegram API error: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.error(f"Telegram send timeout for {chat_id}")
                raise MessageSendError("Telegram send timeout")

    async def send_typing_action(self, chat_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.base_url}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                )
        except Exception:
            pass

    def _split_message(self, text: str, max_length: int = 4000) -> List[str]:
        if len(text) <= max_length:
            return [text]

        parts = []
        while len(text) > max_length:
            split_at = text[:max_length].rfind("\n\n")
            if split_at == -1:
                split_at = text[:max_length].rfind(". ")
            if split_at == -1:
                split_at = max_length

            parts.append(text[:split_at].strip())
            text = text[split_at:].strip()

        if text:
            parts.append(text)

        return parts
