"""동반 GEO 채점 — 한 크롤, 두 눈금, 두 실행 (콘솔 재설계 ①).

지키는 성질:

1. SEO 진단이 쓴 크롤 결과물로 GEO 가 채점·저장된다 — 재크롤 없음.
2. 두 실행은 별도의 축(Scan.kind SEO/GEO)에 매달리고, 점수는 합쳐지지 않는다.
3. 동반 채점 실패는 SEO 를 죽이지 않되, 실패 사실이 결과로 남는다 —
   "재려다 실패" 와 "잰 적 없음" 은 다른 사실이다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip("pydantic")

from tests.seo.test_regression_alert import project, site  # noqa: F401  (지역 픽스처 재사용)

#: 진단이 시작한 시각. 근거는 tests/seo/test_scan_history.py 의
#: TestHowLongTheScanTook 에 적혀 있다.
SCAN_STARTED_AT = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


def _crawl_outcome():  # type: ignore[no-untyped-def]
    from tests.seo.conftest import FIXTURE_NAME
    from tests.seo.support import build_context

    from veo.seo.crawl import CrawlOutcome

    context = build_context(FIXTURE_NAME)
    return CrawlOutcome(
        documents=tuple(context.documents.values()),
        robots_txt=context.robots_txt,
    )


def read_scan_history_ids(db_session, principal, site_id):  # type: ignore[no-untyped-def]
    from veo.seo.history import read_scan_history

    return [
        entry.scan_run_id
        for entry in read_scan_history(db_session, principal=principal, site_id=site_id)
    ]


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
            urls_collected=len(outcome.documents), started_at=SCAN_STARTED_AT,
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

    def test_each_axis_opens_only_through_its_own_door(
        self, db_session, principal, site  # noqa: F811
    ):
        """스냅샷의 모양은 축마다 다르다 — SEO 문으로 GEO 를 열면 응답 모델 검증에서
        터지거나, 더 나쁘게는 비슷한 필드끼리 조용히 맞물린다. 그래서 읽기가 축을
        말하면 다른 축의 실행은 '없다' 가 된다."""
        from veo.geo.companion import score_and_save_geo_companion
        from veo.seo.history import GEO_KIND, SEO_KIND, read_scan_report

        outcome = _crawl_outcome()
        companion = score_and_save_geo_companion(
            db_session,
            principal=principal,
            site_id=site.id,
            target_url=site.origin,
            outcome=outcome,
            locale="ko-KR",
            urls_attempted=len(outcome.documents),
            urls_collected=len(outcome.documents), started_at=SCAN_STARTED_AT,
        )
        assert companion.scan_run_id is not None

        through_geo_door = read_scan_report(
            db_session, principal=principal,
            scan_run_id=companion.scan_run_id, kind=GEO_KIND,
        )
        assert through_geo_door is not None
        assert "readiness" in through_geo_door, "GEO 스냅샷의 모양이 아니다"

        through_seo_door = read_scan_report(
            db_session, principal=principal,
            scan_run_id=companion.scan_run_id, kind=SEO_KIND,
        )
        assert through_seo_door is None, "GEO 실행이 SEO 문으로 열리면 모양이 섞인다"

    def test_the_saved_seo_snapshot_names_its_companion_geo_run(
        self, db_session, principal, site, monkeypatch  # noqa: F811
    ):
        """지난 SEO 결과를 다시 열 때 화면(SEO|GEO 전환기)은 짝이 되는 GEO 실행을
        스냅샷에서 찾는다 — 저장 순서가 바뀌어 geo 블록이 빠지면, 전환기는 방금 잰
        실행에서만 동작하고 어제 실행에서는 조용히 죽는다(재설계 ②의 연결 고리)."""
        import uuid as uuid_module

        import veo.seo.router as router_module
        from veo.seo.history import SEO_KIND, read_scan_report
        from veo.seo.schemas import SiteScanRequest

        outcome = _crawl_outcome()

        class StubCrawler:
            def crawl(self, target_url, *, extra_urls=(), max_urls=None):  # type: ignore[no-untyped-def]
                return outcome

            def collect(self, targets):  # type: ignore[no-untyped-def]
                return outcome.documents, outcome.robots_txt

        monkeypatch.setattr(router_module, "ConsoleCrawler", StubCrawler)

        response = router_module.run_site_scan(
            SiteScanRequest(
                target_url=site.origin, site_id=site.id, discover=False,
                urls=[doc.final_url for doc in outcome.documents],
            ),
            principal,
            str(uuid_module.uuid4()),
            db_session,
        )

        geo = response.data.geo
        assert geo is not None and geo.scan_run_id is not None

        seo_history = read_scan_history_ids(db_session, principal, site.id)
        assert seo_history, "SEO 실행이 저장되지 않았다"
        snapshot = read_scan_report(
            db_session, principal=principal, scan_run_id=seo_history[0], kind=SEO_KIND
        )
        assert snapshot is not None
        stored_geo = snapshot.get("geo")
        assert isinstance(stored_geo, dict)
        assert stored_geo.get("scan_run_id") == str(geo.scan_run_id), (
            "스냅샷이 동반 GEO 실행을 모른다 — 전환기가 지난 실행에서 동작하지 못한다"
        )

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
            urls_collected=len(outcome.documents), started_at=SCAN_STARTED_AT,
        )

        assert companion.scan_run_id is None
        assert companion.failure_note_ko is not None
