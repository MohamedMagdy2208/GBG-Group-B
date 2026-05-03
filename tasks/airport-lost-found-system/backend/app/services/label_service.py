from __future__ import annotations

from io import BytesIO
from urllib.parse import quote
from uuid import uuid4

from app.core.config import get_settings
from app.models import BarcodeLabel, FoundItem, User


class LabelService:
    def build_payload(self, label_code: str) -> str:
        base_url = get_settings().qr_label_base_url.rstrip("/")
        return f"{base_url}/staff/scan?code={quote(label_code)}"

    def create_found_item_label(self, item: FoundItem, created_by: User | None = None) -> BarcodeLabel:
        label = BarcodeLabel(
            label_code=f"LF-{uuid4().hex[:10].upper()}",
            entity_type="found_item",
            entity_id=item.id,
            created_by_staff_id=created_by.id if created_by else None,
            qr_payload="",
        )
        label.qr_payload = self.build_payload(label.label_code)
        return label

    def qr_svg(self, payload: str, label_code: str) -> str:
        try:
            import qrcode
            import qrcode.image.svg

            factory = qrcode.image.svg.SvgPathImage
            image = qrcode.make(payload, image_factory=factory, border=2)
            stream = BytesIO()
            image.save(stream)
            return stream.getvalue().decode("utf-8")
        except Exception:
            safe_payload = payload.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_code = label_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-label="QR label {safe_code}">
  <rect width="256" height="256" fill="#ffffff"/>
  <rect x="20" y="20" width="216" height="216" fill="none" stroke="#0f172a" stroke-width="8"/>
  <text x="128" y="116" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" fill="#0f172a">{safe_code}</text>
  <text x="128" y="146" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#334155">{safe_payload}</text>
</svg>"""


label_service = LabelService()
