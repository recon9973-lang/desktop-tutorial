"""NOT_SAMPLED — 명세가 재지 않기로 한 것은 감점도 측정 범위 손실도 아니다.

1.9.0 이 신설한 상태다. 절대 평가의 원칙은 "못 잰 것은 분모에 남는다"(ADR 0016)
이고 NOT_SAMPLED 는 그 예외이므로, 이 파일이 지키는 것은 예외의 **경계**다:

1. 명세가 표본 정책(sampling.*.check_ids)을 선언한 검사에만 허용된다 — 다른 검사에
   붙이면 평가기가 오류를 낸다. "안 재기로 했다" 가 절대평가를 비껴가는 뒷문이
   되지 않는다.
2. 셈은 N/A 와 같다(분모·측정 범위 제외). 이름이 다른 이유는 사실이 다르기 때문이고,
   그 사실은 not_sampled_check_ids 목록으로 화면까지 간다.
3. 숫자를 바꾸지 않은 판이다 — 같은 판정이면 1.8.0 과 1.9.0 의 점수가 같다.
4. 명세의 측정 범위 선언과 서버 설정은 같은 값이어야 한다 — 같은 값을 두 곳이
   들고 있으므로, 어긋나면 여기서 깨진다.
"""

from __future__ import annotations

import copy

import pytest

from veo.core.settings import get_settings
from veo.scoring import CheckOutcome, CheckStatus, build_spec, evaluate, latest_published
from veo.scoring.errors import ScoringSpecError


def outcome(check_id: str, status: CheckStatus) -> CheckOutcome:
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=1.0,
        evidence_ids=[f"ev::{check_id}"],
    )


def sampled_spec(tiny_spec_dict):  # type: ignore[no-untyped-def]
    """cat_a 의 major 검사 하나를 표본 정책 대상으로 선언한 사본."""
    raw = copy.deepcopy(tiny_spec_dict)
    raw["spec_id"] = "veo.test.sampled"
    raw["status_policy"]["not_sampled"] = "EXCLUDE_FROM_DENOMINATOR"
    raw["sampling"] = {
        "perf_lab": {
            "max_urls": 5,
            "min_measured_ratio": 0.6,
            "check_ids": ["test.a.major"],
        }
    }
    return build_spec(raw)


ALL_IDS = ("test.a.blocker", "test.a.major", "test.a.info", "test.b.critical", "test.b.minor")


def outcomes_with(status_of: dict[str, CheckStatus]) -> list[CheckOutcome]:
    return [outcome(cid, status_of.get(cid, CheckStatus.PASS)) for cid in ALL_IDS]


