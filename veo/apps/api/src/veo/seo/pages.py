"""저장된 진단에서 페이지별 판정을 재집계한다 — 재크롤 없이.

`check_results` 의 `affected_urls`/`evaluated_urls` (2026-08-02 부터 기록)를 페이지
축으로 뒤집는다. 대행사가 실제로 고치는 대상은 검사가 아니라 **페이지**다 — "canonical
문제 103장" 을 페이지 축으로 뒤집어야 "이 페이지의 문제 목록" 이 된다.

## 여기서 점수를 내지 않는 이유

페이지 **점수** 산식(단계별 URL 고정분모·페이지 관문·NOT_SAMPLED)은 설계됐지만
(SEO_SCORING_V3_PAGES.md) 아직 발행 명세가 아니다. 모든 숫자는 발행 명세에서만
나온다는 규칙에 따라, 명세 1.9.0 이 발행되기 전까지 이 모듈은 **판정 사실**만
돌려준다: 이 페이지에서 무엇이 실패했고, 무엇을 확인했고, 무엇은 재지 않았는가.
그것만으로 "고칠 페이지 특정" 이라는 용도는 성립한다.

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
from veo.db.models.analysis import CheckResult, ScanRun

__all__ = ["PageBreakdown", "PageChecks", "SiteCheck", "page_breakdown"]


@dataclass(frozen=True, slots=True)
class PageChecks:
    """한 페이지에서 실제로 판정된 검사들."""

    url: str
    failed: tuple[str, ...] = ()
    warned: tuple[str, ...] = ()
    passed: tuple[str, ...] = ()

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
    pages = tuple(
        sorted(
            (
                PageChecks(
                    url=url,
                    failed=tuple(sorted(failed.get(url, []))),
                    warned=tuple(sorted(warned.get(url, []))),
                    passed=tuple(sorted(passed.get(url, []))),
                )
                for url in urls
            ),
            key=lambda page: (-page.problem_count, page.url),
        )
    )

    legacy = bool(rows) and not any_lists
    notes: tuple[str, ...] = ()
    if legacy:
        notes = (
            "이 실행은 페이지별 판정 목록이 기록되기 전(2026-08-02 이전)에 저장된 "
            "것입니다. 페이지별 보기가 필요하면 사이트를 다시 진단하십시오 — 이후 "
            "실행부터는 자동으로 기록됩니다.",
        )

    return PageBreakdown(
        scan_run_id=scan_run_id,
        measured_at=run.finished_at,
        pages=pages,
        site_checks=tuple(sorted(site_checks, key=lambda c: c.check_id)),
        recorded_before_page_lists=legacy,
        notes_ko=notes,
    )
