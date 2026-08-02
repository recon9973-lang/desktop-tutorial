"""점수 하락 경보 — 거래처가 나빠진 것을 사람이 화면을 열기 전에 안다 (#9 전반부).

알림 통로는 새로 만들지 않는다 — #45 가 만든 ``veo.notify.send_alert`` 하나를
재사용한다(0-D, notify 모듈 머리글의 약속). 이 파일이 하는 일은 판단뿐이다:
"방금 저장된 진단이, 같은 눈금의 직전 진단보다 의미 있게 낮은가."

## 비교 규칙

- **같은 명세 버전끼리만.** 판이 다르면 같은 판정도 다른 점수가 된다 — 그 차이를
  하락이라고 알리면 거짓 경보다(버전 취급 규칙 그대로).
- 직전 진단이 없으면(첫 측정) 비교할 것이 없다 — 조용히 지나간다.
- 문턱은 설정(``alert_score_drop_threshold``)이다. 채점 숫자가 아니라 언제 사람을
  부를 것인가라는 운영 판단이므로 명세가 아니라 설정에 산다(크롤 상한과 같은 지위).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.core.settings import get_settings
from veo.db.models.analysis import Scan, ScanRun, ScoreResult
from veo.notify import send_alert

__all__ = ["maybe_alert_score_drop", "should_alert"]

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


def maybe_alert_score_drop(
    db: Session,
    *,
    principal: Principal,
    site_id: uuid.UUID,
    origin: str,
    scan_run_id: uuid.UUID,
) -> None:
    """방금 저장된 진단을 직전 진단과 비교해, 하락이면 알린다.

    실패해도 예외를 올리지 않는다 — 경보 때문에 진단 저장이 죽으면 안 된다.
    """
    try:
        # 현재는 id 로 직접, 직전은 "그 실행을 뺀 최신" 으로 — 시작 시각 정렬에
        # 기대면 같은 초에 저장된 두 실행에서 비교가 조용히 어긋난다.
        current_statement = tenant_select(ScoreResult, principal).where(
            ScoreResult.scan_run_id == scan_run_id
        )
        assert_tenant_scoped(current_statement, principal.organization_id)
        current = db.execute(current_statement).scalars().first()
        if current is None or current.status != "SCORED":
            return

        previous_statement = (
            tenant_select(ScoreResult, principal)
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
        previous = db.execute(previous_statement).scalars().first()
        if previous is None:
            return

        threshold = get_settings().alert_score_drop_threshold
        if not should_alert(
            previous_score=previous.score,
            current_score=current.score,
            previous_spec_version=previous.spec_version,
            current_spec_version=current.spec_version,
            threshold=threshold,
        ):
            return

        drop = (previous.score or 0.0) - (current.score or 0.0)
        send_alert(
            title_ko=f"{origin} 점수 하락 ▼{drop:.1f}",
            body_ko=(
                f"SEO 준비도 {previous.score:.1f} → {current.score:.1f} "
                f"(명세 {current.spec_version}, 같은 눈금 비교). "
                "콘솔에서 무엇이 실패로 바뀌었는지 확인하십시오 — 최근 배포·개편이 "
                "원인인 경우가 많습니다."
            ),
            source="seo.score_drop",
        )
    except Exception:
        _log.exception("점수 하락 경보 판단에 실패했습니다. 진단 저장은 그대로 유지합니다.")
