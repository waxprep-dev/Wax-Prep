from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from waxprep.app.gateways.normalizer import NormalizedMessage
from waxprep.app.core.constants import Platform


class TelegramParser:

    def parse_update(self, update: Dict[str, Any]) -> Optional[NormalizedMessage]:
        try:
            message = update.get("message") or update.get("edited_message")
            if not message:
                return None

            from_user = message.get("from", {})
            platform_user_id = str(from_user.get("id", ""))
            platform_message_id = str(message.get("message_id", ""))

            timestamp_raw = message.get("date", "")
            try:
                timestamp = datetime.fromtimestamp(int(timestamp_raw))
            except (ValueError, TypeError):
                timestamp = datetime.now()

            content = ""
            message_type = "text"
            is_voice = False
            media_url = None

            if "text" in message:
                content = message["text"]
                message_type = "text"

            elif "voice" in message:
                is_voice = True
                message_type = "voice"
                content = "[Voice message — I can see you sent a voice note! For now, type out what you want to say and I'll be right with you. Voice support is coming soon.]"

            elif "photo" in message:
                photos = message["photo"]
                best_photo = max(photos, key=lambda p: p.get("file_size", 0))
                media_url = best_photo.get("file_id", "")
                content = message.get("caption", "[Photo received]")
                message_type = "photo"

            elif "document" in message:
                content = message.get("caption", "[Document received]")
                message_type = "document"

            elif "sticker" in message:
                content = "[Sticker received 😄]"
                message_type = "sticker"

            else:
                return None

            if not content:
                return None

            return NormalizedMessage(
                platform=Platform.TELEGRAM,
                platform_user_id=platform_user_id,
                platform_message_id=f"tg_{platform_message_id}",
                content=content,
                message_type=message_type,
                timestamp=timestamp,
                raw_payload=update,
                media_url=media_url,
                is_voice=is_voice,
                metadata={"from_user": from_user},
            )

        except Exception as e:
            logger.error(f"Error parsing Telegram update: {e}")
            return None
