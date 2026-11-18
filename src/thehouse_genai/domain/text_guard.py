"""Shared text safety guards for untrusted input and generated output.

The escaping and the injection detection used by the explanation use case are kept here
so the search use case can apply the exact same rules. The module is pure: it depends
only on the standard library and never on providers, the API or infrastructure.

Detection works on a separate string. Homoglyphs and zero-width characters are folded
only to look for markers; the text returned to callers is never rewritten by detection.
"""

from __future__ import annotations

import unicodedata
from typing import Final

INJECTION_MARKERS: Final[tuple[str, ...]] = (
    "<untrusted_data>",
    "</untrusted_data>",
    "ignora las instrucciones",
    "ignora las reglas",
    "ignore previous instructions",
    "ignore all previous",
    "new system prompt",
    "nuevo system prompt",
    "system:",
)

# Detection-only homoglyph folding (spec 005, D6). NFKC handles fullwidth and other
# compatibility forms but does not turn Cyrillic or Greek letters into Latin ones, so an
# explicit confusables table is needed.
_CONFUSABLES: Final[dict[str, str]] = {
    chr(code): latin
    for code, latin in (
        # Cyrillic lower and upper case
        (0x0430, "a"), (0x0435, "e"), (0x043E, "o"), (0x0440, "p"), (0x0441, "c"),
        (0x0456, "i"), (0x0443, "y"), (0x0445, "x"), (0x043A, "k"), (0x043C, "m"),
        (0x0442, "t"), (0x043D, "h"), (0x0432, "b"),
        (0x0410, "A"), (0x0415, "E"), (0x041E, "O"), (0x041F, "P"), (0x0421, "C"),
        (0x0406, "I"), (0x0423, "Y"), (0x0425, "X"), (0x041A, "K"), (0x041C, "M"),
        (0x0422, "T"), (0x041D, "H"), (0x0412, "B"),
        # Greek lower and upper case
        (0x03B1, "a"), (0x03B5, "e"), (0x03BF, "o"), (0x03C1, "p"), (0x03B9, "i"),
        (0x03C5, "u"), (0x03C7, "x"), (0x03BA, "k"), (0x03BC, "m"), (0x03C4, "t"),
        (0x03BD, "v"), (0x03B2, "b"), (0x03B7, "n"),
        (0x0391, "A"), (0x0395, "E"), (0x039F, "O"), (0x03A1, "P"), (0x0399, "I"),
        (0x03A5, "U"), (0x03A7, "X"), (0x039A, "K"), (0x039C, "M"), (0x03A4, "T"),
        (0x039D, "N"), (0x0392, "B"), (0x0397, "H"),
    )
}

_ZERO_WIDTH_CHARS: Final[frozenset[str]] = frozenset(
    {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"}
)


def is_control(char: str) -> bool:
    """Report whether a character is a C0 control or DEL."""

    code = ord(char)
    return code < 32 or code == 127


def escape_untrusted(value: str) -> str:
    """Neutralize delimiters and control characters in untrusted free text.

    Angle brackets become HTML entities so a value can never close the
    `<untrusted_data>` block of the prompt. Backslashes are doubled first, so the
    control-character escapes emitted below cannot be confused with input text.
    """

    escaped = value.replace("\\", "\\\\").replace("<", "&lt;").replace(">", "&gt;")
    return "".join(
        f"\\u{ord(char):04x}" if is_control(char) else char
        for char in escaped
    )


def normalize_for_detection(text: str) -> str:
    """Fold homoglyphs and zero-width characters for marker detection only.

    The result is a separate string: callers never return it as user-facing text, so
    validation can never alter the content that reaches Backend.
    """

    folded = unicodedata.normalize("NFKC", text)
    without_zero_width = "".join(char for char in folded if char not in _ZERO_WIDTH_CHARS)
    return "".join(_CONFUSABLES.get(char, char) for char in without_zero_width)


def contains_injection_marker(text: str) -> bool:
    """Report whether detection-normalized text carries a known injection marker."""

    folded = normalize_for_detection(text).casefold()
    return any(marker in folded for marker in INJECTION_MARKERS)
