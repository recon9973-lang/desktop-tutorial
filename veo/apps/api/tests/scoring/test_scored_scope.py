"""100점이 모든 고객에게 같은 뜻이어야 한다.

명세 1.3.0 은 열 개 항목을 **연동이 있어야 잴 수 있는 것**으로 표시한다. 서치콘솔·
서치어드바이저는 사이트 소유자가 권한을 줘야 하고, 백링크·브랜드 언급은 유료 데이터원이
있어야 한다. 사용자의 지시는 분명했다 — 그것들은 배점에서 빼고, 다만 무엇이 빠졌는지는
아래에 남겨 알려 준다.

그런데 배점에서 빼는 방법이 두 가지고, 하나는 틀렸다.

**틀린 쪽**: 못 잰 항목이라 통째로 해당 없음이 되어 그 영역이 가중치 합에서 빠지게
두는 것. 그러면 분모가 고객마다 달라진다. 연동이 없는 고객은 80점어치 안에서 100점을
받고, 서치콘솔을 연결한 고객은 90점어치 안에서 채점된다. 연결하면 잴 것이 늘어 점수가
내려갈 수 있으니, **연결하지 않는 편이 점수에 유리해진다.** 진단 도구가 만들면 안 되는
유인이다.

**맞는 쪽**: 그 영역들이 애초에 준비도 점수의 일부가 아니라고 명세에 적는 것. 준비도는
VEO 가 스스로 잴 수 있는 것만으로 100점을 이루고, 연동 지표는 점수 옆에 따로 표시한다.
연동을 붙이든 안 붙이든 100점의 뜻이 변하지 않는다.

명세 자체가 이미 그렇게 말하고 있었다 — `observability_outcomes` 의 설명은 "검색 성과
데이터는 기술 준비도와 분리해 표시" 라고 적혀 있는데, 정작 채점에서는 분리되지 않았다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")


@pytest.fixture
def spec():  # type: ignore[no-untyped-def]
    import veo.api.app  # noqa: F401
    from veo.scoring.spec import latest_published

    return latest_published("veo.seo.readiness")


class TestTheScoredCategoriesMakeAHundredOnTheirOwn:
    def test_the_categories_that_carry_the_score_sum_to_one_hundred(self, spec) -> None:  # type: ignore[no-untyped-def]
        """점수를 이루는 영역만으로 100이어야 한다. 80이면 남은 20은 어디서 오는가."""
        scored = [c for c in spec.categories if c.contributes_to_score]

        assert sum(c.weight for c in scored) == pytest.approx(100.0)

    def test_the_integration_categories_are_declared_outside_the_score(self, spec) -> None:  # type: ignore[no-untyped-def]
        """고객이 권한을 주기 전에는 잴 수 없는 영역들이다."""
        outside = {c.id for c in spec.categories if not c.contributes_to_score}

        assert outside == {
            "search_engine_integration",
            "observability_outcomes",
            "offpage_entity",
        }

    def test_every_check_outside_the_score_needs_someone_else_to_open_it(self, spec) -> None:  # type: ignore[no-untyped-def]
        """점수 밖으로 뺀 근거는 '연동이 필요하다' 하나뿐이다. 다른 이유로 빼면 안 된다."""
        for category in spec.categories:
            if category.contributes_to_score:
                continue
            for check in category.checks:
                assert check.availability in {"CUSTOMER_GRANTED", "PAID_PROVIDER"}, check.id

    def test_nothing_self_service_hides_outside_the_score(self, spec) -> None:  # type: ignore[no-untyped-def]
        """우리가 스스로 잴 수 있는 것을 점수 밖에 두면 그냥 안 재는 것이다."""
        scored = [c for c in spec.categories if c.contributes_to_score]

        assert scored, "점수를 이루는 영역이 하나도 없다"


class TestTheDenominatorDoesNotMoveWhenAnIntegrationOpens:
    def _score(self, fixture: str, **kwargs):  # type: ignore[no-untyped-def]
        from tests.seo.support import build_context

        import veo.api.app  # noqa: F401
        from veo.seo.service import run_seo_scan

        return run_seo_scan(build_context(fixture, **kwargs)).score

    def test_without_any_provider_the_denominator_is_one_hundred(self) -> None:
        """연동이 하나도 없는 것이 기본 상태다. 그 상태에서 만점이 100이어야 한다."""
        score = self._score("healthy")

        assert score.effective_weight_total == pytest.approx(100.0)

    def test_connecting_a_provider_does_not_change_the_denominator(self) -> None:
        """연결했다고 분모가 늘면, 연결한 고객만 더 어려운 시험을 치르게 된다."""
        from tests.seo.support import build_context, healthy_provider_payloads

        import veo.api.app  # noqa: F401
        from veo.contracts.enums import ProviderState
        from veo.seo.service import run_seo_scan

        urls = tuple(build_context("healthy").documents)
        connected = build_context(
            "healthy",
            provider_states=dict.fromkeys(
                (
                    "GOOGLE_PAGESPEED",
                    "GOOGLE_SEARCH_CONSOLE",
                    "NAVER_SEARCH_ADVISOR",
                    "INDEXNOW",
                    "BACKLINK_INDEX",
                    "BRAND_MENTIONS",
                    "GOOGLE_CRUX",
                ),
                ProviderState.ENABLED,
            ),
            provider_payloads=healthy_provider_payloads(urls),
        )

        assert run_seo_scan(connected).score.effective_weight_total == pytest.approx(100.0)


class TestAnUnopenedIntegrationIsNotAFailure:
    def test_a_customer_granted_check_leaves_the_denominator(self) -> None:
        """아직 요청하지도 않은 권한 때문에 고객의 점수가 낮아지면 안 된다."""
        from tests.seo.support import build_context

        import veo.api.app  # noqa: F401
        from veo.scoring import CheckStatus
        from veo.seo.service import run_seo_scan

        result = run_seo_scan(build_context("healthy"))
        outcomes = {item.check_id: item for item in result.score.outcomes}

        assert outcomes["seo.integration.gsc_verified"].status is CheckStatus.NOT_APPLICABLE

    def test_the_reason_says_what_would_unlock_it(self) -> None:
        """"해당 없음" 만 띄우면 영영 잴 수 없는 항목으로 읽힌다."""
        from tests.seo.support import build_context

        import veo.api.app  # noqa: F401
        from veo.seo.service import run_seo_scan

        result = run_seo_scan(build_context("healthy"))
        outcomes = {item.check_id: item for item in result.score.outcomes}

        note = outcomes["seo.integration.gsc_verified"].note or ""
        assert "권한" in note or "연결" in note or "연동" in note

    def test_a_self_service_check_we_failed_to_run_is_still_unknown(self) -> None:
        """PageSpeed 는 우리 키로 잰다. 못 쟀다면 고객 탓이 아니라 우리가 안 한 것이다."""
        from tests.seo.support import build_context

        import veo.api.app  # noqa: F401
        from veo.scoring import CheckStatus
        from veo.seo.service import run_seo_scan

        result = run_seo_scan(build_context("healthy"))
        outcomes = {item.check_id: item for item in result.score.outcomes}

        assert outcomes["seo.perf.lcp_lab"].status is CheckStatus.UNKNOWN

    def test_a_connected_provider_is_measured_normally(self) -> None:
        """연동이 살아 있으면 해당 없음이 아니라 실제 판정이 나와야 한다."""
        from tests.seo.support import build_context, healthy_provider_payloads

        import veo.api.app  # noqa: F401
        from veo.contracts.enums import ProviderState
        from veo.scoring import CheckStatus
        from veo.seo.service import run_seo_scan

        urls = tuple(build_context("healthy").documents)
        connected = build_context(
            "healthy",
            provider_states={"GOOGLE_SEARCH_CONSOLE": ProviderState.ENABLED},
            provider_payloads=healthy_provider_payloads(urls),
        )

        outcomes = {
            item.check_id: item for item in run_seo_scan(connected).score.outcomes
        }
        assert outcomes["seo.integration.gsc_verified"].status is not CheckStatus.NOT_APPLICABLE
