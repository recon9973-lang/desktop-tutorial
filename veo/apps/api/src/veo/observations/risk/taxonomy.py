"""The risk taxonomy: what can go wrong in an AI answer, and how badly.

VEO's customers are hospitals and clinics. When an answer engine says a clinic performs a
procedure it does not, quotes a price it does not charge, or attributes another business's
malpractice story to it, that is a regulatory and legal exposure — not a marketing
inconvenience. The bands below are ordered by that exposure, not by how surprising the
error is.

Two rules govern every line here:

**Severity is read, never chosen.** :data:`RISK_TAXONOMY` is a versioned table. A caller
supplies the *kind* of finding and the *subject matter* of the claim; the band comes back
from the table. No call site anywhere in this package writes a severity literal, so a
band cannot drift between the report, the queue and the gate.

**Regulated subject matter overrides everything.** Medical, legal, pricing and contractual
claims are the top band regardless of which check found them. A stale opening-hours line
is a low finding; a stale price is fatal, because a patient acts on it.

All worked examples below concern invented businesses and are marked
:data:`FICTIONAL_EXAMPLE_MARKER`. A plausible-looking example is one copy-paste away from
a customer report, and VEO would then be publishing a claim about a real clinic that it
made up itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from veo.scoring.models import Severity

#: Bump when a band assignment or a kind changes. Reports quote it, so a reader can tell
#: which edition of the methodology produced a count.
TAXONOMY_VERSION = "risk-taxonomy/2026-07-28.1"

#: Every worked example carries this marker. Asserted by a test.
FICTIONAL_EXAMPLE_MARKER = "가상 사례"


class RiskKind(StrEnum):
    """The checks the methodology defines.

    ``RECOMMENDATION_INCLUSION`` and ``RECOMMENDATION_EXCLUSION`` are separate findings —
    "the engine recommended a competitor for our own branded question" and "the engine
    left our customer out of a list it belongs in" call for different work — but the
    ``claim_assessments.assessment_type`` column documents a single ``RECOMMENDATION``
    value. :attr:`storage_value` performs that narrowing on the way out;
    :meth:`from_storage` refuses to invent the missing half on the way back. Widening the
    stored vocabulary is request #1 in ``INTEGRATION_REQUEST.md``.
    """

    CLAIM_ACCURACY = "CLAIM_ACCURACY"
    CITATION_ENTAILMENT = "CITATION_ENTAILMENT"
    CITATION_COMPLETENESS = "CITATION_COMPLETENESS"
    ENTITY_DISAMBIGUATION = "ENTITY_DISAMBIGUATION"
    RECOMMENDATION_INCLUSION = "RECOMMENDATION_INCLUSION"
    RECOMMENDATION_EXCLUSION = "RECOMMENDATION_EXCLUSION"
    SENTIMENT_WITH_GROUNDS = "SENTIMENT_WITH_GROUNDS"
    STALENESS = "STALENESS"

    @property
    def storage_value(self) -> str:
        """The value ``claim_assessments.assessment_type`` accepts today."""
        return _STORAGE_VALUES.get(self, self.value)

    @classmethod
    def from_storage(cls, raw: str) -> RiskKind:
        """Read a stored ``assessment_type`` back, refusing the ambiguous one.

        ``RECOMMENDATION`` maps to two different findings. Picking one would silently
        turn "the clinic was left out of the list" into "the clinic was wrongly
        recommended", which is a different sentence to put in front of a customer.
        """
        if raw == "RECOMMENDATION":
            raise ValueError(
                "저장된 'RECOMMENDATION' 값만으로는 추천 포함/누락 중 어느 쪽인지 알 수 없습니다. "
                "둘은 서로 다른 지적이므로 추측하지 않습니다."
            )
        for kind in cls:
            if kind.storage_value == raw:
                return kind
        raise ValueError(f"알 수 없는 위험 유형입니다: {raw}")


_STORAGE_VALUES: dict[RiskKind, str] = {
    RiskKind.RECOMMENDATION_INCLUSION: "RECOMMENDATION",
    RiskKind.RECOMMENDATION_EXCLUSION: "RECOMMENDATION",
    RiskKind.SENTIMENT_WITH_GROUNDS: "SENTIMENT",
}


class ClaimDomain(StrEnum):
    """What the assessed sentence is *about*.

    The kind of check says how the error was found. The domain says what it costs. A
    hallucinated opening hour and a hallucinated surgical indication are the same check
    and nothing like the same problem.
    """

    MEDICAL = "MEDICAL"
    """진료·시술·적응증·부작용·자격. 의료광고 및 환자 안전 영역."""

    LEGAL = "LEGAL"
    """인허가·규제·행정처분·법적 지위."""

    PRICING = "PRICING"
    """가격·비급여 고지·할인·환급 조건."""

    CONTRACTUAL = "CONTRACTUAL"
    """보증·환불·계약 조건·보험 처리."""

    IDENTITY = "IDENTITY"
    """어느 업체를 말하는지. 동명 병원 혼동이 여기에 들어갑니다."""

    CONTACT = "CONTACT"
    """주소·전화·진료 시간·교통."""

    REPUTATION = "REPUTATION"
    """평판·후기·비교 서술."""

    GENERAL = "GENERAL"
    """위 어디에도 해당하지 않는 일반 서술."""


#: Subject matter that is always the top band, whatever check found it.
REGULATED_DOMAINS: frozenset[ClaimDomain] = frozenset(
    {ClaimDomain.MEDICAL, ClaimDomain.LEGAL, ClaimDomain.PRICING, ClaimDomain.CONTRACTUAL}
)


class RiskBand(StrEnum):
    """치명 / 높음 / 중간 / 낮음.

    Four bands, declared in order. :attr:`rank` exists only so a queue can sort and a
    gate can compare; it is never serialised into a report, because the moment a band
    becomes a number somebody adds them up.
    """

    FATAL = "FATAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @property
    def label_ko(self) -> str:
        return _BAND_LABELS_KO[self]

    @property
    def definition_ko(self) -> str:
        return _BAND_DEFINITIONS_KO[self]

    @property
    def rank(self) -> int:
        """0 is the most severe. Ordering only — never published."""
        return _BAND_ORDER.index(self)


_BAND_ORDER: tuple[RiskBand, ...] = (
    RiskBand.FATAL,
    RiskBand.HIGH,
    RiskBand.MEDIUM,
    RiskBand.LOW,
)

_BAND_LABELS_KO: dict[RiskBand, str] = {
    RiskBand.FATAL: "치명",
    RiskBand.HIGH: "높음",
    RiskBand.MEDIUM: "중간",
    RiskBand.LOW: "낮음",
}

_BAND_DEFINITIONS_KO: dict[RiskBand, str] = {
    RiskBand.FATAL: (
        "환자가 이 문장을 믿고 행동하면 건강·금전·법적 피해가 발생할 수 있습니다. "
        "의료·법률·가격·계약 영역의 오류는 어떤 검사에서 나왔든 전부 여기입니다."
    ),
    RiskBand.HIGH: (
        "사실관계가 틀렸거나 근거가 문장을 뒷받침하지 못합니다. 환자의 판단을 왜곡하지만 "
        "규제 영역은 아닙니다."
    ),
    RiskBand.MEDIUM: (
        "답변이 불완전하거나 편향되어 있습니다. 틀린 문장은 아니지만 고객이 받아야 할 "
        "노출을 잃고 있습니다."
    ),
    RiskBand.LOW: "표현·시점의 문제로, 방치해도 즉각적인 피해는 없습니다.",
}

#: How a band is written into ``claim_assessments.severity`` and read by the rest of the
#: platform. The band is the Korean-facing name; :class:`~veo.scoring.models.Severity` is
#: the shared vocabulary, so a risk finding and a SEO issue sort against each other.
BAND_SEVERITY: dict[RiskBand, Severity] = {
    RiskBand.FATAL: Severity.BLOCKER,
    RiskBand.HIGH: Severity.CRITICAL,
    RiskBand.MEDIUM: Severity.MAJOR,
    RiskBand.LOW: Severity.MINOR,
}
# Severity.INFO is deliberately unmapped. A risk finding that is worth no action is not
# recorded at all; giving it a band would put noise into a count that is meant to be read
# whole.


@dataclass(frozen=True, slots=True)
class WorkedExample:
    """One concrete, invented case and the band it earns."""

    situation_ko: str
    band: RiskBand
    why_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "situation_ko": self.situation_ko,
            "band": self.band.value,
            "band_label_ko": self.band.label_ko,
            "why_ko": self.why_ko,
        }


@dataclass(frozen=True, slots=True)
class RiskKindSpec:
    """One row of the methodology.

    ``deterministic_ko`` and ``needs_model_ko`` are not documentation for its own sake:
    they are the contract that :mod:`veo.observations.risk.assessment` and
    :mod:`veo.observations.risk.entailment` implement, and the reason a reader can tell
    at a glance which findings a language model was involved in.
    """

    kind: RiskKind
    name_ko: str
    definition_ko: str
    base_band: RiskBand
    deterministic_ko: str
    needs_model_ko: str
    examples: tuple[WorkedExample, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "stored_as": self.kind.storage_value,
            "name_ko": self.name_ko,
            "definition_ko": self.definition_ko,
            "base_band": self.base_band.value,
            "base_band_label_ko": self.base_band.label_ko,
            "deterministic_ko": self.deterministic_ko,
            "needs_model_ko": self.needs_model_ko,
            "examples": [example.as_dict() for example in self.examples],
        }


@dataclass(frozen=True, slots=True)
class RiskTaxonomy:
    """The published table. Everything else in this package reads it."""

    version: str
    kinds: tuple[RiskKindSpec, ...]
    regulated_domains: frozenset[ClaimDomain]
    review_required_at_or_above: RiskBand

    def spec_for(self, kind: RiskKind) -> RiskKindSpec:
        for spec in self.kinds:
            if spec.kind is kind:
                return spec
        raise KeyError(f"분류표에 없는 위험 유형입니다: {kind.value}")

    def band_for(self, *, kind: RiskKind, domain: ClaimDomain) -> RiskBand:
        """The band this finding lands in.

        Regulated subject matter is checked first and wins outright. A stale price is not
        a "staleness, low" finding — it is a price a patient may act on.
        """
        if domain in self.regulated_domains:
            return RiskBand.FATAL
        return self.spec_for(kind).base_band

    def severity_for(self, *, kind: RiskKind, domain: ClaimDomain) -> Severity:
        return BAND_SEVERITY[self.band_for(kind=kind, domain=domain)]

    def requires_human_review(self, band: RiskBand) -> bool:
        """Whether a finding in this band may not be published unreviewed."""
        return band.rank <= self.review_required_at_or_above.rank

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "review_required_at_or_above": self.review_required_at_or_above.value,
            "regulated_domains": sorted(domain.value for domain in self.regulated_domains),
            "bands": [
                {
                    "band": band.value,
                    "label_ko": band.label_ko,
                    "definition_ko": band.definition_ko,
                    "severity": BAND_SEVERITY[band].value,
                }
                for band in _BAND_ORDER
            ],
            "kinds": [spec.as_dict() for spec in self.kinds],
        }


# --------------------------------------------------------------------------- #
# The table
# --------------------------------------------------------------------------- #
#
# Base bands apply to unregulated subject matter only. Anything medical, legal, pricing
# or contractual is 치명 by the rule in `band_for`, which is why no row below has to
# repeat it.

_KINDS: tuple[RiskKindSpec, ...] = (
    RiskKindSpec(
        kind=RiskKind.CLAIM_ACCURACY,
        name_ko="사실 정확성",
        definition_ko=(
            "AI 답변이 고객에 대해 말한 문장이 실제와 맞는지. 비교 대상은 고객이 직접 게시한 "
            "정보(자사 홈페이지·공식 고지)이며, 검증자의 인상이 아닙니다."
        ),
        base_band=RiskBand.HIGH,
        deterministic_ko=(
            "고객 홈페이지에 게시된 값과 직접 대조할 수 있는 항목 — 가격, 진료 시간, 주소, "
            "전화번호 — 은 규칙으로 판정합니다. 언어모델을 쓰지 않습니다."
        ),
        needs_model_ko=(
            "서술형 문장('이 병원은 ○○에 강점이 있다')의 참·거짓은 규칙으로 판정할 수 없어 "
            "언어모델 판정을 거치고, 그 판정은 반드시 사람 검수 대상입니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: 가상 하늘별의원은 로봇수술 장비가 없는데 AI 답변이 "
                    "'로봇수술이 가능한 병원'이라고 소개했습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="제공하지 않는 시술을 제공한다고 말한 의료 영역 오류입니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: 가상 하늘별의원 주차장이 3면인데 AI 답변이 "
                    "'넓은 전용 주차장'이라고 설명했습니다."
                ),
                band=RiskBand.HIGH,
                why_ko="사실과 다르지만 규제 영역이 아니며 환자 안전과 직결되지 않습니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.CITATION_ENTAILMENT,
        name_ko="인용 근거 일치",
        definition_ko=(
            "AI 답변이 든 출처가 그 문장을 실제로 뒷받침하는지. 출처가 존재하는 것과 "
            "출처가 그 말을 하고 있는 것은 다른 사실입니다."
        ),
        base_band=RiskBand.HIGH,
        deterministic_ko=(
            "인용 URL이 없거나 404 인 경우는 규칙으로 '뒷받침 없음' 판정입니다. "
            "가져오지 못한 경우(타임아웃·차단)는 판정이 아니라 UNKNOWN 입니다."
        ),
        needs_model_ko=(
            "출처 본문을 읽어와 문장이 함의되는지 보는 단계에서만 언어모델을 사용하며, "
            "자격증명이 없으면 UNKNOWN 으로 남깁니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: AI 답변이 가상 하늘별의원의 시술 성공률을 말하며 "
                    "링크한 문서에는 성공률 언급이 전혀 없습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="근거 없는 의료 효과 서술이며 의료광고 규제 대상 표현입니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: AI 답변이 가상 하늘별의원의 수상 이력을 말하며 "
                    "관련 없는 지역 뉴스 페이지를 인용했습니다."
                ),
                band=RiskBand.HIGH,
                why_ko="출처가 문장을 뒷받침하지 않지만 규제 영역은 아닙니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.CITATION_COMPLETENESS,
        name_ko="인용 충실도",
        definition_ko=(
            "확인이 필요한 문장에 출처가 붙어 있는지. 출처 없는 단정은 독자가 검증할 방법이 "
            "없고, 검증할 수 없는 문장은 반박할 수도 없습니다."
        ),
        base_band=RiskBand.MEDIUM,
        deterministic_ko=(
            "문장에 인용이 하나도 없다는 사실 자체는 규칙으로 판정합니다. "
            "답변에 붙은 인용 목록만 보면 되기 때문입니다."
        ),
        needs_model_ko=(
            "'이 문장이 출처를 필요로 하는 종류인가' 는 언어모델 판정이 필요하며, "
            "판정 결과는 사람 검수로 확정됩니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: AI 답변이 가상 하늘별의원의 비급여 시술 가격을 "
                    "출처 없이 단정했습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="가격 영역 서술이므로 근거 유무와 무관하게 최상위 등급입니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: AI 답변이 가상 하늘별의원을 '지역에서 인기 있는 곳' 이라고 "
                    "출처 없이 말했습니다."
                ),
                band=RiskBand.MEDIUM,
                why_ko="틀린 문장은 아니지만 독자가 확인할 수단이 없습니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.ENTITY_DISAMBIGUATION,
        name_ko="동일 업체 식별",
        definition_ko=(
            "AI 답변이 말하는 대상이 정말 우리 고객인지. 같은 상호를 쓰는 다른 지점·다른 "
            "업종이 흔하고, 남의 이야기를 고객의 실적이나 사고로 옮겨 적는 순간 보고서 "
            "전체가 무효가 됩니다."
        ),
        base_band=RiskBand.HIGH,
        deterministic_ko=(
            "사업자등록번호·공식 도메인·전화번호가 답변에 함께 등장해 대조 가능한 경우는 "
            "규칙으로 판정합니다."
        ),
        needs_model_ko=(
            "이름만 등장할 때의 동일성 판단은 언어모델을 거치되, 확정은 사람 검수 큐로 "
            "넘깁니다. 추측으로 확정하지 않습니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: 동명의 다른 지역 '가상 하늘별의원' 의 행정처분 기사를 "
                    "AI 답변이 우리 고객의 이력으로 서술했습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="남의 법적 문제를 고객에게 귀속시킨 법률 영역 오류입니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: 폐업한 동명 의원의 옛 주소를 우리 고객의 위치로 "
                    "AI 답변이 안내했습니다."
                ),
                band=RiskBand.HIGH,
                why_ko="대상 식별이 틀렸고 환자가 엉뚱한 곳으로 갑니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.RECOMMENDATION_INCLUSION,
        name_ko="추천 포함",
        definition_ko=(
            "고객이 추천 목록에 들어가지 말아야 할 자리에 들어갔는지. 취급하지 않는 시술의 "
            "추천 목록에 오르면 방문한 환자가 헛걸음합니다."
        ),
        base_band=RiskBand.MEDIUM,
        deterministic_ko=(
            "고객이 공개한 진료과목 목록과 대조하여 취급 여부를 규칙으로 확인합니다."
        ),
        needs_model_ko="추천의 맥락과 어조 판단은 언어모델이 필요합니다.",
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: 가상 하늘별의원은 소아 진료를 하지 않는데 "
                    "'소아 진료 추천 병원' 목록에 올랐습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="제공하지 않는 진료 영역이므로 의료 영역 오류입니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: 가상 하늘별의원이 인접 시 지역 추천 목록에 "
                    "포함되었습니다."
                ),
                band=RiskBand.MEDIUM,
                why_ko="틀린 정보는 아니지만 문의 품질을 떨어뜨립니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.RECOMMENDATION_EXCLUSION,
        name_ko="추천 누락",
        definition_ko=(
            "고객이 당연히 들어가야 할 추천 목록에서 빠졌는지. 노출의 손실이며, "
            "틀린 문장이 아니라 없는 문장의 문제입니다."
        ),
        base_band=RiskBand.MEDIUM,
        deterministic_ko=(
            "답변 본문과 인용 목록에 고객 이름·도메인이 등장하지 않았다는 사실은 "
            "규칙으로 판정합니다."
        ),
        needs_model_ko=(
            "'이 질문이 고객이 들어갔어야 할 질문인가' 의 판단은 언어모델이 필요합니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: 가상 하늘별의원이 있는 동네의 야간진료 추천 질문에서 "
                    "경쟁 병원 세 곳만 언급되고 고객은 빠졌습니다."
                ),
                band=RiskBand.MEDIUM,
                why_ko="사실 오류는 없으나 얻어야 할 노출을 잃고 있습니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.SENTIMENT_WITH_GROUNDS,
        name_ko="근거 있는 부정 서술",
        definition_ko=(
            "AI 답변의 부정적 서술과, 그 서술이 근거로 삼은 문서. 감정만 세는 것은 "
            "쓸모가 없습니다 — 부정 서술은 어디서 왔는지와 함께여야 대응할 수 있습니다."
        ),
        base_band=RiskBand.MEDIUM,
        deterministic_ko="부정 서술이 인용한 출처 URL의 존재 여부는 규칙으로 확인합니다.",
        needs_model_ko=(
            "어조가 부정인지, 그 부정이 인용 문서에서 실제로 도출되는지는 언어모델 판정이며 "
            "사람 검수 없이는 고객 보고서에 실리지 않습니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: AI 답변이 가상 하늘별의원에 대해 '부작용 대응이 미흡하다는 "
                    "평가가 있다' 고 서술하고 출처로 무관한 커뮤니티 글을 들었습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="부작용 대응은 의료 영역 서술이며 근거도 문장을 뒷받침하지 않습니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: AI 답변이 가상 하늘별의원을 '대기 시간이 길다' 고 서술하고 "
                    "실제 후기 페이지를 인용했습니다."
                ),
                band=RiskBand.MEDIUM,
                why_ko="근거가 있는 부정 서술이므로 정정이 아니라 운영 대응 대상입니다.",
            ),
        ),
    ),
    RiskKindSpec(
        kind=RiskKind.STALENESS,
        name_ko="시점 낙후",
        definition_ko=(
            "AI 답변이 지금은 맞지 않는 과거 정보를 현재형으로 말하는지. 과거에 참이었다는 "
            "점 때문에 사실 오류보다 발견이 늦습니다."
        ),
        base_band=RiskBand.LOW,
        deterministic_ko=(
            "고객이 게시한 최신 값과 답변 속 값이 다르고, 게시 이력에 과거 값으로 존재하면 "
            "규칙으로 '낙후' 판정입니다."
        ),
        needs_model_ko=(
            "이력이 없는 서술형 정보의 낙후 여부는 언어모델 판정이 필요합니다."
        ),
        examples=(
            WorkedExample(
                situation_ko=(
                    "가상 사례: 가상 하늘별의원이 3개월 전 인상한 비급여 가격을 "
                    "AI 답변이 옛 가격으로 안내했습니다."
                ),
                band=RiskBand.FATAL,
                why_ko="가격 영역이므로 낙후라 해도 최상위 등급입니다.",
            ),
            WorkedExample(
                situation_ko=(
                    "가상 사례: 작년에 종료된 가상 하늘별의원 건강강좌를 "
                    "AI 답변이 진행 중이라고 안내했습니다."
                ),
                band=RiskBand.LOW,
                why_ko="즉각적인 피해가 없고 표현·시점의 문제입니다.",
            ),
        ),
    ),
)


#: The published taxonomy. Import this; do not rebuild it at a call site.
RISK_TAXONOMY = RiskTaxonomy(
    version=TAXONOMY_VERSION,
    kinds=_KINDS,
    regulated_domains=REGULATED_DOMAINS,
    # 치명 and 높음 may not be published unreviewed. 중간 and 낮음 may, with a caveat —
    # holding back every low finding until a human reads it would mean nothing ships,
    # and a queue nobody can clear is a queue nobody reads.
    review_required_at_or_above=RiskBand.HIGH,
)


__all__ = [
    "BAND_SEVERITY",
    "FICTIONAL_EXAMPLE_MARKER",
    "REGULATED_DOMAINS",
    "RISK_TAXONOMY",
    "TAXONOMY_VERSION",
    "ClaimDomain",
    "RiskBand",
    "RiskKind",
    "RiskKindSpec",
    "RiskTaxonomy",
    "WorkedExample",
]
