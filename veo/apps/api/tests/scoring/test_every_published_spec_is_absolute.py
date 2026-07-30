"""분모가 움직이지 못하게 하는 문지기.

## 왜 이 파일이 있나

절대 평가는 2026-07 에 `veo.seo.readiness/1.2.0` 에서 **한 번** 정해졌다. 그런데 그
결정은 SEO 에만 적용됐고 GEO 는 그대로 남았다. 다섯 달치 작업 동안 아무도 몰랐다 —
**그 규칙을 검사하는 코드가 하나도 없었기 때문이다.** 사람이 기억으로 지켜야 했고,
기억은 실패한다.

그래서 이 파일은 개별 명세를 검사하지 않는다. **앞으로 발행될 모든 명세**를 검사한다.
새 도메인(키워드·경쟁사 등)의 명세를 만들면서 이 규칙을 잊으면 여기서 빨간불이 뜬다.
그것이 "한 번 고치면 그대로 간다" 의 실제 구현이다.

## 왜 옛 판까지 검사하지는 않나

발행본은 불변이다(ADR 0012). `veo.seo.readiness/1.0.0` 은 상대 평가로 발행됐고, 그
판으로 채점된 과거 점수는 앞으로도 그 판의 규칙으로 설명되어야 한다. 옛 판을 고치면
과거 보고서의 숫자를 설명할 수 없게 된다.

그래서 검사 대상은 **각 명세의 현재 발행본**이다.
"""

from __future__ import annotations

import pytest

from veo.scoring.evaluator import ABSOLUTE_UNKNOWN_POLICY
from veo.scoring.spec import ScoringSpec, available_specs, latest_published

SPEC_IDS = sorted(available_specs())


def _latest() -> list[tuple[str, ScoringSpec]]:
    return [(spec_id, latest_published(spec_id)) for spec_id in SPEC_IDS]


def test_there_is_something_to_check() -> None:
    """명세를 하나도 못 찾으면 아래 검사들이 조용히 통과한다."""
    assert SPEC_IDS, "발행된 명세를 찾지 못했습니다"


@pytest.mark.parametrize("spec_id", SPEC_IDS)
def test_the_current_edition_scores_unknown_as_zero_in_the_denominator(spec_id: str) -> None:
    """못 잰 항목은 배점을 유지한 채 0점이다.

    분모에서 빼면 **적게 잴수록 점수가 오른다.** 진단 도구가 만들면 안 되는 유인이고,
    이 하나를 지키지 못하면 100점이 고객마다 다른 뜻이 된다.
    """
    spec = latest_published(spec_id)

    assert spec.status_policy.unknown == ABSOLUTE_UNKNOWN_POLICY, (
        f"{spec_id}/{spec.version} 이 '{spec.status_policy.unknown}' 로 발행돼 있습니다. "
        f"'{ABSOLUTE_UNKNOWN_POLICY}' 여야 합니다 — 지침서 0-B."
    )


@pytest.mark.parametrize("spec_id", SPEC_IDS)
def test_not_applicable_still_leaves_the_denominator(spec_id: str) -> None:
    """해당 없음은 유일한 예외다.

    "이 대상에는 그 항목이 존재하지 않는다" 는 "없다" 가 아니다. 페이지네이션이 없는
    사이트에 페이지네이션 검사를 0점으로 매기면 **없는 결함을 지어내는 것**이다.
    """
    spec = latest_published(spec_id)

    assert spec.status_policy.not_applicable == "EXCLUDE_FROM_DENOMINATOR", (
        f"{spec_id}/{spec.version} 의 해당 없음 정책이 바뀌었습니다."
    )


@pytest.mark.parametrize("spec_id", SPEC_IDS)
def test_the_scored_areas_add_up_to_the_declared_total(spec_id: str) -> None:
    """점수를 이루는 영역만으로 100 이다.

    점수 밖으로 선언한 영역이 분모에 남아 있으면, 우리가 아직 만들지 않은 수집 기능
    때문에 **모든 고객의 점수가 내려간다.**
    """
    spec = latest_published(spec_id)
    scored = sum(
        category.weight for category in spec.categories if category.contributes_to_score
    )

    assert scored == pytest.approx(100.0), (
        f"{spec_id}/{spec.version} 의 점수 영역 합이 {scored} 입니다. 100 이어야 합니다."
    )


@pytest.mark.parametrize("spec_id", SPEC_IDS)
def test_nothing_in_the_score_is_beyond_our_reach(spec_id: str) -> None:
    """수집 경로가 없는 항목을 점수 안에 두지 않는다.

    0-B: "수집 경로가 없는 채로 선언하면 우리가 아직 만들지 않은 기능 때문에 모든
    고객의 점수가 내려간다. 수집을 먼저 만들고 다음 판에 넣는다."

    고객의 권한이나 유료 데이터원이 있어야 볼 수 있는 항목은 `availability` 로 선언하고
    그 영역을 점수 밖에 둔다. 그렇게 하지 않으면 "연동할수록 불리" 가 된다.
    """
    spec = latest_published(spec_id)
    trapped = [
        f"{category.id}/{check.id} ({check.availability})"
        for category in spec.categories
        if category.contributes_to_score
        for check in category.checks
        if check.availability != "SELF_SERVICE"
    ]

    assert trapped == [], (
        f"{spec_id}/{spec.version}: 우리가 스스로 잴 수 없는 항목이 점수 안에 있습니다 — "
        + ", ".join(trapped)
    )
