"""회귀 경보 — 거래처가 나빠진 것을 사람이 화면을 열기 전에 안다 (#9 + P1-7a).

알림 통로는 새로 만들지 않는다 — #45 가 만든 ``veo.notify.send_alert`` 하나를
재사용한다(0-D, notify 모듈 머리글의 약속). 이 파일이 하는 일은 판단뿐이다:
"방금 저장된 진단이 직전보다 **의미 있게 나빠졌는가**" — 두 갈래로 본다.

1. **점수 하락**: 같은 눈금(명세 버전)의 직전 점수보다 문턱 이상 낮다.
2. **새 이슈**: 직전 실행에는 없던 검사가 조치 목록에 나타났다 — 점수가 그대로여도
   (다른 개선이 하락을 상쇄했어도) 새로 깨진 것은 새로 깨진 것이다.

둘 중 하나라도 참이면 **한 건의 메시지**로 알린다. 두 통 보내면 채널이 시끄러워지고,
시끄러운 채널은 꺼진다 — 꺼진 알림은 없는 기능이다.

## 비교 규칙

- **같은 명세 버전끼리만.** 판이 다르면 같은 판정도 다른 점수·다른 이슈가 된다 —
  그 차이를 회귀라고 알리면 거짓 경보다(버전 취급 규칙 그대로).
- 직전 진단이 없으면(첫 측정) 비교할 것이 없다 — 조용히 지나간다.
- 스냅샷이 없는 옛 실행과는 이슈 diff 를 하지 않는다 — "그때 무엇이 있었는지"를
  모르면서 "새로 생겼다"고 말할 수는 없다.
- 문턱은 설정(``alert_score_drop_threshold``)이다. 채점 숫자가 아니라 언제 사람을
  부를 것인가라는 운영 판단이므로 명세가 아니라 설정에 산다(크롤 상한과 같은 지위).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import final

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.core.settings import get_settings
from veo.db.models.analysis import Scan, ScanRun, ScoreResult
from veo.notify import send_alert

__all__ = ["IssueDiff", "issue_diff", "maybe_alert_regression", "should_alert"]

_log = logging.getLogger(__name__)


def should_alert(
    *,
    previous_score: float | None,
    current_score: float | None,
    previous_spec_version: str,
    current_spec_version: str,
    threshold: float,
) -> bool:
    """순수한 판단 — 시험이 통신·DB 없이 셈만 본다."""
    if previous_score is None or current_score is None:
        return False
    if previous_spec_version != current_spec_version:
        # 다른 눈금의 두 숫자 — 차이를 하락이라고 부르면 거짓 경보다.
        return False
    return (previous_score - current_score) >= threshold


@final
@dataclass(frozen=True, slots=True)
class IssueDiff:
    """두 실행의 조치 목록 차이 — 새로 깨진 것과 고쳐진 것."""

    appeared_titles_ko: tuple[str, ...]
    resolved_count: int

    @property
    def appeared_count(self) -> int:
        return len(self.appeared_titles_ko)


def _issue_index(snapshot: Mapping[str, object] | None) -> dict[str, str] | None:
    """스냅샷의 조치 목록을 check_id → 제목으로. 스냅샷이 없으면 ``None`` — 빈 목록과
    "기록이 없음"은 다른 사실이고, 없는 기록과는 비교하지 않는다."""
    if snapshot is None:
        return None
    issues = snapshot.get("issues")
    if not isinstance(issues, list):
        return None
    index: dict[str, str] = {}
    for raw in issues:
        if not isinstance(raw, Mapping):
            continue
        check_id = raw.get("check_id")
        if isinstance(check_id, str) and check_id:
            title = raw.get("title_ko")
            index[check_id] = title if isinstance(title, str) else check_id
    return index


def issue_diff(
    previous_snapshot: Mapping[str, object] | None,
    current_snapshot: Mapping[str, object] | None,
) -> IssueDiff | None:
    """직전 실행 대비 새로 나타난·사라진 이슈. 어느 쪽이든 기록이 없으면 ``None``."""
    previous = _issue_index(previous_snapshot)
    current = _issue_index(current_snapshot)
    if previous is None or current is None:
        return None
    appeared = [check_id for check_id in current if check_id not in previous]
    resolved = [check_id for check_id in previous if check_id not in current]
    return IssueDiff(
        appeared_titles_ko=tuple(current[check_id] for check_id in sorted(appeared)),
        resolved_count=len(resolved),
    )


def _appeared_line(diff: IssueDiff) -> str:
    named = list(diff.appeared_titles_ko[:3])
    overflow = diff.appeared_count - len(named)
    names = " · ".join(named)
    return f"새로 생긴 이슈 {diff.appeared_count}건: {names}" + (
        f" 외 {overflow}건" if overflow > 0 else ""
    )


def maybe_alert_regression(
    db: Session,
    *,
    principal: Principal,
    site_id: uuid.UUID,
    origin: str,
    scan_run_id: uuid.UUID,
) -> None:
    """방금 저장된 진단을 직전 진단과 비교해, 나빠졌으면 한 건으로 알린다.

    실패해도 예외를 올리지 않는다 — 경보 때문에 진단 저장이 죽으면 안 된다.
    """
    try:
        # 현재는 id 로 직접, 직전은 "그 실행을 뺀 최신" 으로 — 시작 시각 정렬에
        # 기대면 같은 초에 저장된 두 실행에서 비교가 조용히 어긋난다.
        current_statement = (
            tenant_select(ScoreResult, principal)
            .add_columns(ScanRun)
            .join(ScanRun, ScoreResult.scan_run_id == ScanRun.id)
            .where(
                ScanRun.organization_id == principal.organization_id,
                ScoreResult.scan_run_id == scan_run_id,
            )
        )
        assert_tenant_scoped(current_statement, principal.organization_id)
        current_row = db.execute(current_statement).first()
        if current_row is None:
            return
        current, current_run = current_row.tuple()
        if current.status != "SCORED":
            return

        previous_statement = (
            tenant_select(ScoreResult, principal)
            .add_columns(ScanRun)
            .join(ScanRun, ScoreResult.scan_run_id == ScanRun.id)
            .join(Scan, Scan.id == ScanRun.scan_id)
            .where(
                # 조인한 테이블 전부를 조직으로 거른다 — 하나라도 빠지면 다른
                # 조직의 행과 맞물릴 수 있고, assert_tenant_scoped 가 거부한다.
                ScanRun.organization_id == principal.organization_id,
                Scan.organization_id == principal.organization_id,
                Scan.site_id == site_id,
                ScoreResult.status == "SCORED",
                ScoreResult.scan_run_id != scan_run_id,
                # 같은 명세(SEO 는 SEO 끼리)만. 동반 GEO 실행이 생기면서(companion)
                # 같은 사이트에 두 눈금의 점수가 쌓인다 — 이 필터가 없으면 '직전' 이
                # GEO 행이 되고, 버전 불일치로 경보가 영원히 침묵한다.
                ScoreResult.spec_id == current.spec_id,
            )
            .order_by(ScanRun.started_at.desc())
            .limit(1)
        )
        assert_tenant_scoped(previous_statement, principal.organization_id)
        previous_row = db.execute(previous_statement).first()
        if previous_row is None:
            return
        previous, previous_run = previous_row.tuple()

        threshold = get_settings().alert_score_drop_threshold
        dropped = should_alert(
            previous_score=previous.score,
            current_score=current.score,
            previous_spec_version=previous.spec_version,
            current_spec_version=current.spec_version,
            threshold=threshold,
        )
        # 이슈 diff 도 같은 눈금끼리만 — 판이 다르면 이슈 목록 자체가 다른 규칙이다.
        diff = (
            issue_diff(previous_run.report_snapshot, current_run.report_snapshot)
            if previous.spec_version == current.spec_version
            else None
        )
        appeared = diff is not None and diff.appeared_count > 0
        if not dropped and not appeared:
            return

        lines: list[str] = []
        if (
            dropped or (previous.score is not None and current.score is not None)
        ) and previous.score is not None and current.score is not None:
            lines.append(
                f"SEO 준비도 {previous.score:.1f} → {current.score:.1f} "
                f"(명세 {current.spec_version}, 같은 눈금 비교)."
            )
        if diff is not None and diff.appeared_count > 0:
            lines.append(_appeared_line(diff) + ".")
        if diff is not None and diff.resolved_count > 0:
            lines.append(f"고쳐진 이슈 {diff.resolved_count}건.")
        lines.append(
            "콘솔에서 무엇이 실패로 바뀌었는지 확인하십시오 — 최근 배포·개편이 "
            "원인인 경우가 많습니다."
        )

        drop = (previous.score or 0.0) - (current.score or 0.0)
        title = (
            f"{origin} 점수 하락 ▼{drop:.1f}"
            if dropped
            else f"{origin} 새 이슈 {diff.appeared_count if diff else 0}건"
        )
        send_alert(title_ko=title, body_ko=" ".join(lines), source="seo.regression")
    except Exception:
        _log.exception("회귀 경보 판단에 실패했습니다. 진단 저장은 그대로 유지합니다.")
