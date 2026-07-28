"""Shared values, synthetic specifications and DB seeding for the VEO-LAB tests.

Two things live here that are worth explaining.

**A synthetic specification family.** ``veo.lab_test.readiness`` is four checks across two
categories, small enough that every expected number below was worked out by hand. The
tests need a *baseline* on disk (v1.0.0) and a *candidate* the workflow can carry all the
way to publication (v1.1.0), and they need golden fixtures whose expectations match the
candidate — because a candidate that fails the fixtures must not be publishable, which is
the whole point of the gate.

**A copied specification root.** ``build_specs_root`` copies the real
``packages/scoring-specs`` and adds the synthetic family beside it, so
``VEO_SCORING_SPECS_DIR`` can point the loader at the copy without the real published
specifications going missing. Nothing under ``packages/`` is written to.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.core.settings import get_settings
from veo.db.models.analysis import Scan, ScanRun
from veo.db.models.analysis import ScoreResult as ScoreResultRow
from veo.db.models.identity import Organization, Project, Site, User
from veo.scoring import CheckOutcome, CheckStatus, ScoreResult, ScoringSpec, evaluate

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

API_PREFIX = get_settings().api_prefix
VERSIONS = f"{API_PREFIX}/lab/scoring-versions"

LAB_SPEC_ID = "veo.lab_test.readiness"
BASELINE_VERSION = "1.0.0"
CANDIDATE_VERSION = "1.1.0"

#: Weights of the two categories in the baseline and in the candidate. The only thing the
#: candidate changes is where 10 points of weight sit, which is exactly what the Korean
#: diff has to be able to name.
BASELINE_WEIGHTS = {"alpha": 60.0, "beta": 40.0}
CANDIDATE_WEIGHTS = {"alpha": 70.0, "beta": 30.0}


# --------------------------------------------------------------------------- #
# The synthetic specification family
# --------------------------------------------------------------------------- #


def _check(check_id: str, severity: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "title_ko": f"{check_id} 점검",
        "title_en": check_id,
        "severity": severity,
        "scope": "URL",
        "remediation_owner": "DEVELOPER",
    }


def lab_document(
    *,
    version: str,
    status: str,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """A complete, schema-valid specification document for the synthetic family."""
    resolved = dict(weights or BASELINE_WEIGHTS)
    return {
        "spec_id": LAB_SPEC_ID,
        "domain": "SEO_READINESS",
        "version": version,
        "status": status,
        "effective_at": "2026-08-01T00:00:00+09:00",
        "methodology_owner": "VEO-LAB",
        "implementation_owner": "VENOM",
        "compatible_collector_versions": ["lab-test-collector/1.x"],
        "score_meaning": {
            "ko": "실험용 준비도 점수입니다. 검색 순위 예측값이 아닙니다.",
            "en": "laboratory readiness score",
            "is_rank_prediction": False,
        },
        "severity_coefficients": {
            "BLOCKER": 1.0,
            "CRITICAL": 0.6,
            "MAJOR": 0.3,
            "MINOR": 0.1,
            "INFO": 0.0,
        },
        "confidence_levels": {"DIRECT_OBSERVATION": 1.0, "HEURISTIC_LOW": 0.5},
        "status_policy": {
            "fail_penalty_multiplier": 1.0,
            "warning_penalty_multiplier": 0.5,
            "pass_penalty_multiplier": 0.0,
            "not_applicable": "EXCLUDE_FROM_DENOMINATOR",
            "unknown": "EXCLUDE_FROM_SCORE_REDUCE_COVERAGE",
        },
        "url_importance": {"CONVERSION_OR_HOME": 3.0, "CONTENT_OR_PRODUCT": 1.0},
        "categories": [
            {
                "id": "alpha",
                "weight": resolved["alpha"],
                "name_ko": "알파",
                "name_en": "Alpha",
                "checks": [
                    _check("lab.alpha.one", "BLOCKER"),
                    _check("lab.alpha.two", "MAJOR"),
                ],
            },
            {
                "id": "beta",
                "weight": resolved["beta"],
                "name_ko": "베타",
                "name_en": "Beta",
                "checks": [
                    _check("lab.beta.one", "CRITICAL"),
                    _check("lab.beta.two", "MINOR"),
                ],
            },
        ],
        "caps": [
            {
                "id": "alpha_blocked",
                "max_overall_score": 30,
                "reason_ko": "알파 차단 항목이 실패했습니다.",
                "release_condition_ko": "차단을 해제한 뒤 재검증하세요.",
                "trigger": {"any_of": [{"check_id": "lab.alpha.one", "status": "FAIL"}]},
            }
        ],
        "gates": [
            {
                "id": "beta_gate",
                "status_code": "BETA_BLOCKED",
                "label_ko": "베타 차단",
                "label_en": "Beta blocked",
                "trigger": {"any_of": [{"check_id": "lab.beta.one", "status": "FAIL"}]},
            }
        ],
        "bands": [
            {"id": "ready", "min": 90, "max": 100, "label_ko": "준비", "label_en": "Ready"},
            {
                "id": "fair",
                "min": 60,
                "max": 89.999999,
                "label_ko": "보통",
                "label_en": "Fair",
            },
            {
                "id": "poor",
                "min": 0,
                "max": 59.999999,
                "label_ko": "취약",
                "label_en": "Poor",
            },
        ],
    }


def baseline_document() -> dict[str, Any]:
    """The published baseline, v1.0.0, weights 60/40."""
    return lab_document(
        version=BASELINE_VERSION, status="PUBLISHED", weights=BASELINE_WEIGHTS
    )


def candidate_document(**overrides: Any) -> dict[str, Any]:
    """The candidate the workflow publishes, v1.1.0, weights 70/30.

    Authored with ``status: PUBLISHED`` because the checksum is computed once, when the
    draft is created, and must not move when the row is published.
    """
    document = lab_document(
        version=CANDIDATE_VERSION, status="PUBLISHED", weights=CANDIDATE_WEIGHTS
    )
    document.update(overrides)
    return document


# --------------------------------------------------------------------------- #
# Golden fixtures for the synthetic family — expectations are the *candidate's*
# --------------------------------------------------------------------------- #

#: All four checks pass, so both categories score 100 under any weighting.
GOLDEN_ALL_PASS: dict[str, Any] = {
    "name": "labtest-01-all-pass",
    "spec_id": LAB_SPEC_ID,
    "spec_version": CANDIDATE_VERSION,
    "purpose_ko": "모든 항목이 통과하는 기준선입니다.",
    "default": {"status": "PASS", "confidence": 1.0},
    "overrides": [],
    "expected": {
        "status": "SCORED",
        "overall_score": 100.0,
        "overall_score_before_caps": 100.0,
        "band_id": "ready",
        "coverage": 1.0,
        "confidence": 1.0,
        "effective_weight_total": 100.0,
        "applied_cap_ids": [],
        "gate_status_codes": [],
        "categories": {
            "alpha": {"status": "SCORED", "score": 100.0, "budget": 1.3},
            "beta": {"status": "SCORED", "score": 100.0, "budget": 0.7},
        },
    },
}

#: alpha.two (MAJOR, 0.30) fails. alpha budget 1.30, penalty 0.30 -> 76.923077.
#: overall = (76.923077 x 70 + 100 x 30) / 100 = 83.846154 under the candidate's weights,
#: and 86.153846 under the baseline's — which is why the baseline fails this fixture.
GOLDEN_ALPHA_MAJOR_FAIL: dict[str, Any] = {
    "name": "labtest-02-alpha-major-fail",
    "spec_id": LAB_SPEC_ID,
    "spec_version": CANDIDATE_VERSION,
    "purpose_ko": "알파 카테고리의 MAJOR 항목 하나가 실패한 상태입니다.",
    "default": {"status": "PASS", "confidence": 1.0},
    "overrides": [{"check_id": "lab.alpha.two", "status": "FAIL", "confidence": 1.0}],
    "expected": {
        "status": "SCORED",
        "overall_score": 83.846154,
        "overall_score_before_caps": 83.846154,
        "band_id": "fair",
        "coverage": 1.0,
        "confidence": 1.0,
        "effective_weight_total": 100.0,
        "applied_cap_ids": [],
        "gate_status_codes": [],
        "categories": {
            "alpha": {"status": "SCORED", "score": 76.923077, "budget": 1.3},
            "beta": {"status": "SCORED", "score": 100.0},
        },
    },
}

LAB_GOLDEN_FIXTURES = (GOLDEN_ALL_PASS, GOLDEN_ALPHA_MAJOR_FAIL)

#: Hand-computed overall scores for the seeded score results, before and after.
SCORES_UNDER_BASELINE = {"alpha_fail": 86.153846, "beta_fail": 65.714286, "clean": 100.0}
SCORES_UNDER_CANDIDATE = {"alpha_fail": 83.846154, "beta_fail": 74.285714, "clean": 100.0}


def build_specs_root(destination: str | os.PathLike[str]) -> str:
    """Copy the real specification root and add the synthetic family to the copy."""
    from veo.scoring import find_specs_root

    source = find_specs_root()
    root = shutil.copytree(source, destination, dirs_exist_ok=True)

    spec_dir = os.path.join(root, "specs", LAB_SPEC_ID)
    os.makedirs(spec_dir, exist_ok=True)
    with open(os.path.join(spec_dir, f"{BASELINE_VERSION}.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump(baseline_document(), fh, allow_unicode=True, sort_keys=False)

    golden_dir = os.path.join(root, "golden")
    os.makedirs(golden_dir, exist_ok=True)
    for fixture in LAB_GOLDEN_FIXTURES:
        path = os.path.join(golden_dir, f"{fixture['name']}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(fixture, fh, ensure_ascii=False, indent=2)

    return str(root)


# --------------------------------------------------------------------------- #
# Test principals and rows
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Tenant:
    """One organization plus the three callers the workflow distinguishes."""

    organization_id: uuid.UUID
    lab_admin: Principal
    analyst: Principal
    viewer: Principal


@dataclass
class PrincipalBox:
    """The caller of the next request. Swapped by the ``act_as`` fixture."""

    current: Principal | None = None


def payload(response: Any) -> dict[str, Any]:
    body = response.json()
    assert body["error"] is None, body["error"]
    data: dict[str, Any] = body["data"]
    return data


def error_code(response: Any) -> str:
    body = response.json()
    assert body["data"] is None
    code: str = body["error"]["code"]
    return code


def error_message(response: Any) -> str:
    message: str = response.json()["error"]["message"]
    return message


def make_tenant(db: Session, label: str) -> Tenant:
    suffix = uuid.uuid4().hex[:8]
    organization = Organization(
        slug=f"veo-lab-{label}-{suffix}",
        name=f"VEO LAB 테스트 조직 {label}",
        is_active=True,
        settings={},
    )
    db.add(organization)

    users = {
        role: User(
            email=f"{role}-{suffix}@veo-lab-test.invalid",
            display_name=f"{role} {suffix}",
            is_active=True,
        )
        for role in ("lab", "analyst", "viewer")
    }
    db.add_all(list(users.values()))
    db.commit()

    def principal(key: str, role: Role) -> Principal:
        return Principal(
            user_id=users[key].id,
            organization_id=organization.id,
            roles=frozenset({role}),
            session_id=f"session-{suffix}-{key}",
            display_name=users[key].display_name,
        )

    return Tenant(
        organization_id=organization.id,
        lab_admin=principal("lab", Role.LAB_ADMIN),
        analyst=principal("analyst", Role.ANALYST),
        viewer=principal("viewer", Role.SALES_VIEWER),
    )


def make_scan_run(db: Session, tenant: Tenant, *, label: str) -> ScanRun:
    """A project, site, scan and one completed run, so a score has somewhere to hang."""
    suffix = uuid.uuid4().hex[:8]
    project = Project(
        organization_id=tenant.organization_id,
        slug=f"lab-{label}-{suffix}",
        name=f"LAB 프로젝트 {label}",
        locale="ko-KR",
        settings={},
    )
    db.add(project)
    db.flush()

    site = Site(
        organization_id=tenant.organization_id,
        project_id=project.id,
        origin=f"https://lab-{suffix}.example",
        display_name=f"LAB 사이트 {label}",
        is_primary=True,
        crawl_settings={},
    )
    db.add(site)
    db.flush()

    scan = Scan(
        organization_id=tenant.organization_id,
        project_id=project.id,
        site_id=site.id,
        kind="SEO",
        scope="SINGLE_URL",
        target_url=f"https://lab-{suffix}.example/",
        configuration={},
        is_active=True,
    )
    db.add(scan)
    db.flush()

    run = ScanRun(
        organization_id=tenant.organization_id,
        scan_id=scan.id,
        surface="CONSOLE",
        status="SUCCEEDED",
        collector_version="lab-test-collector/1.0.0",
        device_profile="MOBILE",
        urls_attempted=1,
        urls_collected=1,
        provider_states={},
        partial_reasons=[],
    )
    db.add(run)
    db.commit()
    return run


def outcomes_for(spec: ScoringSpec, failing: tuple[str, ...] = ()) -> list[CheckOutcome]:
    """Every check in ``spec``: PASS unless named in ``failing``."""
    return [
        CheckOutcome(
            check_id=check_id,
            status=CheckStatus.FAIL if check_id in failing else CheckStatus.PASS,
            confidence=1.0,
            evidence_ids=(f"lab-test::{check_id}",),
        )
        for check_id in spec.check_ids
    ]


def persist_score(
    db: Session,
    tenant: Tenant,
    run: ScanRun,
    spec: ScoringSpec,
    result: ScoreResult,
) -> ScoreResultRow:
    row = ScoreResultRow(
        organization_id=tenant.organization_id,
        scan_run_id=run.id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
        domain=str(spec.domain),
        status=result.status,
        score=result.overall_score,
        score_before_caps=result.overall_score_before_caps,
        band_id=result.band_id,
        coverage=result.coverage,
        confidence=result.confidence,
        effective_weight_total=result.effective_weight_total,
        category_scores=[c.model_dump(mode="json") for c in result.categories],
        applied_caps=[c.model_dump(mode="json") for c in result.applied_caps],
        gates=[g.model_dump(mode="json") for g in result.gates],
        calculation_trace=result.trace,
    )
    db.add(row)
    db.commit()
    return row


def seed_score(
    db: Session,
    tenant: Tenant,
    spec: ScoringSpec,
    *,
    label: str,
    failing: tuple[str, ...] = (),
) -> ScoreResultRow:
    run = make_scan_run(db, tenant, label=label)
    result = evaluate(spec, outcomes_for(spec, failing))
    return persist_score(db, tenant, run, spec, result)


def snapshot(row: ScoreResultRow) -> str:
    """A stable, comparable rendering of every column of a score row."""
    columns = sorted(c.name for c in ScoreResultRow.__table__.columns)
    return json.dumps(
        {name: _plain(getattr(row, name)) for name in columns},
        sort_keys=True,
        ensure_ascii=False,
    )


def _plain(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    return str(value)


def score_rows(db: Session, scan_run_id: uuid.UUID) -> list[ScoreResultRow]:
    db.rollback()
    return list(
        db.scalars(
            select(ScoreResultRow)
            .where(ScoreResultRow.scan_run_id == scan_run_id)
            .order_by(ScoreResultRow.created_at, ScoreResultRow.spec_version)
        )
    )
