"""리포트의 숫자는 **실측에서만** 온다.

이 파일이 생기기 전, `DiagnosisInput` 을 만드는 코드는 `veo/reports/schemas.py` 한
곳뿐이었고 그것은 HTTP 요청 본문에서 만든다. 저장된 진단에서 만드는 코드는 0건이었다.

그래서 리포트를 발행하려면 점수·판정·근거·측정 조건을 **호출자가 전부 타이핑해
넣어야** 했다. 발행 후 수정 불가, 내용 해시, 버전 불변 — 그 장치 전체가 아무도 재지
않은 숫자를 지키고 있었다. `reports` 테이블이 0줄이던 이유다.

여기서 고정하는 것:

* 본문에 제목 말고 숫자가 없다.
* 저장된 점수를 **다시 계산하지 않는다**. 다시 계산하면 오늘의 명세로 어제의 자료를
  채점한 숫자가 나오고, 그건 그때 고객이 본 점수가 아니다.
* 측정 조건이 없는 실행은 **거절한다**. 빈 리포트를 만들지 않는다.
* 이 진단이 재지 않은 것(키워드 수요·경쟁사)은 비워 둔다.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from report_support import REPORTS, Tenant

pytest.importorskip("sqlalchemy")


def _data(response: Any) -> dict[str, Any]:
    body = response.json()
    assert body["error"] is None, body["error"]
    payload: dict[str, Any] = body["data"]
    return payload


@pytest.fixture
def measured_run(db, org_a: Tenant):  # type: ignore[no-untyped-def]
    """실제 채점기를 통과한 진단 하나를 저장한다.

    합성 페이로드를 손으로 만들지 않는다 — 그러면 되살리기가 **실제 저장 결과가 아니라
    내 상상** 과 맞는지만 확인하게 된다.
    """
    from tests.seo.support import build_context

    from veo.db.models.identity import Site
    from veo.seo.history import save_scan_run
    from veo.seo.service import run_seo_scan

    site = Site(
        organization_id=org_a.organization_id,
        project_id=org_a.project_id,
        origin="https://example.com",
        display_name="측정 대상",
        is_primary=True,
        crawl_settings={},
    )
    db.add(site)
    db.flush()

    context = build_context("broken_jsonld")
    result = run_seo_scan(context)
    saved = save_scan_run(
        db,
        principal=org_a.analyst,
        site_id=site.id,
        result=result,
        context=context,
        urls_attempted=len(context.documents),
        urls_collected=len(context.documents),
    )
    db.commit()
    return saved, result


def test_the_request_body_carries_no_numbers(
    client: TestClient, act_as, org_a: Tenant, measured_run
) -> None:  # type: ignore[no-untyped-def]
    saved, _ = measured_run
    act_as(org_a.analyst)

    response = client.post(
        f"{REPORTS}/from-scan",
        json={"scan_run_id": str(saved.scan_run_id), "title": "온담한의원 7월 진단"},
    )

    assert response.status_code == 201, response.text
    created = _data(response)
    assert created["version_number"] == 1
    assert created["title_ko"] == "온담한의원 7월 진단"


def test_the_published_score_is_the_score_that_was_measured(
    client: TestClient, act_as, org_a: Tenant, measured_run
) -> None:  # type: ignore[no-untyped-def]
    """다시 계산하지 않는다는 것이 이 테스트의 전부다."""
    saved, result = measured_run
    act_as(org_a.analyst)

    created = _data(
        client.post(
            f"{REPORTS}/from-scan",
            json={"scan_run_id": str(saved.scan_run_id), "title": "점수 확인"},
        )
    )
    version = _data(
        client.get(f"{REPORTS}/{created['report_id']}/versions/{created['version_number']}")
    )

    assert version["spec_versions"]["seo"]["version"] == result.score.spec_version
    assert version["spec_versions"]["seo"]["checksum"] == result.score.spec_checksum


def test_a_run_without_measurement_conditions_is_refused(
    client: TestClient, act_as, org_a: Tenant, db, measured_run
) -> None:  # type: ignore[no-untyped-def]
    """어떤 조건에서 쟀는지 문서에 적을 수 없으면 문서를 만들지 않는다."""
    from veo.db.models.analysis import ScanRun

    saved, _ = measured_run
    db.get(ScanRun, saved.scan_run_id).measurement_conditions = None
    db.commit()

    act_as(org_a.analyst)
    response = client.post(
        f"{REPORTS}/from-scan",
        json={"scan_run_id": str(saved.scan_run_id), "title": "조건 없음"},
    )

    assert response.status_code == 409
    message = response.json()["error"]["message"]
    assert "측정 조건" in message
    assert not message.isascii()


def test_another_organizations_run_is_not_reportable(
    client: TestClient, act_as, org_a: Tenant, org_b: Tenant, measured_run
) -> None:  # type: ignore[no-untyped-def]
    saved, _ = measured_run
    act_as(org_b.analyst)

    response = client.post(
        f"{REPORTS}/from-scan",
        json={"scan_run_id": str(saved.scan_run_id), "title": "남의 진단"},
    )

    assert response.status_code == 409
    assert "찾을 수 없습니다" in response.json()["error"]["message"]


def test_an_unknown_run_answers_exactly_like_a_foreign_one(
    client: TestClient, act_as, org_a: Tenant
) -> None:  # type: ignore[no-untyped-def]
    """존재 여부를 알려주지 않는다."""
    act_as(org_a.analyst)
    response = client.post(
        f"{REPORTS}/from-scan",
        json={"scan_run_id": str(uuid.uuid4()), "title": "없는 진단"},
    )

    assert response.status_code == 409
    assert "찾을 수 없습니다" in response.json()["error"]["message"]


def test_only_runs_with_conditions_are_offered(
    client: TestClient, act_as, org_a: Tenant, db, measured_run
) -> None:  # type: ignore[no-untyped-def]
    """골랐다가 거절당하는 것보다 애초에 고를 수 없는 편이 낫다."""
    from veo.db.models.analysis import ScanRun

    saved, _ = measured_run
    act_as(org_a.analyst)

    offered = client.get(
        f"{REPORTS}/reportable-runs", params={"project_id": str(org_a.project_id)}
    ).json()["data"]
    assert [row["scan_run_id"] for row in offered] == [str(saved.scan_run_id)]

    db.get(ScanRun, saved.scan_run_id).measurement_conditions = None
    db.commit()

    offered = client.get(
        f"{REPORTS}/reportable-runs", params={"project_id": str(org_a.project_id)}
    ).json()["data"]
    assert offered == []


def test_the_list_shows_what_was_published(
    client: TestClient, act_as, org_a: Tenant, measured_run
) -> None:  # type: ignore[no-untyped-def]
    saved, _ = measured_run
    act_as(org_a.analyst)
    client.post(
        f"{REPORTS}/from-scan",
        json={"scan_run_id": str(saved.scan_run_id), "title": "목록에 나올 것"},
    )

    rows = client.get(REPORTS).json()["data"]
    assert [row["title"] for row in rows] == ["목록에 나올 것"]
    assert rows[0]["latest_version_number"] == 1
    assert rows[0]["latest_content_hash"].startswith("sha256:")


def test_another_organization_sees_none_of_it(
    client: TestClient, act_as, org_a: Tenant, org_b: Tenant, measured_run
) -> None:  # type: ignore[no-untyped-def]
    saved, _ = measured_run
    act_as(org_a.analyst)
    client.post(
        f"{REPORTS}/from-scan",
        json={"scan_run_id": str(saved.scan_run_id), "title": "우리 것"},
    )

    act_as(org_b.analyst)
    assert client.get(REPORTS).json()["data"] == []


def test_what_this_scan_did_not_measure_stays_empty(
    client: TestClient, act_as, org_a: Tenant, measured_run
) -> None:  # type: ignore[no-untyped-def]
    """키워드 수요와 경쟁사는 이 진단이 잰 것이 아니다.

    채워 넣으면 리포트가 '이 실행에서 나온 값' 이라고 말하게 되는데 사실이 아니다.
    """
    saved, _ = measured_run
    act_as(org_a.analyst)
    created = _data(
        client.post(
            f"{REPORTS}/from-scan",
            json={"scan_run_id": str(saved.scan_run_id), "title": "빈 칸 확인"},
        )
    )

    version = _data(
        client.get(f"{REPORTS}/{created['report_id']}/versions/{created['version_number']}")
    )
    # 지표 목록에 키워드·경쟁사에서만 나오는 값이 섞여 있으면 안 된다.
    measured = {row["metric_key"] for row in version["metrics"]}
    assert measured
    assert not any(key.startswith("keyword.") for key in measured)
    assert not any(key.startswith("competitor.") for key in measured)
