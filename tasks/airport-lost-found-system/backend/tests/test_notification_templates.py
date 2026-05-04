from app.services.notification_template_service import (
    render_match_alert,
    render_release_confirmation,
    select_template,
)


def test_match_alert_english_includes_report_code() -> None:
    subject, body = render_match_alert("LR-ABC12345", "high", "en")
    assert "LR-ABC12345" in subject
    assert "high" in body.lower()


def test_match_alert_arabic_uses_arabic_subject() -> None:
    subject, body = render_match_alert("LR-X1", "high", "ar")
    assert "LR-X1" in subject
    assert any(letter in subject for letter in "تحديث على بلاغك")
    assert any(letter in body for letter in "عثرنا")


def test_release_confirmation_renders_for_both_languages() -> None:
    en_subject, _ = render_release_confirmation("LR-1", "en")
    ar_subject, _ = render_release_confirmation("LR-1", "ar")
    assert "released" in en_subject.lower()
    assert "تسليم" in ar_subject


def test_select_template_only_fires_match_alert_on_high_confidence() -> None:
    low = select_template("match_candidate.upserted", {"report_code": "LR-1", "confidence_level": "low"}, "en")
    medium = select_template("match_candidate.upserted", {"report_code": "LR-1", "confidence_level": "medium"}, "en")
    high = select_template("match_candidate.upserted", {"report_code": "LR-1", "confidence_level": "high"}, "en")
    assert low is None
    assert medium is None
    assert high is not None


def test_select_template_returns_none_when_report_code_missing() -> None:
    assert select_template("match_candidate.upserted", {"confidence_level": "high"}, "en") is None
    assert select_template("item.released", {}, "en") is None


def test_select_template_unknown_event_returns_none() -> None:
    assert select_template("unknown.event", {"report_code": "LR-1"}, "en") is None
