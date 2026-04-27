from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class SpeechService:
    async def client_token(self) -> dict:
        settings = get_settings()
        base = {
            "provider": settings.voice_provider,
            "enabled": settings.voice_features_enabled,
            "voice_en": settings.azure_speech_voice_en,
            "voice_ar": settings.azure_speech_voice_ar,
        }
        if not settings.voice_features_enabled:
            return base | {"provider": "disabled"}
        if settings.voice_provider != "azure" or not settings.azure_speech_key or not settings.azure_speech_region:
            return base | {"provider": "browser"}

        endpoint = settings.azure_speech_endpoint or f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com"
        token_url = f"{endpoint.rstrip('/')}/sts/v1.0/issueToken"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    token_url,
                    headers={"Ocp-Apim-Subscription-Key": settings.azure_speech_key},
                )
                response.raise_for_status()
                return base | {
                    "provider": "azure",
                    "token": response.text,
                    "region": settings.azure_speech_region,
                    "endpoint": endpoint,
                    "expires_in_seconds": 540,
                }
        except Exception:
            logger.exception("Azure Speech token request failed", extra={"event": "speech_token_failed"})
            return base | {"provider": "browser"}


speech_service = SpeechService()
