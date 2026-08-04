"""저장된 진단에서 페이지별 판정을 재집계한다 — 재크롤 없이.

`check_results` 의 `affected_urls`/`evaluated_urls` (2026-08-02 부터 기록)를 페이지
축으로 뒤집는다. 대행사가 실제로 고치는 대상은 검사가 아니라 **페이지**다 — "canonical
문제 103장" 을 페이지 축으로 뒤집어야 "이 페이지의 문제 목록" 이 된다.

## 페이지 점수 (1.9.0 부터)

명세 1.9.0 발행으로 페이지 점수 산식이 발행 명세가 됐다 — 계산은
:func:`veo.scoring.page.evaluate_page` 가 하고, 이 모듈은 저장된 판정 목록을
페이지 하나의 CheckOutcome 들로 변환해 넘길 뿐이다. 숫자는 여기서 만들지 않는다.

1.9.0 이전 명세로 저장된 실행에는 점수를 내지 않는다: 그 판의 규칙에는
NOT_SAMPLED 가 없어서, 표본 밖 성능 검사가 페이지마다 빠진 채 계산되면 그 판의
이름으로 그 판에 없던 산수를 하게 된다(ADR 0012). 점수 없이 판정 사실만 나간다.

## NOT_SAMPLED 가 실제로 발행되는 곳

표본 정책 검사(spec.sampled_check_ids)가 이 페이지의 evaluated 목록에 없으면 —
즉 명세가 이 페이지를 재지 않기로 했으면 — 여기서 NOT_SAMPLED 판정이 만들어진다.
사이트 점수 경로에는 이 상태가 등장하지 않는다.

## 판정 규칙 (저장된 목록 → 페이지 한 장의 사실)

```
페이지 P, 검사 C 의 저장 행에서:
  P ∈ affected_urls               → 그 행의 상태 그대로 (FAIL 또는 WARNING)
  P ∈ evaluated_urls, affected 아님   → PASS
  둘 다 아님                       → 이 페이지에서 잰 적 없음 (목록에 안 나옴)
```

목록이 NULL 인 행(2026-08-02 이전 실행, 또는 SITE 범위 검사)은 페이지 축으로
뒤집을 수 없다. SITE 검사는 사이트 전체의 사실로 **측정 날짜와 함께** 따로 돌려준다
— 페이지 화면에 날짜 없이 섞으면 "이 페이지의 문제" 로 잘못 읽힌다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.analysis import CheckResult, ScanRun, ScoreResult
from veo.scoring import CheckOutcome, CheckStatus, ScoringSpec, load_spec
from veo.scoring.errors import SpecNotFoundError
from veo.scoring.page import PageScore, evaluate_page

__all__ = ["PageBreakdown", "PageChecks", "SiteCheck", "page_breakdown"]


@dataclass(frozen=True, slots=True)
class PageChecks:
    """한 페이지에서 실제로 판정된 검사들, 그리고 (1.9.0+ 실행이면) 그 페이지의 점수."""

    url: str
    failed: tuple[str, ...] = ()
    warned: tuple[str, ...] = ()
    passed: tuple[str, ...] = ()
    #: 이 페이지의 점수 전체(산식 출처·항등식 포함). 1.9.0 이전 실행이면 ``None`` —
    #: 그 판의 규칙에 없던 산수를 그 판의 이름으로 하지 않는다(ADR 0012).
    score: PageScore | None = None

    @property
    def problem_count(self) -> int:
        return len(self.failed) + len(self.warned)


@dataclass(frozen=True, slots=True)
class SiteCheck:
    """사이트 전체 단위의 판정 — 페이지에 귀속되지 않는다."""

    check_id: str
    status: str
    reason_ko: str | None = None


@dataclass(frozen=True, slots=True)
class PageBreakdown:
    """한 실행의 판정을 페이지 축으로 뒤집은 것."""

    scan_run_id: uuid.UUID
    #: SITE 검사 값을 읽을 때의 기준 시각. 페이지 화면은 이 날짜를 함께 표기해야 한다.
    measured_at: datetime | None
    #: 문제 많은 페이지부터. 같으면 URL 순 — 순서가 결정적이어야 화면이 안정된다.
    pages: tuple[PageChecks, ...] = ()
    site_checks: tuple[SiteCheck, ...] = ()
    #: 페이지 목록이 기록되기 전의 실행이면 참. pages 가 비는 이유를 화면이 말할 수
    #: 있어야 한다 — 침묵하면 "이 사이트는 페이지가 없다" 로 읽힌다.
    recorded_before_page_lists: bool = False
    notes_ko: tuple[str, ...] = field(default_factory=tuple)


#: 페이지 축 뒤집기가 의미 있는 상태. UNKNOWN·N/A 행은 페이지 목록을 싣지 않는다.
_PAGE_STATUSES = frozenset({"FAIL", "WARNING", "PASS"})


def _spec_for_page_scores(
    db: Session, *, principal: Principal, scan_run_id: uuid.UUID
) -> ScoringSpec | None:
    """이 실행이 채점된 명세 — 페이지 점수를 낼 수 있는 판이면 돌려준다.

    어느 판으로 채점됐는지는 실행의 ScoreResult 행이 알고 있다(불변 기록).
    measurement_scope 는 1.9.0 이 처음 선언했다. 그 전 판으로 저장된 실행에
    1.9.0 의 산수(NOT_SAMPLED)를 적용하면 그 판의 이름으로 그 판에 없던 계산을
    하게 된다 — 점수 없이 판정 사실만 나간다(ADR 0012).
    """
    statement = tenant_select(ScoreResult, principal).where(
        ScoreResult.scan_run_id == scan_run_id
    )
    assert_tenant_scoped(statement, principal.organization_id)
    score_row = db.execute(statement).scalars().first()
    if score_row is None:
        return None
    try:
        spec = load_spec(score_row.spec_id, score_row.spec_version)
    except SpecNotFoundError:
        return None
    if spec.measurement_scope is None:
        return None
    return spec


def _score_page(
    spec: ScoringSpec, rows: list[CheckResult], url: str
) -> PageScore | None:
    """저장된 판정 목록을 페이지 하나의 CheckOutcome 들로 바꿔 채점한다.

    변환 규칙 (모듈 머리 주석의 판정 규칙에 셈만 더한 것):

    - ``url ∈ affected``       → 그 행의 상태 그대로 (FAIL/WARNING)
    - ``url ∈ evaluated``      → PASS
    - 표본 정책 검사인데 목록에 없다 → **NOT_SAMPLED** (여기서 처음 발행된다)
    - 행 전체가 UNKNOWN(재려다 실패) → 이 페이지에서도 UNKNOWN — 분모에 남는다
    - 그 밖에 목록에 없다        → 판정 없음(공급하지 않음) — 그 페이지에 그 항목이
      없었다는 뜻과 같은 셈이 된다
    """
    check_scope = {
        check.id: check.scope
        for category in spec.categories
        for check in category.checks
    }
    outcomes: list[CheckOutcome] = []
    for row in rows:
        if check_scope.get(row.check_id) != "URL":
            continue
        status: CheckStatus | None = None
        if row.status == "UNKNOWN":
            status = CheckStatus.UNKNOWN
        elif row.status == "NOT_APPLICABLE":
            status = None
        elif row.evaluated_urls is None:
            # 목록이 기록되기 전의 행 — 페이지 귀속을 지어내지 않는다.
            status = None
        elif url in set(row.affected_urls or []):
            status = CheckStatus(row.status)
        elif url in set(row.evaluated_urls):
            status = CheckStatus.PASS
        elif row.check_id in spec.sampled_check_ids:
            status = CheckStatus.NOT_SAMPLED
        if status is None:
            continue
        outcomes.append(
            CheckOutcome(
                check_id=row.check_id,
                status=status,
                # 확신도가 비어 있는 것은 **옛 실행**이다(2026-08-05 이전). 그때는 저장이
                # 등급으로 온 판정의 확신도를 버렸고, 그 칸을 NULL 로 되돌려 두었다.
                # 모르는 확신도는 1.0 으로 읽는다 — 채점기가 처음부터 쓰던 규칙과 같고
                # (`scoring/page.py`), 그것은 "깎지 않는다" 는 뜻이다. 임의의 숫자를
                # 지어내 손실을 부풀리거나 없애지 않는다.
                confidence=1.0 if row.confidence is None else row.confidence,
                evidence_ids=tuple(row.evidence_ids or []),
            )
        )
    if not outcomes:
        return None
    return evaluate_page(spec, outcomes)


def page_breakdown(
    db: Session, *, principal: Principal, scan_run_id: uuid.UUID
) -> PageBreakdown | None:
    """저장된 실행 하나를 페이지 축으로. 없거나 남의 것이면 ``None`` (404 로 답한다)."""
    statement = tenant_select(ScanRun, principal).where(ScanRun.id == scan_run_id)
    assert_tenant_scoped(statement, principal.organization_id)
    run = db.execute(statement).scalar_one_or_none()
    if run is None:
        return None

    rows_statement = tenant_select(CheckResult, principal).where(
        CheckResult.scan_run_id == scan_run_id
    )
    assert_tenant_scoped(rows_statement, principal.organization_id)
    rows = list(db.execute(rows_statement).scalars())

    failed: dict[str, list[str]] = {}
    warned: dict[str, list[str]] = {}
    passed: dict[str, list[str]] = {}
    site_checks: list[SiteCheck] = []
    any_lists = False

    for row in rows:
        if row.evaluated_urls is None:
            # 이 칸이 생기기 전의 실행. "기록되지 않았다" 이지 "페이지가 없었다" 가
            # 아니므로, 페이지 축으로 아무것도 지어내지 않는다.
            continue
        any_lists = True
        if not row.evaluated_urls:
            # 페이지에 귀속되지 않는 판정 — 사이트 전체의 사실.
            site_checks.append(
                SiteCheck(
                    check_id=row.check_id,
                    status=row.status,
                    reason_ko=row.unknown_reason or row.not_applicable_reason,
                )
            )
            continue
        if row.status not in _PAGE_STATUSES:
            continue
        affected = set(row.affected_urls or [])
        bucket = failed if row.status == "FAIL" else warned
        for url in row.evaluated_urls:
            if url in affected:
                bucket.setdefault(url, []).append(row.check_id)
            else:
                passed.setdefault(url, []).append(row.check_id)

    urls = sorted(set(failed) | set(warned) | set(passed))
    spec = _spec_for_page_scores(db, principal=principal, scan_run_id=scan_run_id)
    pages = tuple(
        sorted(
            (
                PageChecks(
                    url=url,
                    failed=tuple(sorted(failed.get(url, []))),
                    warned=tuple(sorted(warned.get(url, []))),
                    passed=tuple(sorted(passed.get(url, []))),
                    score=_score_page(spec, rows, url) if spec is not None else None,
                )
                for url in urls
            ),
            key=lambda page: (-page.problem_count, page.url),
        )
    )

    legacy = bool(rows) and not any_lists
    notes_list: list[str] = []
    if legacy:
        notes_list.append(
            "이 실행은 페이지별 판정 목록이 기록되기 전(2026-08-02 이전)에 저장된 "
            "것입니다. 페이지별 보기가 필요하면 사이트를 다시 진단하십시오 — 이후 "
            "실행부터는 자동으로 기록됩니다."
        )
    if spec is None and pages:
        notes_list.append(
            "이 실행은 채점 명세 1.9.0 이전 판으로 저장되어 페이지 점수가 없습니다. "
            "판정 사실(실패·주의·통과)은 그대로 유효합니다 — 점수가 필요하면 사이트를 "
            "다시 진단하십시오."
        )
    notes: tuple[str, ...] = tuple(notes_list)

    return PageBreakdown(
        scan_run_id=scan_run_id,
        measured_at=run.finished_at,
        pages=pages,
        site_checks=tuple(sorted(site_checks, key=lambda c: c.check_id)),
        recorded_before_page_lists=legacy,
        notes_ko=notes,
    )
