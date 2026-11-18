"""One-way metadata derived from secrets for logs and in-memory keys."""

from __future__ import annotations

import hashlib
from typing import Final

_FINGERPRINT_CHARS: Final[int] = 16


def fingerprint(value: str) -> str:
    """Return a short, one-way fingerprint of a credential.

    The digest is used only as an in-memory bucket key and as safe log metadata: it
    never carries the original value and is not reversible for a high-entropy key.
    """

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:_FINGERPRINT_CHARS]
