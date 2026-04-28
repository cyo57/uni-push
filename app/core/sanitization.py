from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.config import get_settings

SENSITIVE_FIELD_NAMES = {
    "authorization",
    "password",
    "secret",
    "sign",
    "signature",
    "token",
}


def sanitize_text(value: str | None, max_bytes: int | None = None) -> str | None:
    if value is None:
        return None

    settings = get_settings()
    limit = max_bytes or settings.sensitive_log_max_bytes
    raw = value.encode("utf-8")
    if len(raw) <= limit:
        return value

    truncated = raw[:limit].decode("utf-8", errors="ignore")
    return f"{truncated}...(truncated)"


def sanitize_for_storage(value):
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            lowered = key.lower()
            if lowered in SENSITIVE_FIELD_NAMES and item not in (None, ""):
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = sanitize_for_storage(item)
        return sanitized

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_for_storage(item) for item in value]

    if isinstance(value, str):
        return sanitize_text(value)

    return value
