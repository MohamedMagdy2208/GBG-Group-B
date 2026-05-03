import pytest

from app.core.security import hash_token, mask_phone, mask_sensitive_text, validate_password_strength, verify_mfa_code


def test_password_strength_rejects_weak_passwords() -> None:
    with pytest.raises(ValueError):
        validate_password_strength("short")
    with pytest.raises(ValueError):
        validate_password_strength("alllowercasepassword")


def test_password_strength_accepts_pilot_policy() -> None:
    validate_password_strength("Password123!")


def test_sensitive_masking_redacts_ids_and_phones_but_not_normal_words() -> None:
    text = "Passenger phone +1 555 222 1234 has passport A1234567 and a blue suitcase"
    masked = mask_sensitive_text(text)
    assert masked is not None
    assert "+1 555 222 1234" not in masked
    assert "A1234567" not in masked
    assert "blue suitcase" in masked


def test_mfa_hook_uses_token_hash() -> None:
    code = "123456"
    assert verify_mfa_code(code, hash_token(code))
    assert not verify_mfa_code("000000", hash_token(code))
    assert verify_mfa_code(None, None)


def test_phone_mask_keeps_only_last_four_digits() -> None:
    assert mask_phone("+1 (555) 222-1234") == "***-***-1234"
