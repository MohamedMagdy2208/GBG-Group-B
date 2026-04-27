import re
from collections.abc import Iterable, Mapping

from src.config import MAX_CHAT_HISTORY_CHARS, MAX_CHAT_HISTORY_MESSAGES


def _compact_text(value: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."


def format_chat_history(
    messages: Iterable[Mapping[str, object]] | None,
    max_messages: int = MAX_CHAT_HISTORY_MESSAGES,
    max_chars: int = MAX_CHAT_HISTORY_CHARS,
) -> str:
    if not messages:
        return "No prior conversation."

    formatted = []
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        formatted.append(f"{role}: {_compact_text(content, max_chars)}")

    if not formatted:
        return "No prior conversation."
    return "\n".join(formatted[-max_messages:])
