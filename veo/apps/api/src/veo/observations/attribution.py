"""관측 파이프라인이 쓰는 언급 판별기 — 동명 업체를 구분하는 쪽.

## 왜 이 파일이 생겼나

판별기가 **둘**이었고, 실제로 돌고 있던 쪽이 느슨한 쪽이었다.

`SubstringMentionDetector` 는 브랜드 이름이 답변 문자열 안에 들어 있으면 언급으로
세었다. 그것뿐이었다. 실측:

    답변: "부산 해운대구의 백세온담한의원이 유명합니다."
    고객: 온담한의원 (서울 강남구)
    →  옛 판별기: mentioned=True      ← 다른 병원이다
       이 판별기: NEEDS_REVIEW (0.00) ← 사람에게 넘긴다

한국 병원 상호는 겹친다. `서울치과`·`중앙병원`·`연세의원` 은 저마다 수십 곳이고,
`온담한의원` 처럼 고유한 이름조차 `백세온담한의원` 같은 더 긴 상호에 통째로 들어간다.
부분 문자열로 세면 틀리는 방향이 **항상 위쪽**이다 — 노출률이 실제보다 좋아 보이고,
고객은 그 사실을 확인할 방법이 없다.

`veo.observations.detection` 은 이 문제를 풀라고 만들어 둔 것이었고, 완성되어 있었고,
`src/` 안에서 아무도 부르지 않았다. 지침서 0-D 가 말하는 상태 그대로다 — 두 벌이 서로
다르게 판단하기 시작한다. #20(노출 지표 모듈이 둘이었다)과 같은 모양이며, 그때와 같이
**느슨한 쪽을 지운다.** 남겨 두면 다음 사람이 둘 중 하나를 고르게 된다.

## 버려지고 있던 것

`brand_identities` 테이블은 주소·전화번호·구별 표현을 이미 받아 저장하고 있었다.
옛 판별기는 이름과 도메인만 읽었으므로, **고객이 등록한 전화번호는 측정에 한 번도
쓰이지 않았다.** 그 전화번호가 흔한 상호를 확정선 위로 올리는 유일한 항목이다
(`brand_identity` 의 실측표 참조).

## 판정이 셋이 된다

부분 문자열 판별기의 답은 둘이었다(언급이다/아니다). 여기서는 셋이다.

* `CONFIRMED` — 이 고객이라고 말할 수 있다. 노출률의 분자로 센다.
* `NEEDS_REVIEW` — 이름은 나왔지만 이 고객인지 갈리지 않는다. **분자로 세지 않는다.**
  추측해서 세면 틀리는 방향이 한쪽으로만 몰린다.
* `NOT_FOUND` — 이름이 없다.

보류를 언급으로 세지 않으므로 노출률은 **확정 하한**이 된다. 그 사실은 숨기지 않고
비율 옆에 보류 건수로 함께 나간다(`runs.aggregate_rate`). 보류를 조용히 0으로 접으면
"안 나왔다" 와 "누구인지 모르겠다" 가 화면에서 같은 모양이 된다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from veo.observations.detection.competitors import detect_answer
from veo.observations.detection.disambiguation import BrandProfile
from veo.observations.detection.mentions import MentionEvent, SpanSource
from veo.observations.detection.mentions import MentionVerdict as DetectionVerdict
from veo.observations.providers.base import CitationSupport
from veo.observations.providers.storage import RecordedAnswer
from veo.observations.runner import BrandSighting, MentionVerdict

__all__ = ["DisambiguatingMentionDetector"]


def _sighting(event: MentionEvent) -> BrandSighting:
    """탐지 결과 하나를 실행 기록이 들고 다니는 모양으로."""
    # 본문에서 걸린 자리만 근거로 쓴다. 인용 구간의 좌표는 URL 문자열을 가리키므로
    # 원문 답변에 대고 잘라내면 엉뚱한 글자가 나온다.
    prose = next(
        (span for span in event.spans if span.source is SpanSource.ANSWER_TEXT), None
    )
    return BrandSighting(
        entity_key=event.entity_key,
        is_own_brand=event.is_own_brand,
        competitor_id=event.competitor_id,
        mentioned=event.verdict is DetectionVerdict.CONFIRMED,
        cited=event.is_cited,
        needs_review=event.verdict is DetectionVerdict.NEEDS_REVIEW,
        confidence=event.match_confidence if event.spans else None,
        evidence_ko=event.evidence_ko,
        first_position=prose.start if prose else None,
        evidence_quote=prose.quote if prose else "",
        raw_occurrence_count=event.raw_occurrence_count if event.spans else 0,
    )


@final
@dataclass(frozen=True, slots=True)
class DisambiguatingMentionDetector:
    """`veo.observations.detection` 을 관측 실행기의 판별기 자리에 끼운다.

    이 클래스가 하는 일은 어댑터뿐이다. 판단은 전부 `detection` 안에 있고, 여기서
    다시 하지 않는다 — 규칙이 두 곳에 생기는 순간 다시 갈라지기 시작한다.

    ## 경쟁사도 **같은 호출**로 본다

    점유율은 비율이고, 비율은 그것을 이루는 두 숫자만큼만 정직하다. 우리 브랜드를
    후하게 세고 경쟁사를 깐깐하게 세면 **산술을 한 글자도 안 고치고** 모든 점유율이
    우리 쪽으로 기운다. 그리고 누가 감사를 한다면 들여다볼 곳은 산술이다.

    그래서 `detect_answer` 하나를 부른다. 우리 쪽만 따로 부르는 경로를 남겨 두면
    언젠가 두 쪽이 다른 규칙으로 갈라진다 — "경쟁사를 설명하는 문장 안에서만 나왔다"
    같은 감점 신호는 양쪽에 대칭으로 걸려야 뜻이 있다.
    """

    profile: BrandProfile
    #: 이 프로젝트가 선언한 경쟁사들. 비어 있으면 점유율을 낼 수 없다 — 그때는 낼 수
    #: 없다고 말하지, 우리만 있는 100% 를 만들지 않는다.
    competitors: tuple[BrandProfile, ...] = ()

    def judge(self, record: RecordedAnswer) -> MentionVerdict:
        # 인용은 **구조화된 인용을 돌려준 응답에서만** 센다. 본문에 우리 주소가 적혀
        # 있는 것은 그 엔진이 우리를 근거로 삼았다는 증거가 아니다.
        citations = (
            record.citations
            if record.citation_support is CitationSupport.STRUCTURED
            else ()
        )

        detected = detect_answer(
            record.text,
            own=self.profile,
            competitors=self.competitors,
            citations=citations,
        )
        own = _sighting(detected.own)

        return MentionVerdict(
            mentioned=own.mentioned,
            # 확정되지 않은 언급 위에 인용을 세울 수 없다. 누구인지 모르는 이름에
            # 붙은 인용은 그 사람의 인용이 아니다.
            cited=own.cited,
            matched_entities=(own.entity_key,) if own.mentioned else (),
            needs_review=own.needs_review,
            confidence=own.confidence,
            evidence_ko=own.evidence_ko,
            first_position=own.first_position,
            evidence_quote=own.evidence_quote,
            raw_occurrence_count=own.raw_occurrence_count,
            sightings=(own, *(_sighting(event) for event in detected.competitors)),
        )
