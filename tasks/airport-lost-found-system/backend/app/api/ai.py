from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.rbac import require_staff
from app.models import User
from app.schemas import AITextRequest, EmbeddingResponse, ImageAnalysisRequest, ImageAnalysisResponse
from app.services.azure_openai_service import azure_openai_service
from app.services.azure_vision_service import azure_vision_service


router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(rate_limit("ai", get_settings().rate_limit_ai_per_minute, 60))])


@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(payload: ImageAnalysisRequest, _: User = Depends(require_staff)) -> dict:
    return await azure_vision_service.analyze_uploaded_item_image(payload.image_url)


@router.post("/extract-item-attributes")
async def extract_item_attributes(payload: AITextRequest, _: User = Depends(require_staff)) -> dict:
    return await azure_openai_service.extract_structured_attributes(payload.text)


@router.post("/generate-embedding", response_model=EmbeddingResponse)
async def generate_embedding(payload: AITextRequest, _: User = Depends(require_staff)) -> dict:
    vector_id, embedding = await azure_openai_service.generate_embedding(payload.text)
    return {"vector_id": vector_id, "embedding": embedding}


@router.post("/summarize-match")
async def summarize_match(payload: dict, _: User = Depends(require_staff)) -> dict:
    summary = await azure_openai_service.summarize_match_evidence(
        payload.get("lost_text", ""),
        payload.get("found_text", ""),
        payload.get("score_breakdown", {}),
    )
    return {"summary": summary}
