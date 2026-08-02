"""채점 결과의 직렬화 — 화면이 받는 문서에 명세의 신원과 근거가 실려 있다.

이 성질들은 원래 ``POST /seo/scan`` 을 운반 수단으로 삼아 검사했다. 그 엔드포인트는
요청자가 넣은 provider 자료를 명세의 이름으로 채점하게 했으므로 닫았고(E1), 성질은
운반 수단과 무관하므로 여기서 서비스 경계 그대로 지킨다 — 같은 직렬화가 콘솔 진단
(`/seo/scans`)과 저장 스냅샷에 쓰인다.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

pytest.importorskip("pydantic")

from tests.seo.support import build_context

from veo.seo.router import _scan_payload
from veo.seo.service import run_seo_scan


def payload_for(**overrides: Any) -> dict[str, Any]:
    context = build_context("healthy")
    if overrides:
        context = replace(context, **overrides)
    return _scan_payload(run_seo_scan(context)).model_dump(mode="json")


class TestTheScoreCarriesItsSpecification:
    def test_a_scan_returns_a_score_with_its_specification_identity(self) -> None:
        data = payload_for()
        assert data["score"]["spec_id"] == "veo.seo.readiness"
        assert data["score"]["spec_checksum"]
        assert data["score"]["is_rank_prediction"] is False
        # 점수 자체는 발행 명세가 정한다. 특정 숫자를 못 박으면 명세를 개정할 때마다
        # 이 검사가 깨지고, 기대값을 기계적으로 갱신하게 되어 무엇을 지키는 검사인지
        # 사라진다. 이 검사가 지키는 것은 **점수에 명세의 신원이 붙어 나온다**는 것이다.
        assert isinstance(data["score"]["score"], (int, float))

    def test_a_scan_reports_unknown_checks_and_why(self) -> None:
        data = payload_for()
        unknown = {item["check_id"]: item for item in data["unknown_checks"]}
        assert "seo.perf.lcp_lab" in unknown
        assert unknown["seo.perf.lcp_lab"]["reason_ko"]

    def test_a_scan_summary_is_written_in_korean(self) -> None:
        data = payload_for()
        assert data["summary_ko"]
        assert any("가" <= ch <= "힣" for ch in data["summary_ko"])


class TestIssuesArriveWithTheirEvidence:
    def test_a_scan_on_a_broken_site_returns_issues_with_evidence(self) -> None:
        data = payload_for(robots_txt="User-agent: *\nDisallow: /\n")

        assert data["issues"]
        evidence_ids = {record["evidence_id"] for record in data["evidence"]}
        for issue in data["issues"]:
            assert set(issue["evidence_ids"]) <= evidence_ids
            assert issue["title_ko"]
            assert issue["remediation_owner"] in {
                "DEVELOPER",
                "MARKETER",
                "BUSINESS_OWNER",
                "OPERATIONS",
            }
