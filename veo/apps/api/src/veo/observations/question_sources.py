"""질문을 **어디서 가져오는가** — 지어내지 않고 사람이 실제로 쓴 것을 모은다.

## 왜 이것이 필요한가

관측의 질문 집합은 "환자가 실제로 무엇을 묻는가" 여야 한다. 그런데 2026-08-08 까지
화면에 있던 예시 질문은 **내가 지어낸 것**이었다(`docs/CORRECTIONS.md` 13번과 같은
기제 — 빈칸을 보면 그럴듯한 값으로 메운다). 지어낸 질문으로 잰 노출률은 지어낸 세계의
노출률이다.

## 출처는 여럿이고, 못 쓰는 출처도 목록에 남는다

이 저장소가 AI 엔진을 다루는 방식과 같다(`observations/providers/registry.py`):

> 쓸 수 있는 엔진만 돌려주지 않는다. **아는 엔진을 전부** 돌려주고 각각 왜 쓸 수
> 있는지·없는지를 함께 준다. 못 쓰는 엔진을 목록에서 빼면 '여기 있는 게 전부' 로
> 읽히고, 자격증명만 넣으면 잴 수 있었던 것을 아무도 모른 채 지나간다.

질문 출처도 똑같다. 지금 SerpAPI 열쇠가 없다고 구글 관련질문을 **설계에서 빼면**,
열쇠가 생기는 날 화면에 그것을 놓을 자리가 없다. 그래서 출처는 처음부터 여럿이고,
열쇠가 없는 출처는 `DISABLED_NO_CREDENTIAL` 로 목록에 남는다.

## 중복에 대한 예외

같은 수집을 베놈 ERP 의 환자질문분석(PAA)이 이미 한다. 지침서 0-D 는 "있는 것을 다시
만들지 않는다" 이고, 이것은 그 예외다 — **사장님 결정(2026-08-08)**:

    "별도로 움직일 수 있도록 만들어줘. 중복에 대한건 이번만 예외로 하자.
     가능하면 veo가 별도로 완전하게 작동했으면 좋겠어."

VEO 가 ERP 없이 혼자 서야 한다는 것이 이유다. 다만 0-D 가 경고한 위험은 그대로
남는다 — **나중에 만든 쪽이 원본의 제약을 모른 채 더 관대해진다.** 그래서 ERP 가 하는
방식을 그대로 따르고, 다른 곳만 아래에 적는다.

## ERP 와 맞춘 것 · 다른 것

`erp/src/app/api/journeymap/paa/route.ts` 의 `fetchNaverKin` · `fetchGooglePaa` 를 읽고
맞췄다.

| | ERP | 여기 |
|---|---|---|
| 지식iN | `kin.json` · `display=100` · `title` · `stripHtml` · 5자 이상 | 같음 |
| 구글 | SerpAPI `engine=google&hl=ko&gl=kr` · `related_questions[].question` · 5자 이상 | 같음 |
| 구글 질의 | 지역·주제를 갈라 `"{지역} {주제}"` 로 재조합 | **안 함** — 아래 참조 |
| AI 분류 | Anthropic 으로 여정단계 배정 | **안 함** — 아래 참조 |
| 중복 | 안 거름 | **거른다** — 아래 참조 |

**질의 재조합을 안 하는 이유.** ERP 는 `parseRegion` 으로 지역 사전을 들고 있다. 그
사전이 여기 없고, 없는 사전을 흉내 내면 "대구임플란트" 를 잘못 갈라 엉뚱한 질의를
던진다. 사람이 넣은 말을 그대로 던진다 — 지역을 붙일지는 넣는 사람이 정한다.

**AI 분류를 안 하는 이유.** 의도·퍼널을 AI 가 자동 배정하면 그것도 근거 없는 값이
된다. 질문은 실제로 수집한 것인데 분류는 지어낸 것이 되고, 그 분류가 집합의 균형
판정(ADR 0015)을 통과시킨다. **고르고 분류하는 것은 사람이 한다.**

**중복을 거르는 이유.** 지식iN 은 비슷한 제목을 여럿 돌려준다. 같은 질문이 집합에 두
번 들어가면 그 질문의 결과가 두 번 세어져 노출률이 그쪽으로 기운다. **글자가 완전히
같은 것만** 거른다 — 비슷한 것을 묶는 것은 판단이고, 판단은 사람이 화면에서 한다.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final, final

import httpx

from veo.common.http import read_capped
from veo.contracts.enums import ProviderState
from veo.providers.naver.errors import NaverResponseTooLargeError
from veo.providers.naver.search import NaverSearchClient, strip_markup

#: 지식iN 이 한 번에 돌려주는 최대 개수. ERP 와 같다.
KIN_DISPLAY: Final = 100

#: 이보다 짧은 제목은 질문으로 보지 않는다. ERP 의 `filter((t) => t.length >= 5)` 와 같다.
MIN_QUESTION_LENGTH: Final = 5

SERPAPI_BASE_URL: Final = "https://serpapi.com"
SERPAPI_TIMEOUT_SECONDS: Final = 8.0
SERPAPI_MAX_RESPONSE_BYTES: Final = 1024 * 1024

NAVER_KIN: Final = "naver_kin"
GOOGLE_PAA: Final = "google_paa"

#: 아는 출처 전부. 못 쓰는 것도 여기 남는다.
SOURCE_LABELS_KO: Final[dict[str, str]] = {
    NAVER_KIN: "네이버 지식iN",
    GOOGLE_PAA: "구글 관련 질문",
}

_STATE_REASONS_KO: Final[dict[ProviderState, str]] = {
    ProviderState.ENABLED: "조회할 수 있습니다.",
    ProviderState.DISABLED_NO_CREDENTIAL: (
        "자격증명이 없어 조회하지 않았습니다. 열쇠를 넣으면 이 출처가 켜집니다."
    ),
}


@final
@dataclass(frozen=True, slots=True)
class CollectedQuestion:
    """실제로 누군가 쓴 질문 한 줄.

    `url` 을 함께 들고 다니는 이유: 나중에 "이 질문 어디서 나왔냐" 를 물었을 때 답할 수
    있어야 한다. 출처를 안 남기면 수집한 것과 지어낸 것이 다시 구분되지 않는다.
    구글 관련질문은 원문 주소를 주지 않으므로 빈 문자열이다.
    """

    text: str
    source: str
    url: str = ""


@final
@dataclass(frozen=True, slots=True)
class SourceHarvest:
    """출처 하나의 결과, 또는 왜 못 했는지.

    실패해도 예외를 던지지 않는다. 출처 하나가 안 되는 것과 질문이 없는 것은 다른
    사실이고, 화면은 그 둘을 구분해 보여줘야 한다.
    """

    source: str
    label_ko: str
    state: ProviderState
    state_reason_ko: str
    questions: tuple[CollectedQuestion, ...] = ()
    #: 출처가 보고한 전체 건수. 가져온 개수와 다르다 — 그 차이를 화면에 적는다.
    total: int = 0
    #: 길이 미달·중복으로 버린 개수. 조용히 줄어들면 "이것이 전부" 로 읽힌다.
    dropped: int = 0
    failure_reason_ko: str | None = None
    notes_ko: tuple[str, ...] = field(default_factory=tuple)


@final
@dataclass(frozen=True, slots=True)
class QuestionHarvest:
    """한 번의 수집. **아는 출처를 전부** 담는다."""

    query: str
    sources: tuple[SourceHarvest, ...] = ()

    @property
    def questions(self) -> tuple[CollectedQuestion, ...]:
        """출처를 가로질러 중복을 뺀 전체 목록. 먼저 온 출처가 이긴다."""
        seen: set[str] = set()
        out: list[CollectedQuestion] = []
        for source in self.sources:
            for question in source.questions:
                if question.text in seen:
                    continue
                seen.add(question.text)
                out.append(question)
        return tuple(out)


def _accept(text: str, seen: set[str]) -> bool:
    return len(text) >= MIN_QUESTION_LENGTH and text not in seen


def _size_note(total: int, looked: int) -> list[str]:
    if total > looked:
        # 1,779건 중 100건만 봤다는 사실을 숨기지 않는다. 숨기면 화면의 목록이
        # "환자가 묻는 질문 전부" 로 읽힌다.
        return [
            f"출처가 보고한 전체 {total:,}건 중 상위 {looked:,}건만 가져왔습니다. "
            "한 번 조회의 상한입니다."
        ]
    return []


def collect_from_naver_kin(
    client: NaverSearchClient, query: str, *, display: int = KIN_DISPLAY
) -> SourceHarvest:
    """지식iN 에서 질문을 모은다."""
    label = SOURCE_LABELS_KO[NAVER_KIN]
    if client.state is not ProviderState.ENABLED:
        return SourceHarvest(
            source=NAVER_KIN,
            label_ko=label,
            state=client.state,
            state_reason_ko=_STATE_REASONS_KO.get(
                client.state, "지금은 조회할 수 없습니다."
            ),
        )

    outcome = client.look_up(query, corpora=("kin",), display=display)

    seen: set[str] = set()
    questions: list[CollectedQuestion] = []
    dropped = 0
    for item in outcome.items:
        text = item.title.strip()
        if not _accept(text, seen):
            dropped += 1
            continue
        seen.add(text)
        questions.append(CollectedQuestion(text=text, source=NAVER_KIN, url=item.url))

    total = int(outcome.totals.get("kin", 0))
    notes = _size_note(total, len(questions) + dropped)
    if dropped:
        notes.append(f"너무 짧거나 글자가 똑같은 {dropped:,}건은 뺐습니다.")

    return SourceHarvest(
        source=NAVER_KIN,
        label_ko=label,
        state=ProviderState.ENABLED,
        state_reason_ko=_STATE_REASONS_KO[ProviderState.ENABLED],
        questions=tuple(questions),
        total=total,
        dropped=dropped,
        failure_reason_ko=(
            outcome.unavailable.get("kin") or outcome.unavailable.get("*")
            if outcome.unavailable and not questions
            else None
        ),
        notes_ko=tuple(notes),
    )


def collect_from_google_paa(
    api_key: str | None,
    query: str,
    *,
    transport: httpx.BaseTransport | None = None,
    base_url: str = SERPAPI_BASE_URL,
) -> SourceHarvest:
    """구글 검색 결과의 '관련 질문' 을 모은다 (SerpAPI 경유).

    **열쇠가 없어도 목록에서 사라지지 않는다.** 상태와 이유를 담아 돌려주고, 화면은
    "열쇠를 넣으면 켜집니다" 라고 적는다 — 그래야 열쇠가 생기는 날 아무도 이 출처를
    잊지 않는다.
    """
    label = SOURCE_LABELS_KO[GOOGLE_PAA]
    if not (api_key or "").strip():
        return SourceHarvest(
            source=GOOGLE_PAA,
            label_ko=label,
            state=ProviderState.DISABLED_NO_CREDENTIAL,
            state_reason_ko=_STATE_REASONS_KO[ProviderState.DISABLED_NO_CREDENTIAL],
        )

    cleaned = query.strip()
    enabled = SourceHarvest(
        source=GOOGLE_PAA,
        label_ko=label,
        state=ProviderState.ENABLED,
        state_reason_ko=_STATE_REASONS_KO[ProviderState.ENABLED],
    )
    if not cleaned:
        return enabled

    try:
        payload = _serpapi_request(api_key or "", cleaned, transport, base_url)
    except (httpx.HTTPError, NaverResponseTooLargeError, ValueError) as exc:
        # 이 출처가 안 된다고 나머지를 버리지 않는다.
        return SourceHarvest(
            source=GOOGLE_PAA,
            label_ko=label,
            state=ProviderState.ENABLED,
            state_reason_ko=_STATE_REASONS_KO[ProviderState.ENABLED],
            failure_reason_ko=f"구글 관련 질문을 가져오지 못했습니다 ({type(exc).__name__}).",
        )

    raw: Sequence[Any] = payload.get("related_questions") or ()
    seen: set[str] = set()
    questions: list[CollectedQuestion] = []
    dropped = 0
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        text = strip_markup(str(entry.get("question") or "")).strip()
        if not _accept(text, seen):
            dropped += 1
            continue
        seen.add(text)
        questions.append(
            CollectedQuestion(
                text=text, source=GOOGLE_PAA, url=str(entry.get("link") or "")
            )
        )

    notes = [f"너무 짧거나 글자가 똑같은 {dropped:,}건은 뺐습니다."] if dropped else []
    return SourceHarvest(
        source=GOOGLE_PAA,
        label_ko=label,
        state=ProviderState.ENABLED,
        state_reason_ko=_STATE_REASONS_KO[ProviderState.ENABLED],
        questions=tuple(questions),
        total=len(questions) + dropped,
        dropped=dropped,
        notes_ko=tuple(notes),
    )


def _serpapi_request(
    api_key: str, query: str, transport: httpx.BaseTransport | None, base_url: str
) -> dict[str, Any]:
    with httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(SERPAPI_TIMEOUT_SECONDS),
        follow_redirects=False,
    ) as client:
        response = client.send(
            client.build_request(
                "GET",
                f"{base_url}/search",
                # ERP 와 같은 값. 한국어·한국 지역으로 고정하지 않으면 다른 나라의
                # 관련 질문이 섞인다.
                params={
                    "engine": "google",
                    "q": query,
                    "hl": "ko",
                    "gl": "kr",
                    "api_key": api_key,
                },
            ),
            stream=True,
        )
        try:
            response.raise_for_status()
            body = read_capped(
                response, SERPAPI_MAX_RESPONSE_BYTES, NaverResponseTooLargeError
            )
        finally:
            response.close()

    parsed = json.loads(body.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("SerpAPI 응답이 객체가 아닙니다")
    return parsed


def harvest_questions(
    query: str,
    *,
    naver_client: NaverSearchClient,
    serpapi_key: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> QuestionHarvest:
    """아는 출처를 **전부** 돌고, 각각의 결과와 상태를 함께 돌려준다."""
    cleaned = query.strip()
    return QuestionHarvest(
        query=cleaned,
        sources=(
            collect_from_naver_kin(naver_client, cleaned),
            collect_from_google_paa(serpapi_key, cleaned, transport=transport),
        ),
    )


__all__ = [
    "GOOGLE_PAA",
    "KIN_DISPLAY",
    "MIN_QUESTION_LENGTH",
    "NAVER_KIN",
    "SOURCE_LABELS_KO",
    "CollectedQuestion",
    "QuestionHarvest",
    "SourceHarvest",
    "collect_from_google_paa",
    "collect_from_naver_kin",
    "harvest_questions",
]
