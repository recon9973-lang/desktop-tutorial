"""성능 표본 정책 — 덜 재서 이득 보지 못한다.

실험실 성능(LCP·CLS·TBT)은 페이지 하나를 실제로 브라우저에 띄워 재는 것이라 한 장에
16~60초가 걸린다(2026-08-01 실측: 16.0 / 24.1 / 28.3 / 59.8초). 100장을 다 재면 진단이
한 시간을 넘어 끝나지 않는다. 그래서 중요도 상위 몇 장만 잰다.

**그 순간 위험이 생긴다.** 잰 페이지만 분모에 넣으면 100장 중 3장 재고 3장 다 통과할
때 "LCP 통과" 가 되고 나머지 97장은 사라진다. 그것은 우리가 경쟁 도구를 비판한 바로
그 구조다 — 타사는 랜딩 1장만 보고 canonical 을 통과시켰고, VEO 는 100장을 훑어 40장
에서 문제를 찾았다.

**가장 나쁜 형태는 편향이 우리에게 유리하게 걸린다는 것이다.** 2026-08-01 실측에서
Lighthouse 가 `FAILED_DOCUMENT_REQUEST` 로 페이지를 못 여는 사례가 실제로 나왔고,
못 여는 이유는 대개 **그 페이지가 느려서**다. 못 잰 페이지를 분모에서 빼면 느린
페이지만 골라 빼는 셈이고, 사이트는 실제보다 빨라 보인다.

이 파일이 막는 것이 그것이다.

실사용자(field) 지표는 사정이 다르다. 구글이 크롬 사용자에게서 이미 모아 둔 값이라
한 번 물으면 **사이트 전체 값**이 함께 온다(2026-08-01 실측, seoul.go.kr: 페이지 값
LCP 1041ms·INP 96ms / 사이트 전체 값 LCP 1011ms·INP 122ms). 표본 문제 자체가 없다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import SPEC, build_context, by_id

from veo.contracts.enums import ProviderState
from veo.scoring import CheckStatus
from veo.seo.collectors import PerformanceUxCollector
from veo.seo.collectors.performance_ux import lab_sample

COLLECTOR = PerformanceUxCollector()
LCP = "seo.perf.lcp_lab"
INP = "seo.perf.inp_field"


def with_pagespeed(context, measured_urls, *, score: float = 1.0):  # type: ignore[no-untyped-def]
    """지정한 URL 들만 PageSpeed 값을 가진 문맥."""
    payload = {
        url: {
            "lighthouse": {
                "largest-contentful-paint": {"score": score, "display_value": "2.0 초"},
                "cumulative-layout-shift": {"score": score, "display_value": "0"},
                "total-blocking-time": {"score": score, "display_value": "100 밀리초"},
            }
        }
        for url in measured_urls
    }
    return dataclasses.replace(
        context,
        provider_states={**context.provider_states, "GOOGLE_PAGESPEED": ProviderState.ENABLED},
        provider_payloads={**context.provider_payloads, "GOOGLE_PAGESPEED": payload},
    )


def with_crux(context, payload):  # type: ignore[no-untyped-def]
    return dataclasses.replace(
        context,
        provider_states={**context.provider_states, "GOOGLE_CRUX": ProviderState.ENABLED},
        provider_payloads={**context.provider_payloads, "GOOGLE_CRUX": payload},
    )


def _with_max_urls(context, max_urls: int):  # type: ignore[no-untyped-def]
    """표본 상한만 바꾼 명세 사본을 문맥에 끼운다."""
    spec = context.spec
    sampling = spec.sampling.model_copy(
        update={"perf_lab": spec.sampling.perf_lab.model_copy(update={"max_urls": max_urls})}
    )
    return dataclasses.replace(context, spec=spec.model_copy(update={"sampling": sampling}))


def status_of(context, check_id: str) -> CheckStatus:  # type: ignore[no-untyped-def]
    return by_id(COLLECTOR.collect(context))[check_id].status


def note_of(context, check_id: str) -> str:  # type: ignore[no-untyped-def]
    return by_id(COLLECTOR.collect(context))[check_id].note or ""


# --------------------------------------------------------------------------- #
# 표본을 고르는 곳은 하나뿐이다
# --------------------------------------------------------------------------- #


class TestTheSampleIsChosenInOnePlace:
    def test_the_published_spec_declares_a_sampling_policy(self) -> None:
        """숫자가 코드에 있으면 "왜 5장이냐" 에 아무도 답하지 못한다(ADR 0001)."""
        assert SPEC.sampling is not None
        assert SPEC.sampling.perf_lab is not None
        assert SPEC.sampling.perf_lab.max_urls > 0
        assert 0.0 < SPEC.sampling.perf_lab.min_measured_ratio <= 1.0

    def test_the_policy_carries_its_reasoning(self) -> None:
        """근거 없는 숫자는 다음 사람이 마음대로 바꾼다."""
        assert SPEC.sampling.perf_lab.rationale_ko  # type: ignore[union-attr]

    def test_the_sample_never_exceeds_the_declared_limit(self) -> None:
        context = build_context("healthy")
        site = COLLECTOR.observe(context)
        assert len(lab_sample(context, site)) <= SPEC.sampling.perf_lab.max_urls  # type: ignore[union-attr]

    def test_the_sample_takes_the_most_important_pages_first(self) -> None:
        """어느 페이지가 중요한지는 명세의 url_importance 가 이미 정해 뒀다(0-D)."""
        context = build_context("healthy")
        site = COLLECTOR.observe(context)
        chosen = set(lab_sample(context, site))

        ranked = sorted(site.pages, key=lambda page: -page.importance_value)
        top = ranked[: len(chosen)]
        assert min(page.importance_value for page in site.pages if page.url in chosen) >= min(
            page.importance_value for page in top
        )


# --------------------------------------------------------------------------- #
# 덜 재서 이득 보지 못한다 — 이 파일의 본체
# --------------------------------------------------------------------------- #


class TestMeasuringLessIsNeverBetter:
    def test_a_thin_sample_reports_unknown_rather_than_a_pass(self) -> None:
        """**이 시험이 결함을 막는 자물쇠다.**

        계획한 표본 중 일부만 값을 받았고 그 값들이 전부 통과라면, 예전 코드는 "통과"
        로 보고했다. 값을 못 받은 페이지가 분모에서 사라졌기 때문이다. 그리고 값을 못
        받는 이유는 대개 그 페이지가 느려서다.
        """
        context = build_context("healthy")
        site = COLLECTOR.observe(context)
        planned = lab_sample(context, site)
        assert len(planned) >= 3, "이 픽스처는 표본이 3장 이상이어야 의미가 있다"

        # 계획한 것 중 한 장만 값을 받았다 — 그리고 그 한 장은 통과다.
        thin = with_pagespeed(context, planned[:1], score=1.0)
        assert status_of(thin, LCP) is CheckStatus.UNKNOWN

    def test_the_thin_sample_reason_says_why_it_is_not_a_pass(self) -> None:
        """'측정 불가' 만 띄우면 고장으로 읽힌다. 왜 못 믿는지를 적어야 한다."""
        context = build_context("healthy")
        planned = lab_sample(context, COLLECTOR.observe(context))
        note = note_of(with_pagespeed(context, planned[:1]), LCP)

        assert "표본이 얇아" in note
        assert "느려서 열리지 않은" in note

    def test_a_full_sample_is_scored(self) -> None:
        context = build_context("healthy")
        planned = lab_sample(context, COLLECTOR.observe(context))
        assert status_of(with_pagespeed(context, planned, score=1.0), LCP) is CheckStatus.PASS

    def test_dropping_the_slow_pages_cannot_turn_a_failure_into_a_pass(self) -> None:
        """느린 페이지만 빠지면 사이트가 빨라 보인다 — 그 경로를 막는다.

        전부 재면 실패. 느린 것들이 빠지고 빠른 한 장만 남으면, 예전에는 통과였다.
        이제는 표본이 얇아 측정 불가다 — **통과로 뒤집히지 않는다.**
        """
        context = build_context("healthy")
        planned = lab_sample(context, COLLECTOR.observe(context))

        everything = with_pagespeed(context, planned, score=0.1)
        assert status_of(everything, LCP) is CheckStatus.FAIL

        only_the_fast_one = with_pagespeed(context, planned[:1], score=1.0)
        assert status_of(only_the_fast_one, LCP) is not CheckStatus.PASS


# --------------------------------------------------------------------------- #
# 표본이라는 사실을 숨기지 않는다
# --------------------------------------------------------------------------- #


class TestTheSampleIsStated:
    def test_a_partial_sample_says_so_in_the_same_sentence(self) -> None:
        """따로 떼어 놓은 단서는 읽히지 않는다.

        "LCP 양호" 만 읽고 사이트 전체가 빠르다고 이해하면, 그 오해는 우리가 만든 것이다.
        """
        # 픽스처는 4장뿐이라 발행 명세의 상한(5장)으로는 부분 표본이 안 나온다.
        # 건너뛰면 이 성질이 영영 확인되지 않으므로, 상한을 2장으로 낮춘 명세 사본을
        # 만들어 실제로 돌린다.
        context = _with_max_urls(build_context("healthy"), 2)
        site = COLLECTOR.observe(context)
        planned = lab_sample(context, site)
        assert len(planned) < len(site.pages)

        note = note_of(with_pagespeed(context, planned, score=1.0), LCP)
        assert "중요도가 높은" in note
        assert "포함되지 않았습니다" in note

    def test_measuring_everything_adds_no_caveat(self) -> None:
        """늘 붙는 단서는 무시된다. 전부 쟀으면 아무 말도 하지 않는다."""
        context = build_context("healthy")
        site = COLLECTOR.observe(context)
        every_url = [page.url for page in site.pages]

        note = note_of(with_pagespeed(context, every_url, score=1.0), LCP)
        assert "중요도가 높은" not in note


# --------------------------------------------------------------------------- #
# 실사용자 지표에는 표본 문제가 없다
# --------------------------------------------------------------------------- #


class TestFieldDataUsesTheWholeSite:
    """구글은 사이트 전체 실사용자 값을 같은 응답에 담아 준다.

    2026-08-01 실측, seoul.go.kr:
      이 페이지     LCP 1041ms  INP  96ms
      사이트 전체    LCP 1011ms  INP 122ms
    """

    def test_the_policy_prefers_the_origin_scope(self) -> None:
        assert SPEC.sampling.perf_field is not None  # type: ignore[union-attr]
        assert SPEC.sampling.perf_field.prefer_origin_scope is True  # type: ignore[union-attr]

    def test_a_site_wide_sample_is_used_when_no_page_has_one(self) -> None:
        context = with_crux(
            build_context("healthy"),
            {
                "https://healthy.example.kr": {
                    "scope": "ORIGIN",
                    "state": "AVAILABLE",
                    "metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "SLOW"}},
                }
            },
        )
        assert status_of(context, INP) is CheckStatus.FAIL

    def test_the_origin_verdict_says_it_is_a_site_wide_number(self) -> None:
        """범위를 적지 않으면 특정 페이지의 값으로 읽힌다.

        사이트 전체 값은 방문이 많은 페이지가 지배한다. 그것을 특정 URL 에 갖다 붙이면
        그 URL 이 겪지 않은 트래픽으로 칭찬하거나 깎게 된다.
        """
        context = with_crux(
            build_context("healthy"),
            {
                "https://healthy.example.kr": {
                    "scope": "ORIGIN",
                    "state": "AVAILABLE",
                    "metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "FAST"}},
                }
            },
        )
        note = note_of(context, INP)
        assert "사이트 전체" in note
        assert "특정 페이지의 값이 아니라" in note

    def test_a_page_level_sample_wins_over_the_site_wide_one(self) -> None:
        """범위를 섞지 않는다. 페이지 값이 있으면 그것이 더 정확한 답이다."""
        pages = build_context("healthy").documents
        first = next(iter(pages))
        context = with_crux(
            build_context("healthy"),
            {
                first: {
                    "scope": "URL",
                    "state": "AVAILABLE",
                    "metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "FAST"}},
                },
                "https://healthy.example.kr": {
                    "scope": "ORIGIN",
                    "state": "AVAILABLE",
                    "metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "SLOW"}},
                },
            },
        )
        assert status_of(context, INP) is CheckStatus.PASS
        assert "사이트 전체" not in note_of(context, INP)

    def test_no_sample_anywhere_is_not_applicable_not_a_failure(self) -> None:
        """방문자가 적다는 사실이지 사이트가 느리다는 뜻이 아니다.

        동네 병원 홈페이지는 대부분 여기 해당된다(2026-08-01 실측: 페이지 값도 사이트
        값도 없었다). 이것을 실패로 적으면 아무 잘못 없는 고객이 점수를 잃는다.
        """
        # 어댑터가 "표본 없음" 을 표현하는 실제 모양이다 — 항목은 있고 metrics 가 비어
        # 있다. 항목 자체를 빼면 "응답을 못 받았다"(측정 불가)와 구분되지 않는다.
        first = next(iter(build_context("healthy").documents))
        context = with_crux(
            build_context("healthy"),
            {first: {"scope": "URL", "state": "NOT_APPLICABLE", "metrics": {}}},
        )
        assert status_of(context, INP) is CheckStatus.NOT_APPLICABLE
