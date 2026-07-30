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

__all__ = ["MAX_KEYWORD_LENGTH", "normalize_keyword", "searchad_hint"]

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


def searchad_hint(normalized: str) -> str:
    """네이버 검색광고 `hintKeywords` 가 받는 형태 — **띄어쓰기가 없다.**

    실측: `hintKeywords=강남 한의원` 은 HTTP 400, `hintKeywords=강남한의원` 은 200 이다.
    그리고 응답의 `relKeyword` 도 띄어쓰기 없는 형태로 돌아온다.

    이것이 `normalize_keyword` 와 다른 함수인 이유: 저쪽은 **우리가 저장하고 보여주는**
    표준형이고, 사용자가 입력한 "강남 한의원" 은 그 모양 그대로 남아야 한다. 이쪽은
    **한 공급자가 요구하는** 모양이다. 둘을 하나로 합치면 공급자 사정이 우리 저장
    형식까지 바꾼다.

    이걸 안 하고 있었다. 그래서 **띄어쓰기가 들어간 키워드는 전부 조회에 실패했다** —
    한국어 검색 키워드는 대부분 띄어쓰기가 있으므로, 사실상 자연스러운 입력이 다 막혀
    있었다.
    """
    return _WHITESPACE_RUN.sub("", normalized)
