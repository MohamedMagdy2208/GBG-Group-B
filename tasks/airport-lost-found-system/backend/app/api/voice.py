from fastapi import APIRouter, Depends

from app.core.rate_limit import rate_limit
from app.schemas import VoiceTokenResponse
from app.services.speech_service import speech_service


router = APIRouter(prefix="/voice", tags=["voice"])


@router.post(
    "/token",
    response_model=VoiceTokenResponse,
    dependencies=[Depends(rate_limit("voice_token", 10, 60))],
)
async def voice_token() -> dict:
    return await speech_service.client_token()
