"""Bilingual notification templates for passenger updates.

Each template returns (subject, body) for the requested language.
Keep templates short and never include the full found-item description
or any unique identifiers — passenger should still authenticate to claim.
"""
from __future__ import annotations

from typing import Any


def _normalise_language(language: str | None) -> str:
    if (language or "").lower().startswith("ar"):
        return "ar"
    return "en"


def render_match_alert(report_code: str, confidence_level: str, language: str | None = None) -> tuple[str, str]:
    lang = _normalise_language(language)
    if lang == "ar":
        subject = f"تحديث على بلاغك المفقود {report_code}"
        body = (
            f"سلام،\n\n"
            f"عثرنا على غرض مطابق محتمل لبلاغك {report_code}. "
            f"درجة الثقة: {confidence_level}.\n"
            f"يرجى مراجعة طاقم خدمة المطار لإكمال خطوات التحقق وإثبات الملكية.\n\n"
            f"شكراً لاستخدام خدمة المفقودات بالمطار."
        )
        return subject, body
    subject = f"Update on your lost-item report {report_code}"
    body = (
        f"Hello,\n\n"
        f"We may have found an item matching your report {report_code}. "
        f"Confidence: {confidence_level}.\n"
        f"Please contact airport lost & found staff to complete identity and ownership verification.\n\n"
        f"Thank you for using the airport lost & found service."
    )
    return subject, body


def render_release_confirmation(report_code: str, language: str | None = None) -> tuple[str, str]:
    lang = _normalise_language(language)
    if lang == "ar":
        return (
            f"تم تسليم غرضك ({report_code})",
            "تم تسليم الغرض المسجل في بلاغك بنجاح. شكراً لاختيارك خدمة المفقودات بالمطار.",
        )
    return (
        f"Your item has been released ({report_code})",
        "The item registered against your report has been released. Thank you for using the airport lost & found service.",
    )


def render_claim_blocked(report_code: str, language: str | None = None) -> tuple[str, str]:
    lang = _normalise_language(language)
    if lang == "ar":
        return (
            f"بلاغك {report_code} يحتاج تحقق إضافي",
            "نحتاج تحقق إضافي قبل تسليم الغرض. يرجى مراجعة طاقم الأمن بالمطار.",
        )
    return (
        f"Additional verification needed for {report_code}",
        "We need extra verification before releasing the item. Please contact airport security staff.",
    )


def select_template(event_type: str, payload: dict[str, Any], language: str | None) -> tuple[str, str] | None:
    report_code = str(payload.get("report_code") or "")
    if event_type == "match_candidate.upserted":
        if (payload.get("confidence_level") or "").lower() != "high":
            return None
        if not report_code:
            return None
        return render_match_alert(report_code, payload.get("confidence_level", "high"), language)
    if event_type == "item.released":
        if not report_code:
            return None
        return render_release_confirmation(report_code, language)
    if event_type == "claim.blocked":
        if not report_code:
            return None
        return render_claim_blocked(report_code, language)
    return None
