import asyncio
from pathlib import Path
from typing import Any

from app.core.config import get_settings


class AzureVisionService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def analyze_uploaded_item_image(self, image_url: str) -> dict[str, Any]:
        if self.settings.use_azure_services and self.settings.azure_ai_vision_endpoint and self.settings.azure_ai_vision_key:
            from azure.ai.vision.imageanalysis import ImageAnalysisClient
            from azure.ai.vision.imageanalysis.models import VisualFeatures
            from azure.core.credentials import AzureKeyCredential

            from app.services.azure_blob_service import azure_blob_service

            image_url = await azure_blob_service.generate_secure_url_from_blob_url(image_url)

            client = ImageAnalysisClient(
                endpoint=self.settings.azure_ai_vision_endpoint,
                credential=AzureKeyCredential(self.settings.azure_ai_vision_key),
            )
            result = await asyncio.to_thread(
                client.analyze_from_url,
                image_url=image_url,
                visual_features=[
                    VisualFeatures.CAPTION,
                    VisualFeatures.TAGS,
                    VisualFeatures.OBJECTS,
                    VisualFeatures.READ,
                ],
            )
            tags = [{"name": tag.name, "confidence": tag.confidence} for tag in (result.tags.list or [])] if result.tags else []
            objects = [
                {"name": obj.tags[0].name if obj.tags else "object", "confidence": obj.tags[0].confidence if obj.tags else 0}
                for obj in (result.objects.list or [])
            ] if result.objects else []
            ocr_text = "\n".join(
                line.text
                for block in (result.read.blocks or []) if result.read
                for line in block.lines
            )
            return {
                "caption": result.caption.text if result.caption else "",
                "tags": tags,
                "ocr_text": ocr_text,
                "objects": objects,
            }
        filename = Path(image_url).name.lower()
        keywords = [
            "phone", "iphone", "smartphone", "bag", "backpack", "suitcase",
            "passport", "wallet", "laptop", "macbook", "keys", "keychain",
            "watch", "headphones", "airpods", "camera", "tablet", "ipad",
            "umbrella", "jacket", "book",
        ]
        guessed_tags = []
        seen: set[str] = set()
        for word in keywords:
            if word in filename and word not in seen:
                guessed_tags.append({"name": word, "confidence": 0.82})
                seen.add(word)
        if not guessed_tags:
            guessed_tags = [{"name": "personal item", "confidence": 0.55}]
        return {
            "caption": "Uploaded item image, analyzed by local mock vision.",
            "tags": guessed_tags,
            "ocr_text": "",
            "objects": list(guessed_tags),
        }


azure_vision_service = AzureVisionService()
