from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
import hmac
import hashlib
from loguru import logger
from waxprep.app.core.config import settings
from waxprep.app.gateways.whatsapp.parser import WhatsAppParser
from waxprep.app.router.dispatcher import dispatch_message

router = APIRouter()
whatsapp_parser = WhatsAppParser()


@router.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified")
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_receive(request: Request, background_tasks: BackgroundTasks):
    body_bytes = await request.body()

    if settings.app_env != "development":
        if not _verify_whatsapp_signature(request, body_bytes):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    messages = whatsapp_parser.parse_payload(payload)
    for normalized_message in messages:
        background_tasks.add_task(dispatch_message, normalized_message)

    return {"status": "ok"}


@router.post("/webhook/telegram")
async def telegram_receive(request: Request, background_tasks: BackgroundTasks):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != settings.telegram_webhook_secret and settings.app_env != "development":
        raise HTTPException(status_code=401, detail="Invalid secret")

    payload = await request.json()

    from waxprep.app.gateways.telegram.parser import TelegramParser
    telegram_parser = TelegramParser()
    normalized_message = telegram_parser.parse_update(payload)

    if normalized_message:
        background_tasks.add_task(dispatch_message, normalized_message)

    return {"status": "ok"}


async def process_whatsapp_payload(payload: dict):
    messages = whatsapp_parser.parse_payload(payload)
    for normalized_message in messages:
        await dispatch_message(normalized_message)


def _verify_whatsapp_signature(request: Request, body_bytes: bytes) -> bool:
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.whatsapp_app_secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
