"""진단 결과를 남기는 규칙.

지금까지 진단은 채점하고 **버렸다.** 그래서 "지난달보다 나아졌나" 에 답할 수 없었고,
고객에게 낼 보고서도 매번 새로 뽑는 단발성 숫자였다. 기획서 §10 은 방법론 버전이 바뀌어도
과거 점수를 보존하라고 요구하고, 구현계획 3단계는 이슈의 재발 추적을 요구한다. 둘 다
결과가 남아 있어야 성립한다.

여기서 고정하는 것:

* 한 번의 진단은 `ScanRun` 한 줄과 `ScoreResult` 한 줄을 남긴다 — 시계열의 단위다.
* 항목별 판정과 근거도 남긴다. 점수만 남기면 "왜 35점이었는지" 를 나중에 설명할 수 없다.
* 같은 문제가 다시 잡히면 **새 이슈를 만들지 않고** 기존 이슈를 갱신한다. 매번 새로 만들면
  이슈 목록이 진단 횟수만큼 불어나고, 담당자 배정과 재검증 이력이 끊긴다.
* 다른 조직의 사이트에는 저장하지 못한다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

pytest.importorskip("sqlalchemy")

#: 진단이 시작한 시각. 저장되는 종료 시각보다 **앞선다** — 그래야 소요 시간이 0 이
#: 아니다. 2026-08-04 운영 DB 에는 39건이 전부 시작=종료로 남아 있었다: 저장하는 쪽이
#: 이 값을 못 받아 종료 시각으로 채웠고, 부르는 곳 두 군데 모두 넘기지 않았다.
#: 고정 시각을 쓰는 이유는 시험이 시계에 흔들리지 않게 하기 위해서다.
STARTED = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)

#: 그보다 **먼저** 잰 실행. 두 실행을 나란히 놓는 시험이 쓴다.
#:
#: 같은 시각을 주면 안 된다. 이력은 잰 순서로 정렬되는데, 동점이면 어느 쪽이 '최신'
#: 인지 그때그때 달라진다 — 같은 트랜잭션에서 저장된 행은 `created_at` 마저 같아서
#: (PostgreSQL 의 `now()` 는 트랜잭션 시각이다) 가를 기준이 남지 않는다. 실제로도
#: 두 진단은 다른 시각에 시작한다.
EARLIER = datetime(2026, 8, 3, 0, 0, tzinfo=UTC)


@pytest.fixture
def project(db_session, organization):
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
def site(db_session, organization, project):
    from veo.db.models.identity import Site

    row = Site(
        organization_id=organization.id,
        project_id=project.id,
        origin="https://example.com",
        display_name="테스트 사이트",
        is_primary=True,
        crawl_settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


class TestSavingOneRun:
    def test_a_run_and_its_score_are_recorded(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session,
            principal=principal,
            site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=3,
            urls_collected=3, started_at=STARTED,
        )

        assert saved.score is not None
        assert saved.spec_version != ""
        assert saved.finished_at is not None

    def test_check_results_are_recorded_so_the_score_can_be_explained(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        rows = db_session.query(CheckResult).filter_by(scan_run_id=saved.scan_run_id).all()
        assert len(rows) == len(scan_result.score.outcomes)

    def test_the_pages_a_check_judged_survive_into_storage(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context,
    ):
        """"canonical 문제 103장" 만 남으면 **어느** 103장인지가 사라진다.

        수집기는 목록을 알고 있었고 저장 직전에 버려지고 있었다 — 비용 근거·측정
        조건과 같은 "저장할 때 흘림" 의 다섯 번째 사례. 이 목록이 페이지별 점수
        재집계(v3 §7-③)의 기반이므로, URL 무게가 있는 판정은 판정한 페이지 목록을
        반드시 함께 남겨야 한다.
        """
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        source = {o.check_id: o for o in scan_result.score.outcomes}
        with_urls = [c for c, o in source.items() if o.evaluated_urls]
        assert with_urls, "픽스처에 URL 목록을 실은 판정이 하나도 없다 — 배선이 끊겼다"

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        rows = {
            row.check_id: row
            for row in db_session.query(CheckResult)
            .filter_by(scan_run_id=saved.scan_run_id)
            .all()
        }
        for check_id in with_urls:
            assert rows[check_id].evaluated_urls == list(source[check_id].evaluated_urls)
            assert rows[check_id].affected_urls == list(source[check_id].affected_urls)

    def test_what_a_check_actually_measured_survives_into_storage(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context,
    ):
        """실측값이 남아야 회차 간 "값이 어떻게 변했나" 를 비교할 수 있다.

        수집기 139곳이 observed_value 를 만들어 넘기는데 저장이 ``{}`` 상수로
        전부 버리고 있었다 — "저장할 때 흘림" 의 여섯 번째 사례(2026-08-03).
        """
        from pydantic_core import to_jsonable_python

        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        source = {o.check_id: o for o in scan_result.score.outcomes}
        with_values = [c for c, o in source.items() if o.observed_value is not None]
        assert with_values, "픽스처에 실측값을 실은 판정이 하나도 없다 — 배선이 끊겼다"

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        rows = {
            row.check_id: row
            for row in db_session.query(CheckResult)
            .filter_by(scan_run_id=saved.scan_run_id)
            .all()
        }
        for check_id in with_values:
            stored = rows[check_id].observed_value
            original = to_jsonable_python(source[check_id].observed_value, fallback=str)
            expected = original if isinstance(original, dict) else {"value": original}
            assert stored == expected, check_id
        # 값을 남기지 않은 판정은 빈 객체 그대로 — 지어내지 않는다.
        without = next((c for c, o in source.items() if o.observed_value is None), None)
        if without is not None:
            assert rows[without].observed_value == {}

    def test_the_reason_a_check_was_unmeasurable_survives(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        """'측정 불가' 만 남기면 나중에 고장으로 읽힌다. 이유가 함께 남아야 한다."""
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        unknown = (
            db_session.query(CheckResult)
            .filter_by(scan_run_id=saved.scan_run_id, status="UNKNOWN")
            .all()
        )
        assert unknown, "이 fixture 는 측정 불가 항목을 포함해야 한다"
        assert all(row.unknown_reason for row in unknown)


class TestHistory:
    def test_two_runs_read_back_newest_first(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import read_scan_history, save_scan_run

        for _ in range(2):
            save_scan_run(
                db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
                urls_attempted=1, urls_collected=1, started_at=STARTED,
            )

        history = read_scan_history(db_session, principal=principal, site_id=site.id)

        assert len(history) == 2
        assert history[0].started_at >= history[1].started_at

    def test_another_organization_cannot_read_this_history(
        self,
        db_session,
        principal,
        other_principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        assert read_scan_history(db_session, principal=other_principal, site_id=site.id) == []


class TestIssueLifecycle:
    def test_the_same_problem_twice_updates_one_issue(
        self,
        db_session,
        principal,
        site,
        project,
        scan_result,
        scan_context
    ):
        from veo.db.models.analysis import Issue
        from veo.seo.history import save_scan_run

        first = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )
        second = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        issues = db_session.query(Issue).filter_by(project_id=project.id).all()
        assert len(issues) == len({issue.check_id for issue in issues}), (
            "같은 검사 항목으로 이슈가 두 줄 생기면 안 된다"
        )
        assert all(issue.first_seen_run_id == first.scan_run_id for issue in issues)
        assert all(issue.last_seen_run_id == second.scan_run_id for issue in issues)

    def test_a_resolved_problem_that_returns_is_counted_as_a_regression(
        self,
        db_session,
        principal,
        site,
        project,
        scan_result,
        scan_context
    ):
        """고쳤다가 다시 깨진 것과 한 번도 못 고친 것은 다른 사건이다."""
        from veo.db.models.analysis import Issue
        from veo.seo.history import save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )
        resolved = db_session.query(Issue).filter_by(project_id=project.id).first()
        assert resolved is not None
        resolved.state = "VERIFIED_RESOLVED"
        db_session.flush()

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )
        db_session.refresh(resolved)

        assert resolved.state == "RECURRED"
        assert resolved.regression_count == 1


class TestReadingAPastRunBack:
    """화면을 닫았다 다시 열면 지난 결과가 그대로 보여야 한다.

    같은 도메인을 하루에도 몇 번씩 다시 재는 것은 대상 사이트에도, 우리 쪽 비용에도
    부담이다. 변경을 확인하려고 **일부러** 다시 재는 경우가 아니면 다시 재지 않는다.
    그러려면 저장된 결과를 그대로 되읽을 수 있어야 한다.
    """

    def test_the_report_comes_back_exactly_as_it_was_shown(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import read_scan_report, save_scan_run

        snapshot = {"summary_ko": "그때의 요약", "issues": [{"check_id": "x"}]}
        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED, report_snapshot=snapshot,
        )

        assert read_scan_report(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        ) == snapshot

    def test_another_organization_cannot_read_the_report(
        self,
        db_session,
        principal,
        other_principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import read_scan_report, save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
            report_snapshot={"summary_ko": "비밀"},
        )

        assert read_scan_report(
            db_session, principal=other_principal, scan_run_id=saved.scan_run_id
        ) is None


class TestWhoRanIt:
    def test_the_history_names_the_person_who_ran_the_scan(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context,
        user
    ):
        """'언제' 만으로는 부족하다. 직원 여럿이 같은 사이트를 만진다."""
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        entry = read_scan_history(db_session, principal=principal, site_id=site.id)[0]
        assert entry.requested_by_name == user.display_name

    def test_a_departed_employee_does_not_take_the_history_with_them(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context,
        user
    ):
        from veo.db.models.identity import User
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )
        db_session.delete(db_session.get(User, user.id))
        db_session.flush()

        history = read_scan_history(db_session, principal=principal, site_id=site.id)
        assert len(history) == 1
        assert history[0].requested_by_name is None


class TestMeasurementConditions:
    """어떤 조건에서 쟀는지를 남긴다.

    `MeasurementConditions` 는 스스로 "모든 결과와 함께 저장된다" 고 적어 두었지만 어떤
    결과와도 함께 저장되지 않았다. `scan_runs` 에는 칸이 있었고, 그 칸들은 전부 상수로
    채워지고 있었다 — `device_profile="DESKTOP"`, `provider_states={}`.

    조건이 없으면 두 실행을 나란히 놓아도 되는지 판단할 근거가 없고, 조건이 달라서 생긴
    차이가 **사이트가 좋아졌다** 는 뜻으로 읽힌다.
    """

    def test_the_conditions_are_recorded(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.db.models.analysis import ScanRun
        from veo.seo.conditions import conditions_from_stored
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        run = db_session.get(ScanRun, saved.scan_run_id)
        conditions = conditions_from_stored(run.measurement_conditions)
        assert conditions is not None
        assert conditions.spec_id == scan_result.score.spec_id
        assert conditions.spec_checksum == scan_result.score.spec_checksum
        assert conditions.pages_examined == len(scan_context.documents)
        assert conditions.locale == scan_context.locale

    def test_the_device_is_not_claimed_to_be_a_desktop_browser(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        """VEO 는 표시된 봇으로 가져온다. 뷰포트도 자바스크립트 엔진도 없다.

        'DESKTOP' 은 고객의 방문자가 보는 화면에 대한 주장이 된다. 봇 수집과 데스크톱
        브라우저 수집을 같은 비교 바구니에 넣게 된다.
        """
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        run = db_session.get(ScanRun, saved.scan_run_id)
        assert run.device_profile == "BOT"
        assert run.user_agent is not None and "VEO" in run.user_agent

    def test_a_renderer_that_did_not_run_is_not_recorded_as_having_run(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.conditions import RENDERER_RAW_HTML, renderer_for

        assert not scan_context.rendered_dom
        assert renderer_for(scan_context) == RENDERER_RAW_HTML

    def test_a_run_saved_before_this_existed_is_not_comparable(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        """조건이 없는 실행을 '비교 가능' 으로 두지 않는다.

        기록이 없다는 사실이 "같은 조건이었다" 는 주장으로 바뀌면 안 된다.
        """
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import read_scan_history, save_scan_run

        older = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=EARLIER,
        )
        # 이 칸이 생기기 전에 저장된 실행을 흉내 낸다.
        db_session.get(ScanRun, older.scan_run_id).measurement_conditions = None
        db_session.flush()
        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        entries = read_scan_history(db_session, principal=principal, site_id=site.id)
        stale = next(one for one in entries if one.scan_run_id == older.scan_run_id)
        assert stale.comparable_with_latest is False
        assert stale.incomparable_reason_ko is not None
        assert not stale.incomparable_reason_ko.isascii()

    def test_the_newest_run_is_always_comparable_with_itself(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        entries = read_scan_history(db_session, principal=principal, site_id=site.id)
        assert entries[0].comparable_with_latest is True
        assert entries[0].incomparable_reason_ko is None

    def test_two_runs_measured_the_same_way_stay_comparable(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        from veo.seo.history import read_scan_history, save_scan_run

        for _ in range(2):
            save_scan_run(
                db_session, principal=principal, site_id=site.id, result=scan_result,
                context=scan_context, urls_attempted=1, urls_collected=1, started_at=STARTED,
            )

        entries = read_scan_history(db_session, principal=principal, site_id=site.id)
        assert [one.comparable_with_latest for one in entries] == [True, True]

    def test_a_different_methodology_breaks_the_line(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        """명세가 개정되면 두 점수는 같은 자로 잰 것이 아니다."""
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import read_scan_history, save_scan_run

        older = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=EARLIER,
        )
        run = db_session.get(ScanRun, older.scan_run_id)
        run.measurement_conditions = {
            **run.measurement_conditions,
            "spec_version": "0.9.0",
            "spec_checksum": "0" * 64,
        }
        db_session.flush()
        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=scan_context, urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        entries = read_scan_history(db_session, principal=principal, site_id=site.id)
        stale = next(one for one in entries if one.scan_run_id == older.scan_run_id)
        assert stale.comparable_with_latest is False
        assert stale.incomparable_reason_ko is not None

    def test_provider_states_are_kept_rather_than_emptied(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        """DEGRADED 는 ENABLED 와 같은 측정이 아니다.

        한쪽의 공급자가 흔들려 생긴 UNKNOWN 이 사이트 품질 차이로 읽히면 안 된다.
        빈 딕셔너리로 저장하면 그 구분이 영영 사라진다.
        """
        from dataclasses import replace

        from veo.contracts.enums import ProviderState
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import save_scan_run

        context = replace(
            scan_context, provider_states={"naver_searchad": ProviderState.DEGRADED}
        )
        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=context, urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        run = db_session.get(ScanRun, saved.scan_run_id)
        assert run.provider_states != {}
        assert "naver_searchad" in run.provider_states

    def test_a_degraded_provider_breaks_comparability(
        self,
        db_session,
        principal,
        site,
        scan_result,
        scan_context
    ):
        """공급자가 흔들린 실행은 멀쩡한 실행과 나란히 놓을 수 없다.

        한쪽에서만 '측정 불가' 가 난 항목이 생기고, 그 구멍이 점수 차이로 나타난다.
        사이트는 그대로인데 그래프는 떨어진다.
        """
        from dataclasses import replace

        from veo.contracts.enums import ProviderState
        from veo.seo.history import read_scan_history, save_scan_run

        healthy = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=replace(scan_context, provider_states={"naver": ProviderState.ENABLED}),
            urls_attempted=1, urls_collected=1, started_at=EARLIER,
        )
        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            context=replace(scan_context, provider_states={"naver": ProviderState.DEGRADED}),
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        entries = read_scan_history(db_session, principal=principal, site_id=site.id)
        earlier = next(one for one in entries if one.scan_run_id == healthy.scan_run_id)
        assert earlier.comparable_with_latest is False
        assert "외부 데이터" in (earlier.incomparable_reason_ko or "")


class TestEvidenceCanBeReached:
    """지적이 부르는 근거를 실제로 찾을 수 있어야 한다.

    `check_results.evidence_ids` 와 `issues.evidence_ids` 는
    `http_response:f98f677064c9d854` 같은 이름을 저장한다. `evidence` 테이블에는 그
    이름을 담을 칸이 없었다 — 운영 DB 기준 근거 56줄, 부를 수 있는 것 0줄.

    감사할 수 없는 지적은 소문이다.
    """

    def test_the_name_a_finding_uses_is_stored_on_the_row(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.db.models.analysis import Evidence
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        stored = {
            row.evidence_id
            for row in db_session.query(Evidence).filter_by(scan_run_id=saved.scan_run_id)
        }
        assert stored == {record.evidence_id for record in scan_result.evidence}
        assert all(name for name in stored)

    def test_every_cited_name_resolves(
        self, db_session, principal, site, scan_result, scan_context
    ):
        """판정이 부른 이름 중 되찾지 못하는 것이 하나도 없어야 한다."""
        from veo.collect.evidence import resolve_evidence
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        cited = {
            name
            for row in db_session.query(CheckResult).filter_by(scan_run_id=saved.scan_run_id)
            for name in (row.evidence_ids or [])
        }
        assert cited, "이 픽스처는 근거를 인용하는 판정을 포함해야 한다"

        found = resolve_evidence(
            db_session, principal=principal,
            scan_run_id=saved.scan_run_id, evidence_ids=sorted(cited),
        )
        assert {row.evidence_id for row in found} == cited

    def test_the_order_a_finding_listed_them_in_is_kept(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.collect.evidence import resolve_evidence
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )
        names = [record.evidence_id for record in scan_result.evidence][:3]

        found = resolve_evidence(
            db_session, principal=principal,
            scan_run_id=saved.scan_run_id, evidence_ids=list(reversed(names)),
        )
        assert [row.evidence_id for row in found] == list(reversed(names))

    def test_a_name_that_does_not_exist_is_left_out_rather_than_faked(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.collect.evidence import resolve_evidence
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        found = resolve_evidence(
            db_session, principal=principal, scan_run_id=saved.scan_run_id,
            evidence_ids=["http_response:0000000000000000"],
        )
        assert found == []

    def test_another_organizations_evidence_is_not_reachable(
        self, db_session, principal, other_principal, site, scan_result, scan_context
    ):
        from veo.collect.evidence import resolve_evidence
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )
        names = [record.evidence_id for record in scan_result.evidence]

        found = resolve_evidence(
            db_session, principal=other_principal,
            scan_run_id=saved.scan_run_id, evidence_ids=names,
        )
        assert found == []


class TestHowLongTheScanTook:
    """진단이 얼마나 걸렸는지가 **DB 에** 남는가.

    2026-08-04, 운영 DB 의 `scan_runs` 39건이 전부 `started_at == finished_at` 이었다.
    마이크로초까지 같았다. 원인은 두 줄이다: 저장하는 쪽이
    `started_at: datetime | None = None` 을 받아 `started_at or finished` 로 채웠고,
    부르는 곳 두 군데(`seo/router.py`, `geo/companion.py`) 모두 그 값을 넘기지 않았다.

    로그에는 단계별 시간이 멀쩡히 찍히고 있었다. 그래서 "느려졌다" 는 눈에 보였지만
    **"진단 한 번이 몇 초냐"** 에는 답할 수 없었고, 오픈 후 사용량이 몇 배로 늘 때
    서버를 얼마나 키워야 하는지 숫자로 말할 근거가 없었다.

    아래 시험은 그 두 줄을 각각 지킨다.
    """

    def test_the_duration_is_not_zero(
        self, db_session, principal, site, scan_result, scan_context
    ):
        """저장된 실행에서 소요 시간을 실제로 뽑을 수 있어야 한다."""
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        run = db_session.get(ScanRun, saved.scan_run_id)
        assert run.started_at is not None
        assert run.finished_at is not None
        # 이것이 결함의 정체다 — 두 값이 같으면 소요가 0 이 된다.
        assert run.finished_at > run.started_at

    def test_the_start_time_is_the_one_we_were_given(
        self, db_session, principal, site, scan_result, scan_context
    ):
        """저장하는 쪽이 시작 시각을 **만들어 내지 않는다.**

        진단은 수집부터 시작하고 저장은 맨 마지막이다. 저장 시점에 시작 시각을 찍으면
        정작 시간을 쓴 구간이 전부 기록에서 빠진다.
        """
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=STARTED,
        )

        run = db_session.get(ScanRun, saved.scan_run_id)
        assert run.started_at == STARTED

    def test_the_start_time_cannot_be_omitted(self) -> None:
        """넘기지 않으면 **깨져야 한다.**

        결함이 조용했던 이유가 기본값이었다. 기본값을 되살리면 부르는 쪽이 다시 안
        넘기고, 그러면 운영에 또 0초가 쌓이는데 아무도 모른다. 서명에 못을 박는다.
        """
        import inspect

        from veo.seo.history import save_scan_run

        parameter = inspect.signature(save_scan_run).parameters["started_at"]
        assert parameter.default is inspect.Parameter.empty


class TestTheTimerCarriesAWallClock:
    """시작 시각의 출처는 `ScanTimings` 하나다 — 두 벌로 두면 갈라진다(0-D)."""

    def test_the_timer_knows_when_it_started(self) -> None:
        from datetime import UTC, datetime

        from veo.seo.timing import ScanTimings

        before = datetime.now(UTC)
        timings = ScanTimings()
        after = datetime.now(UTC)

        assert before <= timings.started_at <= after

    def test_the_start_time_is_timezone_aware(self) -> None:
        """순진한 시각을 넣으면 `DateTime(timezone=True)` 칸에서 비교가 어긋난다."""
        from veo.seo.timing import ScanTimings

        assert ScanTimings().started_at.tzinfo is not None


class TestWhatWeMeasuredGetsStored:
    """잰 값을 저장하지 않으면 잰 적이 없는 것과 같다.

    2026-08-06 운영 DB 전수 스윕에서 나왔다: `evidence.byte_size` 3,148행 전부 NULL.
    저장하는 코드가 `byte_size=None` 을 하드코딩하고 있었고, `EvidenceRecord.of()` 는
    해시를 내려고 이미 바이트를 손에 쥐고 있었다.
    """

    def test_evidence_keeps_the_size_of_what_it_judged(self) -> None:
        from veo.collect.contract import EvidenceRecord

        record = EvidenceRecord.of("robots_txt", url=None, payload=b"User-agent: *\n")

        assert record.byte_size == 14

    def test_the_size_is_the_real_byte_length_not_the_character_count(self) -> None:
        """한글은 글자 수와 바이트 수가 다르다. 저장할 것은 바이트다."""
        from veo.collect.contract import EvidenceRecord

        record = EvidenceRecord.of("http_response", url=None, payload="가나다")

        assert record.byte_size == 9
