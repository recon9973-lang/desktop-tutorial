"""Keyword normalisation.

Two spellings of one keyword quietly become two keywords: two cache entries, two rows in
a report, two lines in an export that a customer then asks about. So a keyword is reduced
to one canonical form before it is looked up, cached, stored or compared — and the form
the customer typed is kept beside it, because that is what they will recognise.

The reduction is deliberately conservative. It does not strip punctuation or hyphens, and
it does not remove spaces between words: in Korean search behaviour "성형 외과" and
"성형외과" are genuinely different queries with different volumes, and collapsing them
would be VEO deciding the customer meant something else.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

__all__ = ["MAX_KEYWORD_LENGTH", "normalize_keyword"]

#: ``keyword_queries.normalized_keyword`` is ``VARCHAR(255)``.
MAX_KEYWORD_LENGTH: Final = 255

_WHITESPACE_RUN: Final = re.compile(r"\s+")


def normalize_keyword(raw: str) -> str:
    """Reduce ``raw`` to its canonical form, or raise ``ValueError``.

    Compatibility normalisation (NFKC) first, so full-width and half-width spellings of
    the same characters agree; then runs of whitespace collapse to a single space; then
    case folding, which is a no-op for Hangul and the right answer for the Latin and
    numeric fragments that appear in brand and model keywords.
    """
    if not isinstance(raw, str):
        raise TypeError("a keyword must be a string")

    folded = unicodedata.normalize("NFKC", raw)
    # Control characters would survive NFKC and land in a CSV export intact.
    folded = "".join(char for char in folded if unicodedata.category(char)[0] != "C")
    collapsed = _WHITESPACE_RUN.sub(" ", folded).strip()

    if not collapsed:
        raise ValueError("키워드가 비어 있습니다.")
    if len(collapsed) > MAX_KEYWORD_LENGTH:
        raise ValueError(f"키워드는 최대 {MAX_KEYWORD_LENGTH}자까지 입력할 수 있습니다.")

    return collapsed.casefold()
