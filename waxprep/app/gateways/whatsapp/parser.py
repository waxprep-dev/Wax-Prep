from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from waxprep.app.gateways.normalizer import NormalizedMessage
from waxprep.app.core.constants import Platform


class WhatsAppParser:

    def parse_payload(self, payload: Dict[str, Any]) -> List[NormalizedMessage]:
        messages = []

        try:
            entry_list = payload.get("entry", [])
            for entry in entry_list:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    incoming_messages = value.get("messages", [])

                    for msg in incoming_messages:
                        normalized = self._normalize_message(msg, value)
                        if normalized:
                            messages.append(normalized)
        except Exception as e:
            logger.error(f"Error parsing WhatsApp payload: {e}")

        return messages

    def _normalize_message(self, msg: Dict[str, Any], value: Dict[str, Any]) -> Optional[NormalizedMessage]:
        try:
            msg_type = msg.get("type", "")
            platform_user_id = msg.get("from", "")
            platform_message_id = msg.get("id", "")
            timestamp_raw = msg.get("timestamp", "")

            try:
                timestamp = datetime.fromtimestamp(int(timestamp_raw))
            except (ValueError, TypeError):
                timestamp = datetime.now()

            content = ""
            media_url = None
            media_type = None
            is_voice = False

            if msg_type == "text":
                content = msg.get("text", {}).get("body", "")

            elif msg_type == "audio":
                is_voice = True
                content = msg.get("audio", {}).get("id", "")
                media_url = msg.get("audio", {}).get("id", "")
                media_type = "audio"
                content = "[VOICE_NOTE_TO_TRANSCRIBE]"

            elif msg_type == "image":
                content = msg.get("image", {}).get("caption", "[Image received]")
                media_url = msg.get("image", {}).get("id", "")
                media_type = "image"

            elif msg_type == "document":
                content = msg.get("document", {}).get("caption", "[Document received]")
                media_url = msg.get("document", {}).get("id", "")
                media_type = "document"

            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                interactive_type = interactive.get("type", "")
                if interactive_type == "button_reply":
                    content = interactive.get("button_reply", {}).get("title", "")
                elif interactive_type == "list_reply":
                    content = interactive.get("list_reply", {}).get("title", "")

            elif msg_type == "button":
                content = msg.get("button", {}).get("text", "")

            else:
                logger.debug(f"Unhandled WhatsApp message type: {msg_type}")
                return None

            if not content and not is_voice:
                return None

            return NormalizedMessage(
                platform=Platform.WHATSAPP,
                platform_user_id=platform_user_id,
                platform_message_id=platform_message_id,
                content=content,
                message_type=msg_type,
                timestamp=timestamp,
                raw_payload=msg,
                media_url=media_url,
                media_type=media_type,
                is_voice=is_voice,
                metadata={"value": value},
            )

        except Exception as e:
            logger.error(f"Error normalizing WhatsApp message: {e}")
            return None
