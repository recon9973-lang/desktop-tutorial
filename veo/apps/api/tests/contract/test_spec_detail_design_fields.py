"""명세 상세가 설계도를 그릴 재료를 전부 싣는지 — 콘솔 '알고리즘 설계도' 화면의 계약.

이 화면이 생긴 이유가 곧 이 시험의 이유다: 채점 기준 화면이 하드코딩된 1.0.0 목록을
그리는 동안 실제 발행본은 1.9.0 이었다(2026-08-02 사용자 발견). 화면은 이제 이
엔드포인트만 읽는다 — 여기서 필드가 빠지면 설계도가 조용히 비므로, 계약을 붙잡아 둔다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.scoring import latest_published


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_the_latest_seo_spec_detail_carries_the_design(client: TestClient) -> None:
    spec = latest_published("veo.seo.readiness")
    response = client.get(f"/api/scoring/specs/veo.seo.readiness/{spec.version}")
    assert response.status_code == 200
    data = response.json()["data"]

    # 단계 표: 관문과 가중치 — 곱셈과 가중 평균을 화면이 구분해 그릴 근거.
    categories = data["categories"]
    assert any(category["is_gate"] for category in categories)
    assert any(not category["is_gate"] for category in categories)
    # 배점: 1.8.0+ 는 검사마다 명시 배점이 있다.
    scored = [c for c in categories if c["contributes_to_score"] and not c["is_gate"]]
    assert all(
        check["points"] is not None for category in scored for check in category["checks"]
    )

    # 셈법: breadth·주의 계수·NOT_SAMPLED 선언.
    policy = data["status_policy"]
    assert policy["breadth_exponent"] == spec.status_policy.breadth_exponent
    assert policy["not_sampled"] == spec.status_policy.not_sampled

    # 측정 범위(1.9.0+)와 표본 정책 — 근거 문장까지 그대로.
    scope = data["measurement_scope"]
    assert scope is not None
    assert scope["max_pages"] == spec.measurement_scope.max_pages
    assert scope["rationale_ko"]

    sampling = data["sampling"]
    assert sampling is not None
    assert sorted(
        sampling["perf_lab_check_ids"] + sampling["perf_field_check_ids"]
    ) == sorted(spec.sampled_check_ids)


def test_the_spec_listing_contains_the_latest_published_versions(
    client: TestClient,
) -> None:
    """목록에서 최신을 고를 수 있어야 화면이 1.0.0 에 다시 갇히지 않는다."""
    response = client.get("/api/scoring/specs")
    assert response.status_code == 200
    entries = response.json()["data"]["specs"]

    for spec_id in ("veo.seo.readiness", "veo.geo.readiness"):
        latest = latest_published(spec_id)
        versions = [e["version"] for e in entries if e["spec_id"] == spec_id]
        assert latest.version in versions, (
            f"{spec_id} 최신 발행본 {latest.version} 이 목록에 없다"
        )
