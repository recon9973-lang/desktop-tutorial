"""질문은 **가져오는 것**이지 지어내는 것이 아니다.

2026-08-08 까지 질문 집합 화면의 예시 질문 14개는 내가 지어낸 것이었다
(`docs/CORRECTIONS.md`). 지어낸 질문으로 잰 노출률은 지어낸 세계의 노출률이다.

여기서 지키는 것 셋:

* **못 쓰는 출처가 목록에서 사라지지 않는다.** 사라지면 "여기 있는 게 전부" 로 읽히고,
  열쇠만 넣으면 얻을 수 있었던 질문을 아무도 모른 채 지나간다.
* **줄어든 개수를 숨기지 않는다.** 1,779건 중 100건만 봤다는 사실이 안 보이면 화면의
  목록이 "환자가 묻는 질문 전부" 로 읽힌다.
* **출처가 하나 실패해도 나머지는 산다.**
"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from veo.contracts.enums import ProviderState
from veo.observations.question_sources import (
    GOOGLE_PAA,
    MIN_QUESTION_LENGTH,
    NAVER_KIN,
    collect_from_google_paa,
    harvest_questions,
)
from veo.providers.naver.datalab import DataLabCredentials
from veo.providers.naver.search import NaverSearchClient

# HTTP 헤더로 나가는 값이라 ASCII 여야 한다. 한글을 넣으면 httpx 가 인코딩에서 막는다.
CREDENTIALS = DataLabCredentials(
    client_id=SecretStr("synthetic-id"), client_secret=SecretStr("synthetic-secret")
)


def kin_response(titles: list[str], *, total: int | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "total": total if total is not None else len(titles),
            "items": [
                {"title": title, "link": f"https://kin.naver.com/{index}"}
                for index, title in enumerate(titles)
            ],
        },
    )


def naver_client(handler: object) -> NaverSearchClient:
    return NaverSearchClient(
        credentials=CREDENTIALS,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


def serpapi(questions: list[str]) -> object:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"related_questions": [{"question": q} for q in questions]}
        )

    return handler


class TestEveryKnownSourceStaysInTheList:
    def test_google_without_a_key_is_reported_not_hidden(self) -> None:
        """열쇠가 없다고 목록에서 빼면, 열쇠가 생기는 날 아무도 이 출처를 떠올리지 않는다."""
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=naver_client(lambda request: kin_response(["마산 한의원 추천해주세요"])),
            serpapi_key=None,
        )

        sources = {source.source: source for source in harvest.sources}

        assert set(sources) == {NAVER_KIN, GOOGLE_PAA}
        assert sources[GOOGLE_PAA].state is ProviderState.DISABLED_NO_CREDENTIAL
        assert "열쇠" in sources[GOOGLE_PAA].state_reason_ko

    def test_naver_without_credentials_is_reported_too(self) -> None:
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=NaverSearchClient(credentials=None),
            serpapi_key=None,
        )

        naver = next(s for s in harvest.sources if s.source == NAVER_KIN)

        assert naver.state is not ProviderState.ENABLED
        assert naver.questions == ()


class TestWhatWasDroppedIsSaid:
    def test_the_gap_between_total_and_fetched_is_written_down(self) -> None:
        """네이버는 1,779건이 있다고 하고 100건만 준다. 그 차이가 안 보이면 목록이
        '환자가 묻는 질문 전부' 로 읽힌다."""
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=naver_client(
                lambda request: kin_response(["마산 한의원 어디가 좋을까요"], total=1779)
            ),
            serpapi_key=None,
        )

        naver = next(s for s in harvest.sources if s.source == NAVER_KIN)

        assert naver.total == 1779
        assert any("1,779" in note for note in naver.notes_ko)

    def test_short_titles_are_dropped_and_counted(self) -> None:
        titles = ["가나다", "마산 한의원 추천 부탁드립니다"]
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=naver_client(lambda request: kin_response(titles)),
            serpapi_key=None,
        )

        naver = next(s for s in harvest.sources if s.source == NAVER_KIN)

        assert len(naver.questions) == 1
        assert naver.dropped == 1
        assert len("가나다") < MIN_QUESTION_LENGTH

    def test_exact_duplicates_are_dropped(self) -> None:
        """같은 질문이 집합에 두 번 들어가면 그 질문의 결과가 두 번 세어져 노출률이
        그쪽으로 기운다."""
        same = "마산 교통사고 한의원 추천 부탁합니다"
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=naver_client(lambda request: kin_response([same, same, same])),
            serpapi_key=None,
        )

        naver = next(s for s in harvest.sources if s.source == NAVER_KIN)

        assert len(naver.questions) == 1
        assert naver.dropped == 2


class TestTheProvenanceSurvives:
    def test_each_question_keeps_where_it_came_from(self) -> None:
        """출처를 안 남기면 수집한 것과 지어낸 것이 다시 구분되지 않는다."""
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=naver_client(lambda request: kin_response(["마산 한의원 추천해주세요"])),
            serpapi_key=None,
        )

        question = harvest.questions[0]

        assert question.source == NAVER_KIN
        assert question.url.startswith("https://kin.naver.com/")


class TestOneSourceFailingDoesNotKillTheRest:
    def test_a_naver_error_leaves_google_alone(self) -> None:
        harvest = harvest_questions(
            "마산 한의원",
            naver_client=naver_client(lambda request: httpx.Response(500)),
            serpapi_key="synthetic-key",
            transport=httpx.MockTransport(serpapi(["마산 한의원 어디가 잘하나요"])),  # type: ignore[arg-type]
        )

        google = next(s for s in harvest.sources if s.source == GOOGLE_PAA)

        assert len(google.questions) == 1
        assert google.state is ProviderState.ENABLED

    def test_a_serpapi_error_is_reported_without_raising(self) -> None:
        source = collect_from_google_paa(
            "synthetic-key",
            "마산 한의원",
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),  # type: ignore[arg-type]
        )

        assert source.questions == ()
        assert source.failure_reason_ko is not None


class TestGoogleMatchesWhatWeMeasured:
    def test_it_asks_google_in_korean_for_korea(self) -> None:
        """ERP 와 같은 값이다. 고정하지 않으면 다른 나라의 관련 질문이 섞인다."""
        seen: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen.update(dict(request.url.params))
            return httpx.Response(200, json={"related_questions": []})

        collect_from_google_paa(
            "synthetic-key", "마산 한의원", transport=httpx.MockTransport(handler)
        )

        assert seen["engine"] == "google"
        assert seen["hl"] == "ko"
        assert seen["gl"] == "kr"

    def test_it_reads_related_questions(self) -> None:
        source = collect_from_google_paa(
            "synthetic-key",
            "마산 한의원",
            transport=httpx.MockTransport(serpapi(["교통사고 한의원 치료 기간은?"])),  # type: ignore[arg-type]
        )

        assert [q.text for q in source.questions] == ["교통사고 한의원 치료 기간은?"]
        assert source.questions[0].source == GOOGLE_PAA


def test_an_empty_query_asks_nothing() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError("빈 질의로 외부를 부르면 안 됩니다")

    harvest = harvest_questions(
        "   ", naver_client=naver_client(refuse), serpapi_key=None
    )

    assert harvest.questions == ()


def test_the_payload_shape_is_json_safe() -> None:
    """화면으로 나가는 값이다. 직렬화가 안 되면 화면이 통째로 안 뜬다."""
    harvest = harvest_questions(
        "마산 한의원",
        naver_client=naver_client(lambda request: kin_response(["마산 한의원 추천해주세요"])),
        serpapi_key=None,
    )

    body = json.dumps(
        {
            "query": harvest.query,
            "sources": [
                {
                    "source": s.source,
                    "state": str(s.state),
                    "questions": [q.text for q in s.questions],
                }
                for s in harvest.sources
            ],
        },
        ensure_ascii=False,
    )

    assert "마산" in body


@pytest.mark.parametrize("state", [ProviderState.DISABLED_NO_CREDENTIAL])
def test_a_disabled_source_never_pretends_to_have_zero_questions(
    state: ProviderState,
) -> None:
    """'열쇠가 없다' 와 '질문이 없다' 는 다른 사실이다. 화면이 둘을 구분할 수 있어야 한다."""
    source = collect_from_google_paa(None, "마산 한의원")

    assert source.state is state
    assert source.questions == ()
    assert source.total == 0
    # 상태 이유가 비어 있으면 화면은 "질문 0개" 로만 그린다.
    assert source.state_reason_ko != ""
