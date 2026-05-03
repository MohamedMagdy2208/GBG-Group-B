import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.utils import enrich_lost_report, invalidate_operational_caches, run_matching_for_lost_report
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import mask_phone
from app.models import ChatMessage, ChatRole, ChatSession, LostReport
from app.schemas import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSubmitLostReportRequest,
    ChatVerifyReportRequest,
    ChatVoiceMessageRequest,
    LostReportRead,
)
from app.services.azure_openai_service import azure_openai_service
from app.services.cache_service import cache_service


router = APIRouter(prefix="/chat/sessions", tags=["chat"], dependencies=[Depends(rate_limit("chat", get_settings().rate_limit_public_per_minute, 60))])


@router.post("", response_model=ChatSessionRead)
def create_session(payload: ChatSessionCreate | None = None, db: Session = Depends(get_db)) -> ChatSession:
    language = _normalize_language(payload.language if payload else "en")
    session = ChatSession(language=language, voice_enabled=bool(payload.voice_enabled) if payload else False)
    db.add(session)
    db.commit()
    db.refresh(session)
    greeting = ChatMessage(
        session_id=session.id,
        role=ChatRole.assistant,
        message_text=_text(language, "greeting"),
        structured_payload_json={"suggested_actions": ["Report lost item", "Check report status"]},
    )
    db.add(greeting)
    db.commit()
    return session


@router.get("/{session_id}/messages", response_model=list[ChatMessageRead])
def list_messages(session_id: int, db: Session = Depends(get_db)) -> list[ChatMessage]:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return session.messages


