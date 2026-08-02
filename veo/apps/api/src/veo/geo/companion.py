"""SEO 진단에 동반되는 GEO 채점·저장 — 한 크롤, 두 눈금 (콘솔 재설계 ①).

같은 페이지들을 두 번 가져올 이유가 없다. SEO 콘솔 진단이 크롤을 마치면, 그
결과물(CrawlOutcome)로 GEO 문맥을 한 번 더 만들어 채점하고 **별도의 실행으로**
저장한다(Scan.kind=GEO). 점수는 합치지 않는다 — 재는 재료가 같다는 것과 뜻이
같다는 것은 다른 이야기다(geo/router 의 같은 문장).

동반 채점의 실패는 SEO 저장·응답을 죽이지 않는다. 대신 결과에 실패 사실이
실린다 — 조용히 사라지면 화면은 "GEO 를 잰 적 없음" 과 "재려다 실패" 를 구분할
수 없다.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from veo.authz import Principal
from veo.collect.from_crawl import context_from_crawl
from veo.geo.collectors.external_verifiability import CORROBORATION_PROVIDER
from veo.geo.corroboration import look_up_corroboration
from veo.geo.payload import payload_from
from veo.geo.service import GEO_SPEC_ID, run_geo_readiness
from veo.providers.naver.credentials import datalab_from_settings
from veo.providers.naver.search import NaverSearchClient
from veo.scoring import latest_published
from veo.seo.crawl import CrawlOutcome
from veo.seo.history import GEO_KIND, save_scan_run

__all__ = ["GeoCompanion", "score_and_save_geo_companion"]

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GeoCompanion:
    """동반 GEO 채점의 결과 요약 — 화면 전환기가 읽는 최소한."""

    scan_run_id: uuid.UUID | None
    score: float | None
    band_id: str | None
    spec_version: str | None
    #: 실패했으면 그 사실. 성공이면 None — "재려다 실패" 는 "잰 적 없음" 과 다르다.
    failure_note_ko: str | None = None


def score_and_save_geo_companion(
    db: Session,
    *,
    principal: Principal,
    site_id: uuid.UUID,
    target_url: str,
    outcome: CrawlOutcome,
    locale: str,
    urls_attempted: int,
    urls_collected: int,
) -> GeoCompanion:
    """이미 가져온 크롤로 GEO 를 채점해 저장한다. 예외는 결과로 바꾼다."""
    try:
        spec = latest_published(GEO_SPEC_ID)
        context = context_from_crawl(
            target_url=target_url, spec=spec, outcome=outcome, locale=locale
        )
        # 참고 조회(네이버) — geo/router 의 단독 진단과 같은 강화. 실패해도 진단은
        # 계속된다: 못 가져온 것은 측정 불가로 남고, 그 항목들은 점수 밖이다.
        corroboration, provider_state, _reason = look_up_corroboration(
            context, client=NaverSearchClient(credentials=datalab_from_settings())
        )
        context = replace(
            context,
            provider_states={
                **context.provider_states,
                CORROBORATION_PROVIDER: provider_state,
            },
            provider_payloads=(
                context.provider_payloads
                if corroboration is None
                else {**context.provider_payloads, CORROBORATION_PROVIDER: corroboration}
            ),
        )

        report = run_geo_readiness(context, spec=spec)
        snapshot = payload_from(target_url, report).model_dump(mode="json")
        saved = save_scan_run(
            db,
            principal=principal,
            site_id=site_id,
            result=report,
            context=context,
            urls_attempted=urls_attempted,
            urls_collected=urls_collected,
            report_snapshot=snapshot,
            kind=GEO_KIND,
        )
        return GeoCompanion(
            scan_run_id=saved.scan_run_id,
            score=saved.score,
            band_id=saved.band_id,
            spec_version=saved.spec_version,
        )
    except Exception:
        _log.exception("동반 GEO 채점에 실패했습니다. SEO 저장은 그대로 유지합니다.")
        return GeoCompanion(
            scan_run_id=None,
            score=None,
            band_id=None,
            spec_version=None,
            failure_note_ko=(
                "GEO 채점에 실패해 이번 실행에는 GEO 결과가 없습니다. 다시 측정하면 "
                "함께 계산됩니다."
            ),
        )
