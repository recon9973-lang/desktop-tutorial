"""HTTPS 인증서가 곧 만료되지 않는가.

1.3.0 에서 선언을 미뤄 둔 항목이다. 값어치가 없어서가 아니라 — 자동 갱신이 실패한
인증서는 만료되는 순간 사이트가 **통째로 열리지 않는다** — 크롤러가 만료일을 수집하지
않았기 때문이다. 잴 수 없는 항목을 절대 평가에 넣으면 우리가 만들지 않은 기능 때문에
모든 고객의 점수가 내려간다.

이제 TLS 핸드셰이크에서 만료일을 받아 온다. 판정 기준은 갱신 실패를 사고가 되기 전에
잡는 데 맞췄다:

* 이미 만료 → 실패. 사이트가 지금 열리지 않는다.
* 7일 미만 → 실패. 자동 갱신이 여러 번 실패했다는 뜻이고, 주말이 끼면 손쓸 시간이 없다.
* 30일 미만 → 주의. Let's Encrypt 는 만료 30일 전에 갱신을 시작하므로, 이 구간에
  들어와 있다는 것은 첫 갱신 시도가 이미 실패했다는 신호다.
* 그 외 → 통과.

만료일을 못 받은 경우와 여유가 있는 경우는 다르다. 못 받았으면 측정 불가로 남긴다 —
통과로 접으면 만료 직전인 사이트를 정상이라고 보고하게 된다.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta

from tests.seo.support import build_context, by_id, issues_for

from veo.scoring import CheckStatus
from veo.seo.collectors import PerformanceUxCollector

COLLECTOR = PerformanceUxCollector()
CHECK = "seo.security.certificate_not_expiring"


def context_with_expiry(days: float | None, *, fixture: str = "healthy"):
    """모든 문서에 같은 만료일을 심는다. ``None`` 이면 수집하지 못한 상태.

    기준은 **수집 시각**이다. `datetime.now()` 로 재면 며칠 전에 수집한 자료를 다시
    채점할 때 남은 기간이 달라진다 — 같은 진단이 볼 때마다 다른 값을 내면 안 된다.
    """
    context = build_context(fixture)
    moment = None if days is None else context.collected_at + timedelta(days=days)
    documents = {
        url: dataclasses.replace(document, tls_expires_at=moment)
        for url, document in context.documents.items()
    }
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


def outcome(days: float | None, **kwargs):  # type: ignore[no-untyped-def]
    return by_id(COLLECTOR.collect(context_with_expiry(days, **kwargs)))[CHECK]


class TestRoomToRenew:
    def test_a_year_of_headroom_passes(self) -> None:
        assert outcome(365).status is CheckStatus.PASS

    def test_two_months_passes(self) -> None:
        assert outcome(60).status is CheckStatus.PASS

    def test_the_remaining_days_are_reported(self) -> None:
        """"곧 만료됩니다" 만으로는 오늘 처리할 일인지 알 수 없다."""
        note = outcome(45).note or ""
        assert "45" in note


class TestRenewalHasProbablyFailed:
    def test_inside_the_renewal_window_is_a_warning(self) -> None:
        """30일 안쪽이면 자동 갱신의 첫 시도가 이미 실패했다는 신호다."""
        assert outcome(20).status is CheckStatus.WARNING

    def test_under_a_week_is_a_failure(self) -> None:
        assert outcome(3).status is CheckStatus.FAIL

    def test_an_expired_certificate_is_a_failure(self) -> None:
        assert outcome(-1).status is CheckStatus.FAIL

    def test_an_expired_certificate_says_so_plainly(self) -> None:
        note = outcome(-5).note or ""
        assert "만료" in note

    def test_the_issue_says_who_fixes_it_and_how(self) -> None:
        drafts = issues_for(COLLECTOR.collect(context_with_expiry(3)), CHECK)

        assert drafts
        assert drafts[0].remediation_owner == "OPERATIONS"
        assert drafts[0].remediation_ko
        assert drafts[0].business_impact_ko


class TestWhatWeCouldNotSee:
    def test_no_expiry_data_is_unknown_not_a_pass(self) -> None:
        """통과로 접으면 만료 직전인 사이트를 정상이라고 보고하게 된다."""
        assert outcome(None).status is CheckStatus.UNKNOWN

    def test_the_unknown_reason_is_written_down(self) -> None:
        assert outcome(None).note

    def test_a_plain_http_site_has_no_certificate_to_check(self) -> None:
        """인증서가 없는 것은 HTTPS 를 안 쓰는 것이고, 그건 다른 항목이 잡는다."""
        context = build_context("healthy")
        documents = {
            url.replace("https://", "http://"): dataclasses.replace(
                document,
                final_url=document.final_url.replace("https://", "http://"),
                requested_url=document.requested_url.replace("https://", "http://"),
                tls_expires_at=None,
            )
            for url, document in context.documents.items()
        }
        context = dataclasses.replace(
            context,
            documents=documents,
            primary_document=next(iter(documents.values())),
            target_url=context.target_url.replace("https://", "http://"),
        )

        assert by_id(COLLECTOR.collect(context))[CHECK].status is CheckStatus.NOT_APPLICABLE


class TestTheFetcherActuallyCollectsIt:
    def test_a_document_carries_the_expiry_field(self) -> None:
        """수집 경로가 없으면 위의 모든 판정이 영원히 측정 불가로만 남는다."""
        from veo.common.security.fetcher import FetchedDocument

        assert "tls_expires_at" in FetchedDocument.__dataclass_fields__

    def test_the_expiry_is_read_from_the_peer_certificate(self) -> None:
        """`notAfter` 문자열을 시각으로 옮기는 자리. 여기가 틀리면 조용히 잘못 잰다."""
        from veo.common.security.fetcher import parse_certificate_expiry

        moment = parse_certificate_expiry({"notAfter": "Jun  1 12:00:00 2027 GMT"})

        assert moment is not None
        assert (moment.year, moment.month, moment.day) == (2027, 6, 1)

    def test_a_certificate_without_a_date_is_none_not_a_crash(self) -> None:
        from veo.common.security.fetcher import parse_certificate_expiry

        assert parse_certificate_expiry({}) is None
        assert parse_certificate_expiry(None) is None
        assert parse_certificate_expiry({"notAfter": "쓰레기"}) is None
