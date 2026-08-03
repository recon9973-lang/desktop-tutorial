"""점수 하락 경보(#9 전반부) — 같은 눈금끼리만, 문턱을 넘을 때만, 저장을 죽이지 않고.

알림 통로는 #45 의 것을 재사용한다(0-D). 이 파일이 지키는 것은 판단이다.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic")

from veo.seo.regression import should_alert


@pytest.fixture
def project(db_session, organization):  # type: ignore[no-untyped-def]
    import uuid

    from veo.db.models.identity import Project

    row = Project(
        organization_id=organization.id,
        slug=f"p-{uuid.uuid4().hex[:8]}",
        name="테스트 프로젝트",
        locale="ko-KR",
        settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def site(db_session, organization, project):  # type: ignore[no-untyped-def]
    from veo.db.models.identity import Site

    row = Site(
        organization_id=organization.id,
        project_id=project.id,
        origin="https://clinic.example",
        display_name="테스트 사이트",
        is_primary=True,
        crawl_settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


class TestTheDecision:
    def test_a_real_drop_on_the_same_spec_alerts(self) -> None:
        assert should_alert(
            previous_score=71.8,
            current_score=70.2,
            previous_spec_version="1.9.0",
            current_spec_version="1.9.0",
            threshold=1.0,
        )

    def test_a_wobble_below_the_threshold_stays_quiet(self) -> None:
        """잔떨림마다 울리면 채널이 꺼지고, 그날부터 알림은 없는 기능이 된다."""
        assert not should_alert(
            previous_score=71.8,
            current_score=71.0,
            previous_spec_version="1.9.0",
            current_spec_version="1.9.0",
            threshold=1.0,
        )

    def test_different_spec_versions_never_compare(self) -> None:
        """판이 다르면 같은 판정도 다른 점수다 — 그 차이는 하락이 아니다."""
        assert not should_alert(
            previous_score=76.4,
            current_score=70.9,
            previous_spec_version="1.8.0",
            current_spec_version="1.9.0",
            threshold=1.0,
        )

    def test_an_unscored_side_never_compares(self) -> None:
        assert not should_alert(
            previous_score=None,
            current_score=70.0,
            previous_spec_version="1.9.0",
            current_spec_version="1.9.0",
            threshold=1.0,
        )


class TestIssueDiff:
    """새 이슈 감지 (P1-7a) — 점수가 안 떨어져도 새로 깨진 것은 새로 깨진 것이다."""

    def test_appeared_and_resolved_are_kept_apart(self) -> None:
        from veo.seo.regression import issue_diff

        before = [{"check_id": "seo.a", "title_ko": "가"}, {"check_id": "seo.b", "title_ko": "나"}]
        after = [{"check_id": "seo.b", "title_ko": "나"}, {"check_id": "seo.c", "title_ko": "다"}]
        diff = issue_diff({"issues": before}, {"issues": after})

        assert diff is not None
        assert diff.appeared_titles_ko == ("다",)
        assert diff.resolved_count == 1

    def test_a_missing_snapshot_means_no_comparison_not_an_empty_one(self) -> None:
        """스냅샷 없는 옛 실행 — "그때 무엇이 있었는지" 모르면 "새로 생겼다"고 못 한다."""
        from veo.seo.regression import issue_diff

        assert issue_diff(None, {"issues": []}) is None
        assert issue_diff({"issues": []}, None) is None

    def test_new_issues_alert_even_without_a_score_drop(
        self, db_session, principal, site, scan_result, scan_context, monkeypatch
    ):
        import veo.seo.regression as regression
        from veo.seo.history import save_scan_run
        from veo.seo.regression import maybe_alert_regression

        sent: list[tuple[str, str]] = []
        monkeypatch.setattr(
            regression,
            "send_alert",
            lambda **kwargs: sent.append((kwargs["title_ko"], kwargs["body_ko"])),
        )
        # 문턱을 크게 — 점수 하락으로는 절대 울리지 않게 해 두고, 이슈만으로 우는지 본다.
        monkeypatch.setattr(
            regression,
            "get_settings",
            lambda: SimpleNamespace(alert_score_drop_threshold=1000.0),
        )

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
            report_snapshot={"issues": []},
        )
        second = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
            report_snapshot={
                "issues": [{"check_id": "seo.meta.title_present", "title_ko": "제목이 없습니다"}]
            },
        )
        maybe_alert_regression(
            db_session, principal=principal, site_id=site.id,
            origin="https://clinic.example", scan_run_id=second.scan_run_id,
        )

        assert len(sent) == 1
        title, body = sent[0]
        assert "새 이슈 1건" in title
        assert "제목이 없습니다" in body

    def test_resolved_only_stays_quiet(
        self, db_session, principal, site, scan_result, scan_context, monkeypatch
    ):
        """좋아진 것만 있는 진단으로 울리면, 채널은 곧 꺼진다."""
        import veo.seo.regression as regression
        from veo.seo.history import save_scan_run
        from veo.seo.regression import maybe_alert_regression

        sent: list[str] = []
        monkeypatch.setattr(
            regression, "send_alert", lambda **kwargs: sent.append(kwargs["title_ko"])
        )
        monkeypatch.setattr(
            regression,
            "get_settings",
            lambda: SimpleNamespace(alert_score_drop_threshold=1000.0),
        )

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
            report_snapshot={"issues": [{"check_id": "seo.a", "title_ko": "가"}]},
        )
        second = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
            report_snapshot={"issues": []},
        )
        maybe_alert_regression(
            db_session, principal=principal, site_id=site.id,
            origin="https://clinic.example", scan_run_id=second.scan_run_id,
        )

        assert sent == []


class TestTheWiring:
    def test_two_saved_runs_reach_the_alert_path(
        self, db_session, principal, site, scan_result, scan_context, monkeypatch
    ):
        """저장 두 번 → 비교 한 번. 문턱 0 이면 동점(하락 0)도 경보 조건을 만족하므로
        배선 전체(질의→판단→발송)가 실제로 이어져 있는지를 이것으로 확인한다."""
        import veo.seo.regression as regression
        from veo.seo.history import save_scan_run
        from veo.seo.regression import maybe_alert_regression

        sent: list[str] = []
        monkeypatch.setattr(
            regression, "send_alert", lambda **kwargs: sent.append(kwargs["title_ko"])
        )
        monkeypatch.setattr(
            regression,
            "get_settings",
            lambda: SimpleNamespace(alert_score_drop_threshold=0.0),
        )

        first = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        maybe_alert_regression(
            db_session, principal=principal, site_id=site.id,
            origin="https://clinic.example", scan_run_id=first.scan_run_id,
        )
        assert sent == [], "첫 측정에는 비교할 직전이 없다"

        second = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        maybe_alert_regression(
            db_session, principal=principal, site_id=site.id,
            origin="https://clinic.example", scan_run_id=second.scan_run_id,
        )
        assert len(sent) == 1 and "clinic.example" in sent[0]

    def test_a_companion_geo_run_never_becomes_the_previous(
        self, db_session, principal, site, scan_result, scan_context, monkeypatch
    ):
        """같은 사이트에 GEO 실행이 끼어도 SEO 는 SEO 끼리만 비교한다 — 이 필터가
        없으면 '직전' 이 GEO 행이 되고 버전 불일치로 경보가 영원히 침묵한다."""
        from tests.seo.test_geo_companion import _crawl_outcome

        import veo.seo.regression as regression
        from veo.geo.companion import score_and_save_geo_companion
        from veo.seo.history import save_scan_run
        from veo.seo.regression import maybe_alert_regression

        sent: list[str] = []
        monkeypatch.setattr(
            regression, "send_alert", lambda **kwargs: sent.append(kwargs["title_ko"])
        )
        monkeypatch.setattr(
            regression,
            "get_settings",
            lambda: SimpleNamespace(alert_score_drop_threshold=0.0),
        )

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        outcome = _crawl_outcome()
        score_and_save_geo_companion(
            db_session, principal=principal, site_id=site.id,
            target_url=site.origin, outcome=outcome, locale="ko-KR",
            urls_attempted=1, urls_collected=1,
        )
        second = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        maybe_alert_regression(
            db_session, principal=principal, site_id=site.id,
            origin="https://clinic.example", scan_run_id=second.scan_run_id,
        )
        # GEO 행이 사이 끼었지만 SEO 직전(첫 실행)과 비교되어 경보가 나간다.
        assert len(sent) == 1

    def test_a_broken_query_never_breaks_the_save(
        self, db_session, principal, site, monkeypatch
    ):
        import veo.seo.regression as regression
        from veo.seo.regression import maybe_alert_regression

        def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("질의 실패")

        monkeypatch.setattr(regression, "tenant_select", explode)
        import uuid

        maybe_alert_regression(
            db_session, principal=principal, site_id=site.id,
            origin="https://clinic.example", scan_run_id=uuid.uuid4(),
        )
