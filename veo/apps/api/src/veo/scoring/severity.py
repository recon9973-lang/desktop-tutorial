"""The severity vocabulary, and what each term means to the person reading it.

Severity is the engine's word. The *coefficient* attached to a term lives in a versioned
specification and changes with it; the term itself — what BLOCKER means to someone
looking at an issue — is the same in every version, so it is defined once here instead of
being repeated in nine spec files.

It is served rather than left to the screen to spell out. A hand-written list on the
screen keeps showing five terms after the engine grows a sixth, and the failure is
invisible: the missing severity is simply absent, with nothing to notice. The screen
draws whatever this list contains.

No coefficient is exposed here. How much a severity costs is a number, and numbers belong
to the specification — a screen that knew them could compute a score of its own.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from veo.scoring.models import Severity


class SeverityTerm(BaseModel):
    """One severity, named in the language the reader is being addressed in."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: Severity
    label_ko: str
    meaning_ko: str


#: Ordered most severe first — the order a reader should meet them in.
SEVERITY_VOCABULARY: tuple[SeverityTerm, ...] = (
    SeverityTerm(
        severity=Severity.BLOCKER,
        label_ko="차단",
        meaning_ko="색인 자체를 막을 수 있는 문제입니다.",
    ),
    SeverityTerm(
        severity=Severity.CRITICAL,
        label_ko="치명",
        meaning_ko="해석·제공에 큰 영향을 주는 문제입니다.",
    ),
    SeverityTerm(
        severity=Severity.MAJOR,
        label_ko="중대",
        meaning_ko="품질에 눈에 띄는 영향을 주는 문제입니다.",
    ),
    SeverityTerm(
        severity=Severity.MINOR,
        label_ko="경미",
        meaning_ko="영향이 제한적인 개선 항목입니다.",
    ),
    SeverityTerm(
        severity=Severity.INFO,
        label_ko="참고",
        meaning_ko="감점 없이 참고로만 남기는 항목입니다.",
    ),
)
