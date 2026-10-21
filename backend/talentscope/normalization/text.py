from __future__ import annotations

import re
import unicodedata

# Placeholders the legacy scraper and common job boards use for "no value". They are
# treated as missing rather than stored as if they were real text.
_MISSING_MARKERS = frozenset({"", "-", "n/a", "na", "none", "null", "not specified"})

_WHITESPACE = re.compile(r"\s+")


def clean_text(value: object) -> str | None:
    """Return the value as tidy single-line text, or None when it carries no information.

    NFKC folds compatibility characters (non-breaking spaces, full-width digits) into
    their plain forms; meaningful punctuation such as the en dash in "1–3 tahun" is kept.
    """
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN from pandas/CSV readers
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = _WHITESPACE.sub(" ", text).strip()
    if text.casefold() in _MISSING_MARKERS:
        return None
    return text


def normalize_for_matching(value: str | None) -> str:
    """Lowercase, accent-free, punctuation-free form used for fingerprints and dedupe.

    Unlike the original K-Means preprocessing, separators never produce empty tokens:
    runs of non-alphanumeric characters collapse to a single space and the result is
    stripped. "+" and "#" survive so that "C++" and "C#" stay distinguishable.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = re.sub(r"[^0-9a-z+#]+", " ", text)
    return text.strip()
