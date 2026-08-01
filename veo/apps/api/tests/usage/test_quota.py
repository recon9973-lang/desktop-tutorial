"""한도까지 얼마나 남았는가.

PageSpeed 는 하루 25,000회까지 무료다. **돈이 아니라 하루가 위험하다** — 넘기면 그날의
모든 고객 진단에서 성능이 측정 불가가 되고, 화면에는 사이트의 문제처럼 보이는 형태로
나타난다.

이 파일이 지키는 것 중 가장 중요한 하나: **조직이 쓴 몫은 남은 양을 말해 주지 않는다.**
한도는 API 키 하나에 걸리고 키는 하나이므로, 한 조직이 태우면 모든 조직이 함께 막힌다.
이 구분을 흐리면 화면이 "우리 조직은 200회밖에 안 썼는데요" 라고 말하는 동안 키는
이미 막혀 있게 된다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from veo.usage.quota import PAGESPEED_DAILY_QUOTA, QuotaUsage

NOW = datetime(2026, 8, 1, 15, 0, tzinfo=UTC)
DAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)


def usage(*, calls: int, mine: int = 0) -> QuotaUsage:
    return QuotaUsage(
        provider="GOOGLE_PAGESPEED",
        calls_today=calls,
        calls_by_this_organization=mine,
        daily_quota=PAGESPEED_DAILY_QUOTA,
        window_start=DAY,
        window_end=DAY + timedelta(days=1),
    )


class TestRemainingIsTheAnswerPeopleNeed:
    def test_a_quiet_day_leaves_almost_everything(self) -> None:
        assert usage(calls=100).remaining == PAGESPEED_DAILY_QUOTA - 100

    def test_the_remaining_count_never_goes_negative(self) -> None:
        """한도를 넘겨도 "-500회 남음" 은 아무 뜻이 없다."""
        assert usage(calls=PAGESPEED_DAILY_QUOTA + 500).remaining == 0

    def test_exhausted_is_recognised(self) -> None:
        assert usage(calls=PAGESPEED_DAILY_QUOTA).is_exhausted is True

    def test_a_warning_comes_before_the_limit_not_after(self) -> None:
        """넘고 나서 알면 그날은 이미 늦었다."""
        assert usage(calls=int(PAGESPEED_DAILY_QUOTA * 0.5)).is_warning is False
        assert usage(calls=int(PAGESPEED_DAILY_QUOTA * 0.85)).is_warning is True
        assert usage(calls=int(PAGESPEED_DAILY_QUOTA * 0.85)).is_exhausted is False


class TestTheOrganisationShareDoesNotAnswerWhatIsLeft:
    """**이 파일에서 가장 중요한 묶음이다.**

    한도는 키 하나에 걸린다. 조직별 숫자는 "누가 많이 썼나" 를 볼 때 쓰고,
    "남았나" 는 전체로만 답할 수 있다.
    """

    def test_a_small_share_does_not_mean_room_is_left(self) -> None:
        # 이 조직은 200회밖에 안 썼지만 전체는 한도를 다 썼다.
        exhausted = usage(calls=PAGESPEED_DAILY_QUOTA, mine=200)

        assert exhausted.calls_by_this_organization == 200
        assert exhausted.remaining == 0
        assert exhausted.is_exhausted is True

    def test_the_caveat_says_the_share_is_not_the_answer(self) -> None:
        text = usage(calls=100, mine=20).caveat_ko()

        assert "API 키 하나에 걸립니다" in text
        assert "전체로만 답할 수 있습니다" in text


class TestTheSentenceOnScreenSaysWhatToDo:
    def test_exhaustion_says_it_is_our_limit_not_the_site(self) -> None:
        """고객이 자기 사이트를 고치려 들면 안 된다. 우리 한도다(0-J)."""
        text = usage(calls=PAGESPEED_DAILY_QUOTA).summary_ko()

        assert "사이트의 문제가" in text
        assert "우리 한도" in text
        assert "내일 초기화" in text

    def test_a_warning_translates_the_number_into_scans(self) -> None:
        """"5,000회 남음" 보다 "1,000번 더 진단 가능" 이 판단에 쓰인다."""
        text = usage(calls=int(PAGESPEED_DAILY_QUOTA * 0.85)).summary_ko()

        assert "더 진단할 수 있습니다" in text

    def test_a_quiet_day_still_reports_the_number(self) -> None:
        assert "남았습니다" in usage(calls=10).summary_ko()

    def test_the_reset_boundary_is_not_claimed_to_be_exact(self) -> None:
        """구글은 태평양 시간 자정에 초기화하고 우리는 UTC 로 센다.

        정확한 척하면 경계 근처에서 틀린 답을 확신 있게 말하게 된다.
        """
        assert "어긋날 수 있습니다" in usage(calls=1).caveat_ko()


class TestTheQuotaIsGooglesNumberNotOurs:
    def test_the_daily_quota_matches_what_google_publishes(self) -> None:
        """우리가 정한 값이 아니다. 바꾸려면 구글 문서가 근거여야 한다."""
        assert PAGESPEED_DAILY_QUOTA == 25_000


def test_the_query_counts_failed_calls_too() -> None:
    """실패한 호출도 한도를 쓴다.

    질의 자체는 DB 가 필요해 여기서 돌리지 않는다. 대신 **세는 조건에 성공 여부가
    없다는 사실**을 소스에서 확인한다 — 조건이 생기면 이 시험이 깨진다.
    """
    from pathlib import Path

    source = Path(__file__).resolve().parents[2] / "src" / "veo" / "usage" / "quota.py"
    text = source.read_text(encoding="utf-8")

    assert "succeeded" not in text, "성공한 호출만 세면 남은 양을 실제보다 많게 센다"


def test_the_organisation_filter_is_optional() -> None:
    """조직을 지정하지 않아도 전체는 셀 수 있어야 한다.

    운영자가 "지금 키가 얼마나 남았나" 를 볼 때는 조직이 없다.
    """
    import inspect

    from veo.usage.quota import pagespeed_quota

    signature = inspect.signature(pagespeed_quota)
    assert signature.parameters["organization_id"].default is None


def test_a_share_of_zero_is_not_confused_with_no_data() -> None:
    """조직을 지정하지 않으면 몫은 0 이다. 그것은 "안 썼다" 가 아니라 "안 물었다" 다."""
    without = usage(calls=500, mine=0)
    assert without.calls_today == 500
    assert without.remaining == PAGESPEED_DAILY_QUOTA - 500


def test_the_window_covers_exactly_one_day() -> None:
    window = usage(calls=1)
    assert window.window_end - window.window_start == timedelta(days=1)


def test_an_organisation_id_is_a_uuid_not_a_string() -> None:
    """문자열을 받으면 조직 간 격리가 오타 하나로 무너진다."""
    import inspect

    from veo.usage.quota import pagespeed_quota

    annotation = inspect.signature(pagespeed_quota).parameters["organization_id"].annotation
    assert "uuid" in str(annotation).lower()
    assert uuid.UUID  # 형식만 확인한다
