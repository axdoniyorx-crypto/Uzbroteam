"""Short-lived token store for "download audio" inline buttons.

Telegram's Bot API rejects any ``callback_data`` longer than 64 bytes
(``Bad Request: BUTTON_DATA_INVALID``). Some platform handlers (Instagram)
used to build ``callback_data`` by embedding the *full* source URL, e.g.
``f"audio:inst:{original_url}"``. Real Instagram links (with share/tracking
query params) routinely exceed 64 bytes once the prefix is added, which
means the "🎧 MP3 yuklab olish" button silently broke message delivery for
those videos.

This module gives platform handlers a short opaque token to put in
``callback_data`` instead, while the real URL is kept here (in memory, with
a TTL) and resolved back when the button is tapped — the same approach
already used for inline video/album requests in
``services/inline/video_requests.py``.
"""

from __future__ import annotations

import secrets
import time
from typing import Optional

_TTL_SECONDS = 6 * 60 * 60.0  # 6 hours — long enough to outlive a chat session
_MAX_ENTRIES = 4096

_tokens: dict[str, tuple[str, float]] = {}


def _prune(now: Optional[float] = None) -> None:
    now = time.time() if now is None else now
    expired = [token for token, (_, created_at) in _tokens.items() if now - created_at > _TTL_SECONDS]
    for token in expired:
        _tokens.pop(token, None)

    overflow = len(_tokens) - _MAX_ENTRIES
    if overflow > 0:
        oldest = sorted(_tokens, key=lambda token: _tokens[token][1])[:overflow]
        for token in oldest:
            _tokens.pop(token, None)


def register_audio_url(url: str) -> str:
    """Store `url` and return a short token safe to embed in callback_data."""
    _prune()
    token = secrets.token_urlsafe(8)
    _tokens[token] = (url, time.time())
    return token


def resolve_audio_url(token: str) -> Optional[str]:
    """Look up a previously registered URL by its token, or None if expired/unknown."""
    _prune()
    entry = _tokens.get(token)
    return entry[0] if entry else None
