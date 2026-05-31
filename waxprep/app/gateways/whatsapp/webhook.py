from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
import hmac
import hashlib
from loguru import logger
from waxprep.app.core.config import settings
from waxprep.app.core.exceptions import WebhookVerificationError
from waxprep.app.gateways.whatsapp.parser import WhatsAppParser
from waxprep.app.core.constants import Platform

router = APIRouter()
parser = WhatsAppParser()


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)
    logger.warning(f"WhatsApp webhook verification failed. Mode: {hub_mode}, Token: {hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook_receive(request: Request):
    body_bytes = await request.body()

    if not _verify_whatsapp_signature(request, body_bytes):
        logger.warning("WhatsApp webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    logger.debug(f"WhatsApp webhook received: {payload}")

    from waxprep.app.api.routes.webhooks import process_whatsapp_payload
    import asyncio
    asyncio.create_task(process_whatsapp_payload(payload))

    return {"status": "ok"}


def _verify_whatsapp_signature(request: Request, body_bytes: bytes) -> bool:
    if settings.app_env == "development":
        return True

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.whatsapp_app_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