class TestTheBoundary:
    def test_an_undeclared_check_may_not_be_not_sampled(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        spec = sampled_spec(tiny_spec_dict)
        with pytest.raises(ScoringSpecError, match="NOT_SAMPLED"):
            evaluate(spec, outcomes_with({"test.b.critical": CheckStatus.NOT_SAMPLED}))

    def test_a_spec_without_a_sampling_list_allows_no_not_sampled_at_all(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        spec = build_spec(copy.deepcopy(tiny_spec_dict))
        with pytest.raises(ScoringSpecError, match="NOT_SAMPLED"):
            evaluate(spec, outcomes_with({"test.a.major": CheckStatus.NOT_SAMPLED}))

    def test_a_sampling_list_pointing_at_a_missing_check_cannot_be_built(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        raw = copy.deepcopy(tiny_spec_dict)
        raw["status_policy"]["not_sampled"] = "EXCLUDE_FROM_DENOMINATOR"
        raw["sampling"] = {
            "perf_lab": {
                "max_urls": 5,
                "min_measured_ratio": 0.6,
                "check_ids": ["no_such_check"],
            }
        }
        with pytest.raises(ValueError, match="no_such_check"):
            build_spec(raw)

    def test_a_sampling_list_without_a_policy_cannot_be_built(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        raw = copy.deepcopy(tiny_spec_dict)
        raw["sampling"] = {
            "perf_lab": {
                "max_urls": 5,
                "min_measured_ratio": 0.6,
                "check_ids": ["test.a.major"],
            }
        }
        with pytest.raises(ValueError, match="not_sampled"):
            build_spec(raw)


class TestTheArithmetic:
    def test_not_sampled_counts_like_not_applicable(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        """분모·측정 범위에서 빠진다 — N/A 와 같은 산수, 다른 이름."""
        spec = sampled_spec(tiny_spec_dict)

        as_sampled = evaluate(spec, outcomes_with({"test.a.major": CheckStatus.NOT_SAMPLED}))
        as_na = evaluate(spec, outcomes_with({"test.a.major": CheckStatus.NOT_APPLICABLE}))

        assert as_sampled.overall_score == as_na.overall_score
        assert as_sampled.coverage == as_na.coverage

    def test_not_sampled_is_not_unknown(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        """UNKNOWN 은 측정 범위를 낮춘다 — NOT_SAMPLED 가 그러면 우리 정책이 감점이 된다."""
        spec = sampled_spec(tiny_spec_dict)

        as_sampled = evaluate(spec, outcomes_with({"test.a.major": CheckStatus.NOT_SAMPLED}))
        as_unknown = evaluate(spec, outcomes_with({"test.a.major": CheckStatus.UNKNOWN}))

        assert as_sampled.coverage > as_unknown.coverage

    def test_the_list_survives_into_the_category_result(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        """화면이 "표본 밖 — 요청 시 측정" 을 달 근거가 결과에 실려 있어야 한다."""
        spec = sampled_spec(tiny_spec_dict)
        result = evaluate(spec, outcomes_with({"test.a.major": CheckStatus.NOT_SAMPLED}))

        cat_a = next(c for c in result.categories if c.category_id == "cat_a")
        assert cat_a.not_sampled_check_ids == ["test.a.major"]
        assert "test.a.major" not in cat_a.not_applicable_check_ids


class TestThePublishedSpec:
    def test_1_9_0_changes_no_number(self) -> None:
        """같은 판정이면 1.8.0 과 1.9.0 의 점수가 같다 — 선언만 더한 판이다."""
        from veo.scoring import load_spec

        old = load_spec("veo.seo.readiness", "1.8.0")
        new = latest_published("veo.seo.readiness")
        assert new.version == "1.9.0"

        outcomes = [outcome(cid, CheckStatus.PASS) for cid in new.check_ids]
        warned = [
            outcome(cid, CheckStatus.WARNING if i % 3 == 0 else CheckStatus.PASS)
            for i, cid in enumerate(new.check_ids)
        ]
        for supplied in (outcomes, warned):
            assert (
                evaluate(old, supplied).overall_score
                == evaluate(new, supplied).overall_score
            )

    def test_the_declared_scope_matches_the_server_settings(self) -> None:
        """같은 값이 명세와 설정 두 곳에 있다 — 한쪽만 바뀌면 여기서 깨진다."""
        spec = latest_published("veo.seo.readiness")
        scope = spec.measurement_scope
        assert scope is not None, "1.9.0 부터 측정 범위는 명세가 선언한다"

        settings = get_settings()
        assert scope.max_pages == settings.console_crawl_max_urls
        assert scope.max_depth == settings.console_crawl_max_depth
        assert scope.template_group_sample == settings.console_crawl_group_sample

    def test_the_sampling_list_is_exactly_the_performance_checks(self) -> None:
        spec = latest_published("veo.seo.readiness")
        assert sorted(spec.sampled_check_ids) == [
            "seo.perf.cls_lab",
            "seo.perf.inp_field",
            "seo.perf.lcp_lab",
            "seo.perf.modern_image_format",
            "seo.perf.resource_hints",
            "seo.perf.tbt_lab",
            "seo.perf.text_compression",
        ]
