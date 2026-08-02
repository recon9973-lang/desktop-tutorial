"""GEO 1.3.0 — 측정 범위 선언만 더한 판의 성질.

1. 숫자를 바꾸지 않았다 — 같은 판정이면 1.2.0 과 점수가 같다.
2. 선언한 범위는 서버 설정과 같은 값이다 — 같은 값 두 곳은 시험이 묶는다.
3. 표본 정책은 선언하지 않았다 — GEO 에서 NOT_SAMPLED 는 여전히 오류다.
"""

from __future__ import annotations

import pytest

from veo.core.settings import get_settings
from veo.scoring import CheckOutcome, CheckStatus, evaluate, latest_published, load_spec
from veo.scoring.errors import ScoringSpecError


def outcome(check_id: str, status: CheckStatus) -> CheckOutcome:
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=1.0,
        evidence_ids=[f"ev::{check_id}"],
    )


def test_1_3_0_changes_no_number() -> None:
    old = load_spec("veo.geo.readiness", "1.2.0")
    new = latest_published("veo.geo.readiness")
    assert new.version == "1.3.0"

    all_pass = [outcome(check_id, CheckStatus.PASS) for check_id in new.check_ids]
    mixed = [
        outcome(
            check_id,
            CheckStatus.WARNING if index % 3 == 0 else CheckStatus.PASS,
        )
        for index, check_id in enumerate(new.check_ids)
    ]
    for supplied in (all_pass, mixed):
        assert (
            evaluate(old, supplied).overall_score == evaluate(new, supplied).overall_score
        )


def test_the_declared_scope_matches_the_server_settings() -> None:
    """GEO 는 SEO 와 같은 크롤러로 페이지를 가져온다 — 선언도 같은 값이어야 한다."""
    spec = latest_published("veo.geo.readiness")
    scope = spec.measurement_scope
    assert scope is not None, "1.3.0 부터 측정 범위는 명세가 선언한다"

    settings = get_settings()
    assert scope.max_pages == settings.console_crawl_max_urls
    assert scope.max_depth == settings.console_crawl_max_depth
    assert scope.template_group_sample == settings.console_crawl_group_sample


def test_not_sampled_is_still_an_error_in_geo() -> None:
    """표본 정책을 선언하지 않은 판에서는 '안 재기로 했다' 가 존재하지 않는다."""
    spec = latest_published("veo.geo.readiness")
    assert spec.sampled_check_ids == frozenset()

    first = next(iter(spec.check_ids))
    outcomes = [
        outcome(
            check_id,
            CheckStatus.NOT_SAMPLED if check_id == first else CheckStatus.PASS,
        )
        for check_id in spec.check_ids
    ]
    with pytest.raises(ScoringSpecError, match="NOT_SAMPLED"):
        evaluate(spec, outcomes)
