from __future__ import annotations

MAX_SESSION_ID_LENGTH = 64


def normalize_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > MAX_SESSION_ID_LENGTH:
        raise ValueError("Session identifier is too long.")
    if any(ord(char) < 32 for char in candidate):
        raise ValueError("Session identifier contains invalid control characters.")
    if any(not (char.isalnum() or char in {"-", "_"}) for char in candidate):
        raise ValueError(
            "Session identifier can contain only letters, numbers, '-' and '_'."
        )
    return candidate
