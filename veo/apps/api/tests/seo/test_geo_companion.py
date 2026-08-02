"""동반 GEO 채점 — 한 크롤, 두 눈금, 두 실행 (콘솔 재설계 ①).

지키는 성질:

1. SEO 진단이 쓴 크롤 결과물로 GEO 가 채점·저장된다 — 재크롤 없음.
2. 두 실행은 별도의 축(Scan.kind SEO/GEO)에 매달리고, 점수는 합쳐지지 않는다.
3. 동반 채점 실패는 SEO 를 죽이지 않되, 실패 사실이 결과로 남는다 —
   "재려다 실패" 와 "잰 적 없음" 은 다른 사실이다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from tests.seo.test_regression_alert import project, site  # noqa: F401  (지역 픽스처 재사용)


def _crawl_outcome():  # type: ignore[no-untyped-def]
    from tests.seo.conftest import FIXTURE_NAME
    from tests.seo.support import build_context

    from veo.seo.crawl import CrawlOutcome

    context = build_context(FIXTURE_NAME)
    return CrawlOutcome(
        documents=tuple(context.documents.values()),
        robots_txt=context.robots_txt,
    )


class TestCompanionSaves:
    def test_one_crawl_yields_a_saved_geo_run_on_its_own_axis(
        self, db_session, principal, site  # noqa: F811
    ):
        from veo.db.models.analysis import Scan, ScanRun, ScoreResult
        from veo.geo.companion import score_and_save_geo_companion

        outcome = _crawl_outcome()
        companion = score_and_save_geo_companion(
            db_session,
            principal=principal,
            site_id=site.id,
            target_url=site.origin,
            outcome=outcome,
            locale="ko-KR",
            urls_attempted=len(outcome.documents),
            urls_collected=len(outcome.documents),
        )

        assert companion.failure_note_ko is None
        assert companion.scan_run_id is not None
        assert companion.spec_version == "1.3.0"

        run = db_session.get(ScanRun, companion.scan_run_id)
        scan = db_session.get(Scan, run.scan_id)
        assert scan.kind == "GEO", "GEO 실행이 SEO 축에 매달리면 이력이 섞인다"
        assert scan.site_id == site.id

        score_row = (
            db_session.query(ScoreResult)
            .filter_by(scan_run_id=companion.scan_run_id)
            .one()
        )
        assert score_row.spec_id == "veo.geo.readiness"
        assert score_row.score == companion.score

    def test_failure_becomes_a_note_not_an_exception(
        self, db_session, principal, site, monkeypatch  # noqa: F811
    ):
        import veo.geo.companion as companion_module
        from veo.geo.companion import score_and_save_geo_companion

        def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("채점 실패")

        monkeypatch.setattr(companion_module, "run_geo_readiness", explode)
        outcome = _crawl_outcome()

        companion = score_and_save_geo_companion(
            db_session,
            principal=principal,
            site_id=site.id,
            target_url=site.origin,
            outcome=outcome,
            locale="ko-KR",
            urls_attempted=len(outcome.documents),
            urls_collected=len(outcome.documents),
        )

        assert companion.scan_run_id is None
        assert companion.failure_note_ko is not None