@router.post("/{session_id}/messages", response_model=ChatResponse)
async def add_message(
    session_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return await _handle_message(session, payload.message_text, db, language=payload.language)


@router.post("/{session_id}/voice-message", response_model=ChatResponse)
async def add_voice_message(
    session_id: int,
    payload: ChatVoiceMessageRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    session.voice_enabled = True
    return await _handle_message(
        session,
        payload.transcript,
        db,
        language=payload.language,
        user_payload={"voice": True, "provider": payload.provider, "confidence": payload.confidence},
    )


async def _handle_message(
    session: ChatSession,
    message_text: str,
    db: Session,
    language: str | None = None,
    user_payload: dict[str, Any] | None = None,
) -> ChatResponse:
    language = _normalize_language(language or session.language)
    session.language = language
    user_message = ChatMessage(
        session_id=session.id,
        role=ChatRole.user,
        message_text=message_text,
        structured_payload_json=user_payload or {},
    )
    db.add(user_message)

    text = message_text.strip()
    if _looks_like_status_request(text):
        session.current_state = "awaiting_status_verification"
        reply = _text(language, "status_prompt")
        actions = ["Verify report"]
    else:
        session.current_state = "collecting_lost_report"
        session.collected_data_json = _merge_chat_data(session.collected_data_json or {}, text)
        questions = await azure_openai_service.generate_passenger_follow_up_questions(session.collected_data_json)
        if _has_minimum_report_data(session.collected_data_json):
            reply = _text(language, "ready_to_submit")
            actions = ["Submit report", "Add more details"]
        else:
            reply = _localize_question(questions[0], language)
            actions = questions[1:] + ["Check report status"]

    assistant = ChatMessage(
        session_id=session.id,
        role=ChatRole.assistant,
        message_text=reply,
        structured_payload_json={"suggested_actions": actions, "collected_data": session.collected_data_json},
    )
    db.add(assistant)
    db.commit()
    db.refresh(session)
    db.refresh(assistant)
    return ChatResponse(session=session, assistant_message=assistant, suggested_actions=actions)


@router.post("/{session_id}/verify-report", response_model=ChatResponse)
async def verify_report(
    session_id: int,
    payload: ChatVerifyReportRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    report = db.query(LostReport).filter(LostReport.report_code == payload.report_code.upper()).one_or_none()
    language = _normalize_language(payload.language or session.language)
    session.language = language
    if not report or not contact_matches_report(report, payload.contact):
        assistant_text = _text(language, "verify_failed")
        session.verification_status = "failed"
        actions = ["Try again"]
    else:
        cache_key = f"status:{language}:{report.report_code}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            assistant_text = cached["message"]
        else:
            best = max((candidate.match_score for candidate in report.match_candidates), default=0)
            assistant_text = _status_message(language, report.report_code, report.status.value, best)
            await cache_service.set_json(cache_key, {"message": assistant_text}, 60)
        session.verification_status = "verified"
        session.lost_report_id = report.id
        session.current_state = "status_verified"
        actions = ["Ask another update", "Report another item"]
    assistant = ChatMessage(
        session_id=session.id,
        role=ChatRole.assistant,
        message_text=assistant_text,
        structured_payload_json={"safe_status_only": True, "suggested_actions": actions},
    )
    db.add(assistant)
    db.commit()
    db.refresh(session)
    db.refresh(assistant)
    return ChatResponse(session=session, assistant_message=assistant, suggested_actions=actions)


@router.post("/{session_id}/submit-lost-report", response_model=LostReportRead)
async def submit_lost_report(
    session_id: int,
    payload: ChatSubmitLostReportRequest,
    db: Session = Depends(get_db),
) -> LostReport:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    data = payload.data or session.collected_data_json or {}
    if not _has_minimum_report_data(data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="More lost item details are required")
    report = LostReport(
        item_title=data.get("item_title") or f"Lost {data.get('category', 'item')}",
        category=data.get("category"),
        raw_description=data.get("raw_description") or data.get("description") or "Passenger submitted report via chatbot.",
        brand=data.get("brand"),
        model=data.get("model"),
        color=data.get("color"),
        lost_location=data.get("lost_location"),
        lost_datetime=_parse_datetime(data.get("lost_datetime")),
        flight_number=data.get("flight_number"),
        contact_email=data.get("contact_email"),
        contact_phone=data.get("contact_phone"),
    )
    db.add(report)
    await enrich_lost_report(db, report)
    db.commit()
    db.refresh(report)
    session.lost_report_id = report.id
    session.current_state = "report_submitted"
    session.collected_data_json = data
    db.add(ChatMessage(
        session_id=session.id,
        role=ChatRole.assistant,
        message_text=f"Your report has been created. Keep this code: {report.report_code}.",
        structured_payload_json={"report_code": report.report_code},
    ))
    db.commit()
    await run_matching_for_lost_report(db, report)
    await invalidate_operational_caches()
    return report


def _looks_like_status_request(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ["status", "update", "check report", "report code", "حالة", "تحديث", "رقم البلاغ"])


def _merge_chat_data(current: dict[str, Any], text: str) -> dict[str, Any]:
    data = dict(current)
    attrs = {}
    lowered = text.lower()
    if "@" in text:
        match = re.search(r"[\w.\-+]+@[\w.-]+\.\w+", text)
        if match:
            data["contact_email"] = match.group(0)
    phone = re.search(r"\+?\d[\d\s().-]{7,}\d", text)
    if phone:
        data["contact_phone"] = phone.group(0)
    for color in ["black", "white", "blue", "red", "green", "silver", "gold", "gray", "brown"]:
        if re.search(rf"\b{color}\b", lowered):
            data["color"] = color
    arabic_colors = {"أسود": "black", "اسود": "black", "أبيض": "white", "ابيض": "white", "أزرق": "blue", "ازرق": "blue", "أحمر": "red", "احمر": "red", "فضي": "silver", "ذهبي": "gold", "رمادي": "gray", "بني": "brown"}
    for word, value in arabic_colors.items():
        if word in text:
            data["color"] = value
    for category in ["phone", "laptop", "bag", "wallet", "passport", "id card", "headphones", "keys", "watch", "clothing"]:
        if category in lowered:
            data["category"] = category.title()
            data["item_title"] = f"Lost {category.title()}"
    arabic_categories = {"هاتف": "Phone", "لابتوب": "Laptop", "حقيبة": "Bag", "محفظة": "Wallet", "جواز": "Passport", "بطاقة": "ID Card", "سماعة": "Headphones", "مفاتيح": "Keys", "ساعة": "Watch", "ملابس": "Clothing"}
    for word, value in arabic_categories.items():
        if word in text:
            data["category"] = value
            data["item_title"] = f"Lost {value}"
    location = re.search(r"\b(terminal\s?\d|gate\s?[a-z]\d+|security checkpoint\s?[a-z]?|baggage claim\s?\d|food court|lounge|restroom)\b", text, re.IGNORECASE)
    if location:
        data["lost_location"] = location.group(1).title()
    flight = re.search(r"\b([A-Z]{2}\s?\d{2,4})\b", text, re.IGNORECASE)
    if flight:
        data["flight_number"] = flight.group(1).upper().replace(" ", "")
    if len(text) > 20:
        data["raw_description"] = f"{data.get('raw_description', '')} {text}".strip()
    if "today" in lowered:
        data["lost_datetime"] = datetime.now(UTC).isoformat()
    return data | attrs


def _has_minimum_report_data(data: dict[str, Any]) -> bool:
    return bool(data.get("category") and data.get("raw_description") and data.get("lost_location") and (data.get("contact_email") or data.get("contact_phone")))


def contact_matches_report(report: LostReport, contact: str) -> bool:
    contact = contact.strip().lower()
    return contact in {
        (report.contact_email or "").lower(),
        (report.contact_phone or "").lower(),
        (mask_phone(report.contact_phone) or "").lower(),
    }


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _normalize_language(language: str | None) -> str:
    if (language or "").lower().startswith("ar"):
        return "ar"
    return "en"


def _text(language: str, key: str) -> str:
    values = {
        "greeting": {
            "en": "Hi. I can help you file a lost-item report or check an existing report update.",
            "ar": "أهلا. يمكنني مساعدتك في تسجيل بلاغ مفقود أو معرفة تحديث آمن عن بلاغ موجود.",
        },
        "status_prompt": {
            "en": "Please share your report code and the email or phone number used on the report.",
            "ar": "من فضلك أرسل رقم البلاغ والبريد الإلكتروني أو رقم الهاتف المستخدم في البلاغ.",
        },
        "ready_to_submit": {
            "en": "I have enough information to create a lost-item report. You can submit it now, or add more details.",
            "ar": "لدي معلومات كافية لإنشاء بلاغ مفقود. يمكنك إرساله الآن أو إضافة تفاصيل أخرى.",
        },
        "verify_failed": {
            "en": "I could not verify that report with the contact information provided.",
            "ar": "لم أتمكن من التحقق من البلاغ باستخدام بيانات التواصل المقدمة.",
        },
    }
    return values[key][language]


def _status_message(language: str, report_code: str, report_status: str, best: float) -> str:
    if language == "ar":
        return (
            f"البلاغ {report_code} حالته {report_status}. "
            f"أفضل درجة تطابق حالية {best:.0f}/100. "
            "سيتواصل معك موظفو المطار إذا احتاجوا إلى تحقق يدوي."
        )
    return (
        f"Report {report_code} is {report_status}. "
        f"Best current staff review score is {best:.0f}/100. "
        "Airport staff will contact you if manual verification is needed."
    )


def _localize_question(question: str, language: str) -> str:
    if language != "ar":
        return question
    if "location" in question.lower() or "where" in question.lower():
        return "أين فقدت الغرض؟ اذكر الصالة أو البوابة أو أقرب منطقة إن أمكن."
    if "contact" in question.lower() or "email" in question.lower() or "phone" in question.lower():
        return "ما البريد الإلكتروني أو رقم الهاتف الذي يمكننا استخدامه للتواصل معك؟"
    if "color" in question.lower() or "brand" in question.lower():
        return "ما لون الغرض أو علامته التجارية أو أي علامة مميزة؟"
    return "أخبرني بتفاصيل أكثر عن الغرض المفقود، مثل النوع واللون والمكان والوقت."
