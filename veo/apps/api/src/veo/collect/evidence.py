"""저장된 근거를 이름으로 되찾는다.

판정과 이슈는 근거를 ``kind:content_hash[:16]`` 라는 이름으로 부른다
(:meth:`veo.collect.contract.EvidenceRecord.of` 가 만든다). 그 이름을 담을 칸이
``evidence`` 테이블에 없었기 때문에, 저장된 근거 참조는 **하나도 되찾을 수 없었다** —
운영 DB 기준 근거 56줄, 부를 수 있는 것 0줄.

이 모듈이 `seo` 아래 있지 않은 이유는 근거가 SEO 만의 것이 아니기 때문이다. GEO 판정도
같은 이름으로 근거를 부른다.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.analysis import Evidence


def resolve_evidence(
    db: Session,
    *,
    principal: Principal,
    scan_run_id: uuid.UUID,
    evidence_ids: Sequence[str],
) -> list[Evidence]:
    """지적이 부르는 근거를 실제 행으로 찾아 준다. 찾지 못한 이름은 **조용히 버리지 않는다** —
    호출자가 요청한 개수와 받은 개수를 비교할 수 있도록 있는 것만 돌려주고, 없는 것은
    호출자가 세어서 사람에게 알린다.

    이 함수가 없던 동안 근거는 저장만 되고 한 번도 조회되지 않았다.
    """
    wanted = [value for value in dict.fromkeys(evidence_ids) if value]
    if not wanted:
        return []

    statement = tenant_select(Evidence, principal).where(
        Evidence.scan_run_id == scan_run_id,
        Evidence.evidence_id.in_(wanted),
    )
    assert_tenant_scoped(statement, principal.organization_id)
    found = {row.evidence_id: row for row in db.execute(statement).scalars()}
    # 요청한 순서를 지킨다. 지적이 근거를 나열한 순서에 의미가 있는 경우가 있다.
    return [found[name] for name in wanted if name in found]


__all__ = ["resolve_evidence"]
