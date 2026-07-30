"""띄어쓰기가 들어간 키워드 — 한국어 검색어의 대부분.

## 실측으로 잡은 결함

화면을 붙이기 전에 실제 네이버를 불러 봤더니 이랬다.

    hintKeywords=강남 한의원   → HTTP 400
    hintKeywords=강남한의원    → HTTP 200

그리고 우리 코드는 그 400 을 **"네이버 응답 형식이 VEO가 아는 형식과 다릅니다"** 로
보고하고 있었다. 형식은 멀쩡했다. 우리가 보낸 값이 규격에 안 맞았을 뿐이다.

세 층이 동시에 틀려 있었다.

1. 요청: 띄어쓰기를 그대로 보냈다 → 400
2. 설명: 400 을 응답 형식 오류로 분류했다 → 고치는 사람이 네이버 문서를 뒤지게 된다
3. 매칭: 네이버는 띄어쓰기를 뗀 형태로 답하는데(`강남한의원`) 우리는 띄어쓰기가 있는
   표준형과 비교했다 → 설령 200 을 받았어도 **요청한 키워드 자신이 매칭되지 않고**,
   그 자리가 "측정 불가" 로 뜨면서 정작 그 키워드가 연관 키워드 목록에 나타난다

한국어 검색 키워드는 대부분 띄어쓰기가 있다. 즉 자연스러운 입력이 사실상 전부 막혀
있었고, 화면만 붙였다면 "네이버 연동이 안 된다" 로 보였을 것이다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from veo.keywords.normalize import normalize_keyword, searchad_hint
from veo.keywords.service import _split_seed_and_related
from veo.providers.naver.errors import (
    NaverRequestRejectedError,
    NaverSchemaError,
    classify_status,
)
from veo.providers.naver.searchad import normalize_keywordstool

COLLECTED_AT = datetime(2026, 7, 31, tzinfo=UTC)


def keywordstool_response(rows: list[dict[str, object]]) -> dict[str, object]:
    """네이버 `/keywordstool` 응답의 최소 형태. 실제 응답에서 필드 이름을 그대로 옮겼다."""
    return {
        "keywordList": [
            {
                "relKeyword": row["relKeyword"],
                "monthlyPcQcCnt": row["monthlyPcQcCnt"],
                "monthlyMobileQcCnt": row["monthlyMobileQcCnt"],
                "plAvgDepth": 10,
                "compIdx": "높음",
                "monthlyAvePcClkCnt": 1.0,
                "monthlyAveMobileClkCnt": 2.0,
                "monthlyAvePcCtr": 0.5,
                "monthlyAveMobileCtr": 0.6,
            }
            for row in rows
        ]
    }


class TestTheFormNaverAccepts:
    def test_inner_spaces_are_removed_for_the_provider(self) -> None:
        assert searchad_hint("강남 한의원") == "강남한의원"
        assert searchad_hint("허리디스크  치료") == "허리디스크치료"

    def test_our_own_normal_form_keeps_the_space(self) -> None:
        """공급자 사정이 우리 저장 형식까지 바꾸면 안 된다.

        사용자가 "강남 한의원" 이라고 입력했으면 보고서에도 그렇게 나와야 한다.
        """
        assert normalize_keyword("강남 한의원") == "강남 한의원"

    def test_a_keyword_without_spaces_is_untouched(self) -> None:
        assert searchad_hint("강남한의원") == "강남한의원"


class TestWhatWeTellSomeoneDebugging:
    def test_a_rejected_request_is_not_reported_as_a_format_change(self) -> None:
        """이 둘을 섞으면 고치는 사람이 정반대 방향을 본다.

        "응답 형식이 다릅니다" 는 네이버가 계약을 바꿨다는 뜻이다. 실제로는 우리가 보낸
        값이 규격에 안 맞는 것이었고, 그 사이 원인은 우리 쪽에 그대로 남는다.
        """
        error = classify_status(400)

        assert isinstance(error, NaverRequestRejectedError)
        assert not isinstance(error, NaverSchemaError)
        assert "요청을 받아들이지 않았습니다" in error.message_ko

    def test_a_genuinely_odd_status_is_still_a_format_surprise(self) -> None:
        """4xx 를 전부 우리 탓으로 돌리는 것도 틀리다. 3xx 는 계약이 이상한 것이다."""
        assert isinstance(classify_status(302), NaverSchemaError)

    def test_the_statuses_we_already_understood_did_not_change(self) -> None:
        for status, fragment in ((401, "자격증명"), (403, "권한"), (429, "한도")):
            assert fragment in classify_status(status).message_ko, status


class TestMatchingTheReplyBackToWhatWasAsked:
    def test_a_spaceless_reply_matches_the_spaced_request(self) -> None:
        """네이버가 "강남한의원" 으로 답해도 "강남 한의원" 을 물은 것이 맞다."""
        response = normalize_keywordstool(
            keywordstool_response(
                [
                    {
                        "relKeyword": "강남한의원",
                        "monthlyPcQcCnt": 940,
                        "monthlyMobileQcCnt": 1830,
                    },
                    {
                        "relKeyword": "강남역한의원",
                        "monthlyPcQcCnt": 850,
                        "monthlyMobileQcCnt": 710,
                    },
                ]
            ),
            collected_at=COLLECTED_AT,
            raw_bytes=b"{}",
        )

        seed, related = _split_seed_and_related(response, "강남 한의원")

        assert seed is not None, "요청한 키워드가 매칭되지 않으면 그 자리가 측정 불가가 된다"
        assert seed.monthly_total_searches.value == 940 + 1830
        assert len(related) == 1

    def test_the_asked_for_keyword_does_not_appear_as_a_related_one(self) -> None:
        """매칭이 안 되면 자기 자신이 연관 키워드 목록에 나타난다 — 실제로 그랬다."""
        response = normalize_keywordstool(
            keywordstool_response(
                [{"relKeyword": "강남한의원", "monthlyPcQcCnt": 940, "monthlyMobileQcCnt": 1830}]
            ),
            collected_at=COLLECTED_AT,
            raw_bytes=b"{}",
        )

        _, related = _split_seed_and_related(response, "강남 한의원")

        assert [one.related_keyword for one in related] == []
