"""Shared fixtures for scoring evaluator tests.

The synthetic specification below is intentionally tiny so that every arithmetic
assertion in the tests can be verified by hand.
"""

from __future__ import annotations

from typing import Any

import pytest


def _check(
    check_id: str,
    severity: str,
    scope: str = "URL",
    owner: str = "DEVELOPER",
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title_ko": check_id,
        "title_en": check_id,
        "severity": severity,
        "scope": scope,
        "remediation_owner": owner,
    }


@pytest.fixture
def tiny_spec_dict() -> dict[str, Any]:
    """Two categories, weights 70 / 30.

    cat_a: blocker(1.00) + major(0.30) + info(0.00)  -> full budget 1.30
    cat_b: critical(0.60) + minor(0.10)              -> full budget 0.70
    """
    return {
        "spec_id": "veo.test.tiny",
        "domain": "SEO_READINESS",
        "version": "1.0.0",
        "status": "PUBLISHED",
        "effective_at": "2026-07-28T00:00:00+09:00",
        "methodology_owner": "VEO-LAB",
        "implementation_owner": "VENOM",
        "score_meaning": {
            "ko": "테스트용 준비도",
            "en": "test readiness",
            "is_rank_prediction": False,
        },
        "severity_coefficients": {
            "BLOCKER": 1.00,
            "CRITICAL": 0.60,
            "MAJOR": 0.30,
            "MINOR": 0.10,
            "INFO": 0.00,
        },
        "confidence_levels": {
            "DIRECT_OBSERVATION": 1.0,
            "OFFICIAL_API": 0.9,
            "HEURISTIC_LOW": 0.5,
        },
        "status_policy": {
            "fail_penalty_multiplier": 1.0,
            "warning_penalty_multiplier": 0.5,
            "pass_penalty_multiplier": 0.0,
            "not_applicable": "EXCLUDE_FROM_DENOMINATOR",
            "unknown": "EXCLUDE_FROM_SCORE_REDUCE_COVERAGE",
        },
        "url_importance": {
            "CONVERSION_OR_HOME": 3.0,
            "CONTENT_OR_PRODUCT": 1.0,
            "INTENTIONAL_NOINDEX": 0.0,
        },
        "categories": [
            {
                "id": "cat_a",
                "weight": 70,
                "name_ko": "가",
                "name_en": "A",
                "checks": [
                    _check("test.a.blocker", "BLOCKER"),
                    _check("test.a.major", "MAJOR"),
                    _check("test.a.info", "INFO"),
                ],
            },
            {
                "id": "cat_b",
                "weight": 30,
                "name_ko": "나",
                "name_en": "B",
                "checks": [
                    _check("test.b.critical", "CRITICAL"),
                    _check("test.b.minor", "MINOR"),
                ],
            },
        ],
        "caps": [
            {
                "id": "hard_block",
                "max_overall_score": 25,
                "reason_ko": "전면 차단",
                "release_condition_ko": "차단 해제 후 재검증",
                "trigger": {
                    "any_of": [
                        {"check_id": "test.a.blocker", "status": "FAIL", "min_coverage": 0.9}
                    ]
                },
            }
        ],
        "gates": [
            {
                "id": "blocked_gate",
                "status_code": "EXPOSURE_BLOCKED",
                "label_ko": "노출 차단",
                "label_en": "Exposure blocked",
                "trigger": {"any_of": [{"check_id": "test.b.critical", "status": "FAIL"}]},
            }
        ],
        "bands": [
            {"id": "ready", "min": 90, "max": 100, "label_ko": "준비", "label_en": "Ready"},
            {"id": "poor", "min": 0, "max": 89.999999, "label_ko": "취약", "label_en": "Poor"},
        ],
    }
