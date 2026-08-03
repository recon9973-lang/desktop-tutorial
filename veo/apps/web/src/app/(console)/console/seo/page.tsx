import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { ScanReport, type ReportView } from '@/components/ScanReport/ScanReport';
import { listCompanies, type MeasuredSite } from '@/lib/companies';
import type { ConsoleScanResult, GeoCompanionRef } from '@/lib/console-scan';
import { readSavedGeoReadiness, type GeoCheck } from '@/lib/observations';
import {
  readBands,
  readCheckSeverities,
  readHistory,
  readSavedReport,
  type HistoryEntry,
} from '@/lib/scan-report';
import { APP_VERSION } from '@/lib/changelog';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { ReadinessReport } from '../geo/ReadinessReport';
import { PagesSection } from './PagesSection';
import { ScanForm } from './ScanForm';
import own from './seo.module.css';

export const metadata: Metadata = {
  title: '진단 — SEO·GEO 준비도',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * SEO 진단 결과.
 *
 * 화면을 열 때 **다시 재지 않는다.** 저장된 마지막 결과를 보여주고, 재측정은 사람이
 * 버튼을 눌렀을 때만 일어난다 — 같은 주소를 하루에 여러 번 다시 재는 것은 대상 사이트
 * 에도 우리 비용에도 부담이고, 변경을 확인하려는 것이 아니면 다시 잴 이유가 없다.
 */
export default async function SeoPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const identity = await requireConsoleIdentity();
  const params = await searchParams;

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <SeoContent
        siteId={single(params['site'])}
        runId={single(params['run'])}
        view={toView(single(params['view']))}
        pageUrl={single(params['page'])}
        axis={toAxis(single(params['axis']))}
      />
    </PermissionGate>
  );
}

function single(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

/** 결과 보기 방식. 모르는 값은 상세로 — 조용히 다른 화면을 열지 않는다. */
type ConsoleView = ReportView | 'pages';

function toView(value: string | null): ConsoleView {
  if (value === 'simple' || value === 'pages') return value;
  return 'detailed';
}

/** 결과의 축 — 한 크롤로 두 눈금을 쟀고(동반 채점), 화면은 번갈아 볼 뿐 합치지 않는다. */
type Axis = 'seo' | 'geo';

function toAxis(value: string | null): Axis {
  return value === 'geo' ? 'geo' : 'seo';
}

async function SeoContent({
  siteId,
  runId,
  view,
  pageUrl,
  axis,
}: {
  readonly siteId: string | null;
  readonly runId: string | null;
  readonly view: ConsoleView;
  readonly pageUrl: string | null;
  readonly axis: Axis;
}) {
  if (siteId === null) return <NewScan />;

  // GEO 탭이면 GEO 이력을 읽는다. 회차 선택은 SEO 실행 식별자로 하므로 SEO 이력도
  // 함께 필요하다 — 두 눈금은 같은 진단의 두 기록이고, 화면은 보는 눈금의 숫자를 쓴다.
  const [history, geoHistory, companies] = await Promise.all([
    readHistory(siteId),
    axis === 'geo' ? readHistory(siteId, 'GEO') : Promise.resolve(null),
    listCompanies(),
  ]);

  if (!history.ok) {
    return (
      <Shell>
        <ErrorState
          title="이력을 불러오지 못했습니다"
          description={history.message ?? '서버에 연결하지 못했습니다.'}
        />
      </Shell>
    );
  }

  const site = companies.ok
    ? companies.data.flatMap((company) => company.sites).find((one) => one.siteId === siteId)
    : undefined;
  const origin = site?.origin ?? '';
  // 이슈는 프로젝트에 달린다 — 작업 큐의 "이슈로 추적"이 이 프로젝트의 이슈 화면으로 간다.
  const issuesHrefBase =
    site === undefined
      ? '/console/issues?check='
      : `/console/issues?project=${encodeURIComponent(site.projectId)}&check=`;
  // 다른 거래처 레일 — 하락·방치가 다음 일감을 제안한다. 사이트마다 이력을 한 번씩
  // 읽으므로 수를 묶는다(최대 6곳 조회, 4곳 표시).
  const otherSites = companies.ok
    ? companies.data
        .flatMap((company) =>
          company.sites.map((one) => ({ ...one, company: company.name })),
        )
        .filter((one) => one.siteId !== siteId)
        .slice(0, 6)
    : [];

  const entries = history.data;
  // 화면이 그리는 숫자는 **보는 눈금의 것**이어야 한다. 회차 선택(run 파라미터)은 SEO
  // 실행 식별자로 하므로 그쪽은 계속 SEO 이력을 쓴다.
  const shownEntries =
    axis === 'geo' && geoHistory !== null && geoHistory.ok ? geoHistory.data : entries;
  const selected = runId === null ? entries[0] : entries.find((e) => e.scanRunId === runId);
  // 레일과 GEO 전환기가 둘 다 저장된 본문(geo 블록 포함)을 읽으므로 한 번만 가져온다.
  const saved =
    selected === undefined ? null : await readSavedReport(selected.scanRunId, origin);

  return (
    <Shell origin={origin}>
      <div className={own.toolbar}>
        <ScanForm siteId={siteId} />
        {selected === undefined ? null : (
          <AxisSwitch
            siteId={siteId}
            runId={selected.scanRunId}
            axis={axis}
            geo={saved?.geo ?? null}
            seoScore={saved?.score ?? null}
          />
        )}
        {selected === undefined || axis === 'geo' ? null : (
          <ViewSwitch siteId={siteId} runId={selected.scanRunId} view={view} />
        )}
      </div>

      {entries.length === 0 ? (
        <EmptyState description="아직 진단하지 않았습니다. 위의 진단 실행을 누르면 결과가 여기에 쌓입니다." />
      ) : (
        <div className={own.layout}>
          <div className={own.main}>
            <HistoryStrip
              entries={shownEntries}
              siteId={siteId}
              selectedId={selected?.scanRunId ?? null}
              view={view}
              axis={axis}
            />
            {selected === undefined ? null : axis === 'geo' ? (
              <SavedGeoReport geo={saved?.geo ?? null} savedMissing={saved === null} />
            ) : view === 'pages' ? (
              <PagesSection
                scanRunId={selected.scanRunId}
                siteId={siteId}
                pageUrl={pageUrl}
              />
            ) : saved === null ? (
              <ErrorState
                title="저장된 결과를 불러오지 못했습니다"
                description="이 진단은 결과 본문이 남아 있지 않습니다. 다시 측정하면 이후로는 그대로 다시 열 수 있습니다."
              />
            ) : (
              <SavedSeoReport saved={saved} view={view} issuesHrefBase={issuesHrefBase} />
            )}
          </div>
          {selected === undefined ? null : (
            <SummaryRail
              siteId={siteId}
              selected={selected}
              entries={shownEntries}
              saved={saved}
              axis={axis}
              otherSites={otherSites}
            />
          )}
        </div>
      )}
    </Shell>
  );
}

async function SavedSeoReport({
  saved,
  view,
  issuesHrefBase,
}: {
  readonly saved: ConsoleScanResult;
  readonly view: ReportView;
  readonly issuesHrefBase: string;
}) {
  const bands = await readBands(saved.specId, saved.specVersion);
  return <ScanReport result={saved} bands={bands} view={view} issuesHrefBase={issuesHrefBase} />;
}

/**
 * GEO 축 — 같은 크롤로 함께 저장된 동반 실행을 그대로 다시 연다.
 *
 * 동반 저장 이전의 실행에는 geo 블록이 없다. 그 사실을 감추지 않는다 — "잰 적 없음"
 * 과 "재려다 실패"(failureNote)는 다른 문장으로 나온다.
 */
async function SavedGeoReport({
  geo,
  savedMissing,
}: {
  readonly geo: GeoCompanionRef | null;
  readonly savedMissing: boolean;
}) {
  if (savedMissing) {
    return (
      <ErrorState
        title="저장된 결과를 불러오지 못했습니다"
        description="이 진단은 결과 본문이 남아 있지 않습니다. 다시 측정하면 이후로는 그대로 다시 열 수 있습니다."
      />
    );
  }
  if (geo === null || geo.scanRunId === null) {
    return (
      <EmptyState
        description={
          geo?.failureNote ??
          '이 실행에는 GEO 결과가 저장되어 있지 않습니다 — 동반 저장이 생기기 전의 실행입니다. 다시 측정하면 SEO·GEO 가 함께 계산됩니다.'
        }
      />
    );
  }

  const outcome = await readSavedGeoReadiness(geo.scanRunId);
  if (!outcome.ok) {
    return (
      <ErrorState
        title="GEO 결과를 불러오지 못했습니다"
        description={outcome.message ?? '서버에 연결하지 못했습니다.'}
      />
    );
  }
  // 심각도는 GEO 응답에 없다(엔진 경계) — 발행 명세에서 읽어 화면에서 잇는다.
  const severities = await readCheckSeverities(
    outcome.data.readiness.spec_id,
    outcome.data.readiness.spec_version,
  );
  return <ReadinessReport report={outcome.data} severities={severities} />;
}

function HistoryStrip({
  entries,
  siteId,
  selectedId,
  view,
  axis,
}: {
  readonly entries: readonly HistoryEntry[];
  readonly siteId: string;
  readonly selectedId: string | null;
  readonly view: ConsoleView;
  readonly axis: Axis;
}) {
  return (
    <section className={own.history} aria-labelledby="scan-history">
      <h2 id="scan-history" className={own.historyTitle}>
        측정 이력
      </h2>
      <ul className={own.historyList}>
        {entries.map((entry) => {
          const current = entry.scanRunId === selectedId;
          return (
            <li key={entry.scanRunId}>
              <Link
                href={`/console/seo?site=${siteId}&run=${entry.scanRunId}&view=${view}&axis=${axis}`}
                className={current ? `${own.historyItem} ${own.historyCurrent}` : own.historyItem}
                aria-current={current ? 'true' : undefined}
              >
                <span className={own.historyScore}>
                  {entry.score === null ? '—' : entry.score.toFixed(1)}
                </span>
                <span className={own.historyWhen}>{formatWhen(entry.startedAt)}</span>
                <span className={own.historyWho}>
                  {entry.requestedByName ?? '실행자 기록 없음'} · {entry.urlsCollected}페이지
                </span>
              </Link>
              {/*
                점을 나란히 놓으면 사람은 눈으로 잇는다. 조건이 다른 두 점을 이은 선은
                사이트가 변했다는 뜻으로 읽히는데, 변한 것은 재는 방법이다.
              */}
              {!entry.comparableWithLatest ? (
                <p className={own.historyIncomparable}>
                  {entry.incomparableReasonKo ??
                    '최근 실행과 같은 조건에서 쟀는지 확인할 수 없습니다.'}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/**
 * SEO|GEO 전환기 — 한 크롤, 두 눈금. 점수는 합치지 않고 번갈아 볼 뿐이다.
 *
 * GEO 점수가 있으면 숫자를 칩에 함께 보여 "다른 축에도 결과가 있다"는 사실이
 * 클릭 전에 보인다. 없으면 숫자 없이 축 이름만 — 없는 점수를 만들지 않는다.
 */
function AxisSwitch({
  siteId,
  runId,
  axis,
  geo,
  seoScore,
}: {
  readonly siteId: string;
  readonly runId: string;
  readonly axis: Axis;
  readonly geo: GeoCompanionRef | null;
  /** 이 회차의 SEO 점수. 없으면(측정 불가) 숫자를 붙이지 않는다. */
  readonly seoScore: number | null;
}) {
  const base = `/console/seo?site=${siteId}&run=${runId}`;
  return (
    // 두 점수를 **함께** 보여준다(확정 시안 v2.2 §9). 한쪽에만 숫자가 붙어 있으면
    // 어느 쪽이 지금 보는 값인지 헷갈리고, 실제로 그렇게 보였다(사용자 지적).
    // 합산하지 않는다 — 눈금이 다른 두 점수다.
    <nav className={own.axes} aria-label="결과의 축">
      <Link
        href={`${base}&axis=seo`}
        className={axis === 'seo' ? `${own.axisTab} ${own.axisOn}` : own.axisTab}
        aria-current={axis === 'seo' ? 'page' : undefined}
      >
        SEO
        {seoScore === null ? null : (
          <span className={own.axisScore}>{seoScore.toFixed(1)}</span>
        )}
      </Link>
      <Link
        href={`${base}&axis=geo`}
        className={axis === 'geo' ? `${own.axisTab} ${own.axisOn}` : own.axisTab}
        aria-current={axis === 'geo' ? 'page' : undefined}
      >
        GEO
        {geo?.score !== null && geo?.score !== undefined ? (
          <span className={own.axisScore}>{geo.score.toFixed(1)}</span>
        ) : null}
      </Link>
    </nav>
  );
}

function ViewSwitch({
  siteId,
  runId,
  view,
}: {
  readonly siteId: string;
  readonly runId: string;
  readonly view: ConsoleView;
}) {
  const base = `/console/seo?site=${siteId}&run=${runId}`;
  return (
    <nav className={own.views} aria-label="결과 보기 방식">
      <Link href={`${base}&view=simple`} aria-current={view === 'simple' ? 'page' : undefined}>
        간소화 · 업체 전달용
      </Link>
      <Link href={`${base}&view=detailed`} aria-current={view === 'detailed' ? 'page' : undefined}>
        상세 · 직원용
      </Link>
      <Link href={`${base}&view=pages`} aria-current={view === 'pages' ? 'page' : undefined}>
        페이지별 · 어디를 고칠까
      </Link>
    </nav>
  );
}

/**
 * 우측 요약 레일 (재설계 ②) — 담당자가 본문을 읽는 동안 잃지 않아야 할 맥락.
 *
 * 레일이 지키는 것:
 * - 숫자는 전부 서버 값 그대로. 여기서 계산하는 것은 두 실측 점수의 뺄셈 하나뿐이고,
 *   그마저 같은 명세 버전끼리만 한다 — 판이 다르면 차이는 하락이 아니다.
 * - SEO·GEO 는 나란히 놓되 합치지 않는다.
 */
/**
 * 판정 분포와 점검 진행률 — 확정 시안 v2.2 의 레일 카드 둘.
 *
 * 점수 하나로는 "얼마나 남았나" 가 안 보인다. 70.9 점이 실패 2개 때문인지 스무 개
 * 때문인지가 다르고, 담당자가 알고 싶은 것은 후자다.
 *
 * **측정 불가는 분모 밖이다.** 연동이 없어 재지 못한 항목을 실패로 세면 우리가 못 잰
 * 것을 사이트 탓으로 돌리게 된다 — 그것은 다른 화면들과 같은 규칙이고 여기서도 지킨다.
 * 대신 몇 개가 분모 밖인지는 적는다: 조용히 빼면 개수가 맞지 않는 것으로 읽힌다.
 */
function verdictSpread(saved: ConsoleScanResult | null) {
  if (saved === null) return null;
  const scoredOutcomes = saved.outcomes.filter((item) => item.availability === 'SELF_SERVICE');
  if (scoredOutcomes.length === 0) return null;

  const tally = { FAIL: 0, WARNING: 0, PASS: 0, UNKNOWN: 0 } as Record<string, number>;
  for (const item of scoredOutcomes) tally[item.status] = (tally[item.status] ?? 0) + 1;

  const total = scoredOutcomes.length;
  const unknown = tally.UNKNOWN ?? 0;
  const scored = total - unknown;
  const pass = tally.PASS ?? 0;
  const todo = (tally.FAIL ?? 0) + (tally.WARNING ?? 0);
  const segments = [
    { id: 'FAIL', label: '실패', count: tally.FAIL ?? 0, className: own.segFail ?? '' },
    { id: 'WARNING', label: '주의', count: tally.WARNING ?? 0, className: own.segWarn ?? '' },
    { id: 'PASS', label: '통과', count: pass, className: own.segPass ?? '' },
    { id: 'UNKNOWN', label: '측정 불가', count: unknown, className: own.segUnknown ?? '' },
  ]
    .filter((segment) => segment.count > 0)
    .map((segment) => ({ ...segment, percent: (segment.count / total) * 100 }));

  return {
    segments,
    scored,
    pass,
    todo,
    unknown,
    // 채점한 것 중 통과 비율. 잰 적 없는 항목은 여기에도 들어오지 않는다.
    passPercent: scored === 0 ? 0 : (pass / scored) * 100,
    aria: segments.map((segment) => `${segment.label} ${segment.count}`).join(', '),
  };
}

/**
 * 최근 점수 추이 — 확정 시안 v2.2 의 스파크라인.
 *
 * **같은 명세끼리만 잇는다.** 눈금이 바뀐 회차를 이으면 사이트는 그대로인데 선이 꺾이고,
 * 그 꺾임은 우리가 채점 기준을 바꾼 흔적이지 사이트에서 일어난 일이 아니다. 다른 화면의
 * "직전 대비" 가 지키는 규칙과 같다.
 *
 * 점이 둘 미만이면 그리지 않는다 — 한 점을 잇는 선은 추이가 아니다.
 */
function sparkline(entries: readonly HistoryEntry[], selected: HistoryEntry) {
  const comparable = entries
    .filter((entry) => entry.specVersion === selected.specVersion && entry.score !== null)
    .slice(0, 5)
    // 이력은 최신이 앞이다. 왼쪽이 과거가 되도록 뒤집는다.
    .reverse();
  if (comparable.length < 2) return null;

  const scores = comparable.map((entry) => entry.score ?? 0);
  const low = Math.min(...scores);
  const high = Math.max(...scores);
  // 전부 같은 점수면 폭이 0이라 나눌 수 없다. 그때는 가운데 수평선이 정직하다.
  const span = high - low === 0 ? 1 : high - low;
  const width = 280;
  const step = width / (scores.length - 1);
  const points = scores.map((score, index) => ({
    x: Math.round(index * step),
    y: Math.round(30 - ((score - low) / span) * 24),
  }));
  const last = points[points.length - 1];

  return {
    width,
    points,
    line: points.map((point) => `${point.x},${point.y}`).join(' '),
    lastX: last?.x ?? 0,
    lastY: last?.y ?? 0,
  };
}

/**
 * GEO 판정 분포 — SEO 와 같은 규칙을 GEO 자료 모양에 맞춘 것.
 *
 * GEO 판정에는 `availability`(연동이 필요한 항목인지)가 없다. 그 구분은 SEO 쪽 개념이고,
 * 없는 필드를 있는 척 읽으면 전부 배점 안으로 들어온다. 그래서 걸러내지 않고 전부 센다 —
 * 대신 측정 불가는 여기서도 분모 밖이다.
 */
function geoVerdictSpread(checks: readonly GeoCheck[] | null) {
  if (checks === null || checks.length === 0) return null;

  const tally: Record<string, number> = {};
  for (const check of checks) tally[check.status] = (tally[check.status] ?? 0) + 1;

  const total = checks.length;
  const unknown = tally.UNKNOWN ?? 0;
  const scored = total - unknown;
  const pass = tally.PASS ?? 0;
  const todo = (tally.FAIL ?? 0) + (tally.WARNING ?? 0);
  const segments = [
    { id: 'FAIL', label: '실패', count: tally.FAIL ?? 0, className: own.segFail ?? '' },
    { id: 'WARNING', label: '주의', count: tally.WARNING ?? 0, className: own.segWarn ?? '' },
    { id: 'PASS', label: '통과', count: pass, className: own.segPass ?? '' },
    { id: 'UNKNOWN', label: '측정 불가', count: unknown, className: own.segUnknown ?? '' },
  ]
    .filter((segment) => segment.count > 0)
    .map((segment) => ({ ...segment, percent: (segment.count / total) * 100 }));

  return {
    segments,
    scored,
    pass,
    todo,
    unknown,
    passPercent: scored === 0 ? 0 : (pass / scored) * 100,
    aria: segments.map((segment) => `${segment.label} ${segment.count}`).join(', '),
  };
}

async function SummaryRail({
  siteId,
  selected,
  entries,
  saved,
  axis,
  otherSites,
}: {
  readonly siteId: string;
  readonly selected: HistoryEntry;
  readonly entries: readonly HistoryEntry[];
  readonly saved: ConsoleScanResult | null;
  readonly axis: Axis;
  readonly otherSites: readonly (MeasuredSite & { readonly company: string })[];
}) {
  // 밴드는 **한국어 라벨**로 보여준다. 식별자(at_risk)를 그대로 그리면 화면에 내부
  // 이름이 새어 나오고, 읽는 사람에게는 아무 뜻도 없는 영어가 된다.
  const bands = saved === null ? [] : await readBands(saved.specId, saved.specVersion);
  const clients = await otherClientRows(otherSites);
  const geo = saved?.geo ?? null;
  // GEO 축에서는 **GEO 자료**를 읽는다. 이 줄이 없던 동안 레일은 GEO 게이지 아래에
  // SEO 의 분포와 영역 막대를 그렸다 — 축을 바꿨는데 아래 숫자는 그대로여서, 보는
  // 사람은 그것이 GEO 의 숫자라고 읽는다. 조용히 틀리는 종류의 화면이다.
  const geoReport =
    axis === 'geo' && geo !== null && geo.scanRunId !== null
      ? await readSavedGeoReadiness(geo.scanRunId)
      : null;
  const geoData = geoReport !== null && geoReport.ok ? geoReport.data : null;

  // 보는 눈금의 **그 회차**를 짚는다. GEO 실행은 SEO 와 다른 식별자를 갖고, 둘을 잇는
  // 것이 동반 실행 참조(geo.scanRunId)다. 못 찾으면 null 이고, 그때는 증감·추이를
  // 그리지 않는다 — 다른 눈금의 숫자를 대신 그리느니 없는 편이 낫다.
  const shown =
    axis === 'geo'
      ? (entries.find((entry) => entry.scanRunId === geo?.scanRunId) ?? null)
      : selected;

  const verdicts =
    axis === 'geo' ? geoVerdictSpread(geoData?.checks ?? null) : verdictSpread(saved);
  // 게이지는 지금 보고 있는 눈금을 그린다 — 전환기가 GEO 면 GEO 점수다.
  const gaugeScore = axis === 'geo' ? (geo?.score ?? null) : selected.score;
  const bandId = axis === 'geo' ? (geo?.bandId ?? null) : (saved?.bandId ?? null);
  const bandLabel = bands.find((band) => band.id === bandId)?.label ?? null;
  const coverage = saved?.coverage ?? 1;
  const spark = shown === null ? null : sparkline(entries, shown);
  const miniBars = (
    axis === 'geo'
      ? (geoData?.readiness.categories ?? []).map((category) => ({
          categoryId: category.category_id,
          name: category.name_ko,
          status: category.status,
          score: category.score,
        }))
      : (saved?.categories ?? []).map((category) => ({
          categoryId: category.categoryId,
          name: category.name,
          status: category.status,
          score: category.score,
        }))
  )
    // 채점하지 못한 영역은 0% 막대로 그리면 "0점" 으로 읽힌다. 그것은 거짓이다.
    .filter((category) => category.status === 'SCORED' && category.score !== null)
    .map((category) => ({
      categoryId: category.categoryId,
      name: category.name,
      score: category.score ?? 0,
      low: (category.score ?? 0) < 80,
    }));
  const index =
    shown === null ? -1 : entries.findIndex((entry) => entry.scanRunId === shown.scanRunId);
  const previous = index >= 0 ? entries[index + 1] : undefined;
  const delta =
    shown !== null &&
    previous !== undefined &&
    previous.score !== null &&
    shown.score !== null &&
    previous.specVersion === shown.specVersion
      ? shown.score - previous.score
      : null;

  return (
    <aside className={own.rail} aria-label="진단 요약">
      {gaugeScore === null ? null : (
        <section className={own.railBlock}>
          <h2 className={own.railTitle}>이번 측정 — {axis === 'geo' ? 'GEO' : 'SEO'}</h2>
          {/* 확정 시안 v2.2 — 원형 게이지. 숫자 하나보다 "어디까지 찼는가" 가 먼저 읽힌다.
              conic-gradient 로 그린다: 이미지도 라이브러리도 없이 토큰 색 그대로 쓴다. */}
          <div className={own.scoreRow}>
            <div
              className={own.gauge}
              style={{ ['--veo-gauge-deg' as string]: `${(gaugeScore / 100) * 360}deg` }}
              role="img"
              aria-label={`${gaugeScore.toFixed(1)}점`}
            >
              <div className={own.gaugeIn}>
                <b>{gaugeScore.toFixed(1)}</b>
                <span>{bandLabel ?? '점'}</span>
              </div>
            </div>
            <div className={own.scoreSide}>
              {delta === null ? (
                <p>비교할 직전 실행 없음</p>
              ) : (
                <p>
                  직전 대비{' '}
                  <b className={delta < 0 ? own.deltaDown : own.deltaUp}>
                    {delta > 0 ? '▲' : delta < 0 ? '▼' : ''}
                    {Math.abs(delta).toFixed(1)}
                  </b>
                </p>
              )}
              <p>측정 범위 {Math.round(coverage * 100)}%</p>
              <p>명세 {shown?.specVersion ?? '—'}</p>
            </div>
          </div>
          {spark === null ? null : (
            <>
              <svg
                className={own.spark}
                viewBox={`0 0 ${spark.width} 36`}
                preserveAspectRatio="none"
                role="img"
                aria-label={`최근 ${spark.points.length}회 점수 추이`}
              >
                <polyline points={spark.line} fill="none" strokeWidth="2" />
                <circle cx={spark.lastX} cy={spark.lastY} r="3.5" />
              </svg>
              {/* 같은 명세끼리만 잇는다 — 눈금이 바뀐 점을 이으면 없는 변화가 그려진다. */}
              <p className={own.sparkCap}>
                최근 {spark.points.length}회 · 같은 명세({shown?.specVersion})끼리만 잇습니다
              </p>
            </>
          )}
          {/* 선만 보면 "언제 얼마였나" 를 읽을 수 없다. 점의 값을 날짜와 함께 적는다. */}
          <ol className={own.runLog}>
            {entries.slice(0, 5).map((entry) => (
              <li
                key={entry.scanRunId}
                className={entry.scanRunId === shown?.scanRunId ? own.runLogOn : own.runLogRow}
              >
                <span className={own.runLogWhen}>{formatWhen(entry.startedAt)}</span>
                <span className={own.runLogScore}>
                  {entry.score === null ? '측정 불가' : entry.score.toFixed(1)}
                </span>
                {/* 명세가 다르면 위 선에 잇지 않았다는 것을 여기서도 말한다. */}
                {entry.specVersion === shown?.specVersion ? null : (
                  <span className={own.runLogSpec}>명세 {entry.specVersion}</span>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}

      {miniBars.length === 0 ? null : (
        <section className={own.railBlock}>
          <h2 className={own.railTitle}>영역별 — {axis === 'geo' ? 'GEO' : 'SEO'}</h2>
          <ul className={own.miniBars}>
            {miniBars.map((bar) => (
              <li key={bar.categoryId} className={own.miniBar}>
                {/* 확정 시안 v2.2 §12 — 레일이 목차가 된다. 긴 페이지에서 영역 이름을
                    누르면 그 영역 카드로 간다. 새 화면을 여는 것이 아니라 같은 문서 안의
                    자리이므로 `a href="#"` 이면 충분하다 — 자바스크립트가 필요 없고
                    브라우저의 뒤로 가기도 그대로 동작한다. */}
                <a className={own.miniBarName} href={`#check-${bar.categoryId}`}>
                  {bar.name}
                </a>
                <span className={own.miniBarTrack}>
                  <span
                    className={bar.low ? own.miniBarFillLow : own.miniBarFill}
                    style={{ width: `${bar.score}%` }}
                  />
                </span>
                <b className={own.miniBarVal}>{Math.round(bar.score)}</b>
              </li>
            ))}
          </ul>
          {/* 병목만 다른 색으로. 전부 같은 색이면 어디가 문제인지 다시 읽어야 한다. */}
          <p className={own.railNote}>낮은 영역은 다른 색입니다. 가중치는 영역마다 다릅니다.</p>
        </section>
      )}

      <section className={own.railBlock}>
        <h2 className={own.railTitle}>두 눈금</h2>
        <dl className={own.railScores}>
          <div className={axis === 'seo' ? own.railScoreOn : own.railScore}>
            <dt>SEO 준비도</dt>
            <dd>{selected.score === null ? '측정 불가' : selected.score.toFixed(1)}</dd>
          </div>
          <div className={axis === 'geo' ? own.railScoreOn : own.railScore}>
            <dt>GEO 준비도</dt>
            <dd>
              {geo === null || geo.scanRunId === null
                ? '결과 없음'
                : geo.score === null
                  ? '측정 불가'
                  : geo.score.toFixed(1)}
            </dd>
          </div>
        </dl>
        <p className={own.railNote}>같은 크롤로 잰 두 눈금입니다. 합산하지 않습니다.</p>
      </section>

      <section className={own.railBlock}>
        <h2 className={own.railTitle}>직전 대비</h2>
        {previous === undefined ? (
          <p className={own.railNote}>비교할 직전 실행이 없습니다.</p>
        ) : delta === null ? (
          <p className={own.railNote}>
            직전 실행과 명세 버전이 다르거나 점수가 없어 비교하지 않습니다 — 판이 다르면
            차이는 하락이 아닙니다.
          </p>
        ) : (
          <p className={own.railDelta}>
            {delta > 0 ? '▲' : delta < 0 ? '▼' : '—'} {Math.abs(delta).toFixed(1)}점{' '}
            <span className={own.railNote}>
              ({previous.score?.toFixed(1)} → {selected.score?.toFixed(1)}, 명세{' '}
              {selected.specVersion})
            </span>
          </p>
        )}
      </section>

      {verdicts === null ? null : (
        <section className={own.railBlock}>
          {/* 어느 눈금의 분포인지 제목이 말한다 — 전환기로 축을 바꾸면 숫자가 통째로
              바뀌는데, 제목이 같으면 바뀐 줄 모른다. */}
          <h2 className={own.railTitle}>판정 분포 — {axis === 'geo' ? 'GEO' : 'SEO'}</h2>
          {/* 확정 시안 v2.2 — 한 줄 막대와 범례. 색만으로 말하지 않게 숫자를 함께 둔다. */}
          <div className={own.verdictBar} role="img" aria-label={verdicts.aria}>
            {verdicts.segments.map((segment) => (
              <i
                key={segment.id}
                className={segment.className}
                style={{ width: `${segment.percent}%` }}
              />
            ))}
          </div>
          <p className={own.verdictLegend}>
            {verdicts.segments.map((segment) => (
              <span key={segment.id}>
                <i className={segment.className} aria-hidden="true" />
                {segment.label} <b>{segment.count}</b>
              </span>
            ))}
          </p>
          {/* 측정 불가는 분모 밖이다 — 우리 원칙 그대로, 진행률에 섞지 않는다. */}
          <div className={own.progressTrack}>
            <i style={{ width: `${verdicts.passPercent}%` }} />
          </div>
          <p className={own.progressCap}>
            채점 {verdicts.scored}개 중 <b>통과 {verdicts.pass}</b> · 남은 조치{' '}
            {verdicts.todo}
            {verdicts.unknown === 0 ? null : ` · 측정 불가 ${verdicts.unknown}은 분모 밖`}
          </p>
        </section>
      )}

      <section className={own.railBlock}>
        <h2 className={own.railTitle}>이번 측정</h2>
        <ul className={own.railFacts}>
          <li>{formatWhen(selected.startedAt)}</li>
          <li>{selected.urlsCollected}페이지 수집</li>
          <li>{selected.requestedByName ?? '실행자 기록 없음'}</li>
          {/* "명세" 만 적으면 하단 푸터의 앱 버전(v0.3.x)과 같은 축으로 읽힌다(사용자 혼동
              보고). 이것은 점수 계산 규칙의 판이고, 앱이 업데이트돼도 규칙이 그대로면
              바뀌지 않는다 — 그 구분을 화면이 직접 말하게 한다. */}
          <li>
            채점 규칙 {selected.specVersion}
            <span className={own.railFactNote}>
              점수 계산 명세의 버전 — 하단의 앱 버전(v{APP_VERSION})과는 다른 축입니다
            </span>
          </li>
        </ul>
      </section>

      <section className={own.railBlock}>
        <h2 className={own.railTitle}>바로가기</h2>
        <ul className={own.railLinks}>
          <li>
            <Link href={`/console/seo?site=${siteId}&run=${selected.scanRunId}&view=pages`}>
              페이지별로 보기
            </Link>
          </li>
          <li>
            <Link href="/console/scoring-versions">채점 기준·알고리즘 설계도</Link>
          </li>
          <li>
            <Link href="/console/geo">GEO AI 관측(실제 답변 확인)</Link>
          </li>
        </ul>
      </section>

      {clients.length === 0 ? null : (
        <section className={own.railBlock}>
          <h2 className={own.railTitle}>다른 거래처</h2>
          <ul className={own.railClients}>
            {clients.map((client) => (
              <li key={client.siteId}>
                <Link href={`/console/seo?site=${client.siteId}`} className={own.railClient}>
                  <span className={own.railClientName}>{client.label}</span>
                  {client.badge === null ? null : (
                    <span
                      className={
                        client.badge.kind === 'drop'
                          ? own.badgeDown
                          : client.badge.kind === 'rise'
                            ? own.badgeUp
                            : own.badgeStale
                      }
                    >
                      {client.badge.text}
                    </span>
                  )}
                  <span className={own.railClientScore}>
                    {client.score === null ? '—' : client.score.toFixed(1)}
                  </span>
                </Link>
              </li>
            ))}
            <li>
              <Link href="/console/customers" className={own.railClientsAll}>
                전체 거래처 보기 →
              </Link>
            </li>
          </ul>
        </section>
      )}
    </aside>
  );
}

interface ClientRow {
  readonly siteId: string;
  readonly label: string;
  readonly score: number | null;
  readonly badge:
    | { readonly kind: 'drop' | 'rise'; readonly text: string }
    | { readonly kind: 'stale'; readonly text: string }
    | null;
}

/**
 * 다른 거래처의 최근 상태 — 하락·방치가 먼저다 (다음 일감 제안, 시안 v2.2).
 *
 * 숫자 규칙은 레일의 "직전 대비"와 같다: 같은 명세 버전끼리만 뺄셈, 아니면 배지 없음.
 * "N일 경과"는 마지막 측정 이후의 경과일 — 값이 없는 사이트는 "—"로 남는다.
 */
async function otherClientRows(
  sites: readonly (MeasuredSite & { readonly company: string })[],
): Promise<readonly ClientRow[]> {
  const histories = await Promise.all(
    sites.map(async (site) => ({ site, history: await readHistory(site.siteId) })),
  );

  const now = Date.now();
  const rows = histories.map(({ site, history }): ClientRow => {
    const entries = history.ok ? history.data : [];
    const latest = entries[0];
    const previous = entries[1];
    const label = site.displayName !== '' ? site.displayName : site.origin;

    if (latest === undefined) {
      return { siteId: site.siteId, label, score: null, badge: null };
    }

    let badge: ClientRow['badge'] = null;
    if (
      previous !== undefined &&
      previous.score !== null &&
      latest.score !== null &&
      previous.specVersion === latest.specVersion
    ) {
      const delta = latest.score - previous.score;
      if (delta <= -0.1) badge = { kind: 'drop', text: `▼${Math.abs(delta).toFixed(1)}` };
      else if (delta >= 0.1) badge = { kind: 'rise', text: `▲${delta.toFixed(1)}` };
    }
    if (badge === null) {
      const measuredAt = new Date(latest.startedAt).getTime();
      if (Number.isFinite(measuredAt)) {
        const days = Math.floor((now - measuredAt) / 86_400_000);
        if (days >= 14) badge = { kind: 'stale', text: `${days}일 경과` };
      }
    }

    return { siteId: site.siteId, label, score: latest.score, badge };
  });

  // 하락이 먼저, 그다음 오래 방치된 곳 — 담당자의 다음 일감 순서다.
  const rank = (row: ClientRow): number =>
    row.badge?.kind === 'drop' ? 0 : row.badge?.kind === 'stale' ? 1 : 2;
  return [...rows].sort((a, b) => rank(a) - rank(b)).slice(0, 4);
}

/**
 * 첫 화면 — 주소 한 칸.
 *
 * 등록을 먼저 시키지 않는다. 넣으면 잰다. 이미 잰 주소는 아래 목록에서 바로 열 수 있고,
 * 그때는 다시 재지 않는다.
 */
async function NewScan() {
  const companies = await listCompanies();
  const measured = companies.ok
    ? companies.data.flatMap((company) =>
        company.sites.map((site) => ({ company: company.name, ...site })),
      )
    : [];

  return (
    <Shell>
      <Card title="주소를 넣으면 바로 진단합니다" headingLevel={2}>
        <ScanForm />
      </Card>

      {!companies.ok ? (
        <ErrorState
          title="지난 진단 목록을 불러오지 못했습니다"
          description={companies.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : measured.length === 0 ? null : (
        <section className={own.previous} aria-labelledby="measured-sites">
          <h2 id="measured-sites" className={own.historyTitle}>
            이미 진단한 주소
          </h2>
          <ul className={own.siteList}>
            {measured.map((site) => (
              <li key={site.siteId}>
                <Link href={`/console/seo?site=${site.siteId}`}>{site.origin}</Link>
                {site.company === site.origin.replace(/^https?:\/\/(www\.)?/, '') ? null : (
                  <span className={own.siteCompany}> · {site.company}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </Shell>
  );
}

function Shell({ origin, children }: { readonly origin?: string; readonly children: ReactNode }) {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        {/* 한 번 재면 두 눈금이 나온다. 제목이 "SEO" 라고만 말하면 GEO 탭을 보는
            동안에도 SEO 화면에 있는 것으로 읽힌다(사용자 지적). */}
        <h1 className={styles.title}>진단</h1>
        <p className={styles.lede}>
          {origin === undefined || origin === '' ? '' : `${origin} · `}
          검색엔진과 AI 답변 엔진이 사이트를 발견·해석·인용할 수 있는 상태인지 항목별로
          확인합니다. 한 번 측정하면 <strong>SEO·GEO 두 눈금</strong>이 함께 나오고,
          위의 전환기로 오갑니다. 순위 예측이 아니라 준비도이며, 눈금이 다르므로 두 점수를
          합치지 않습니다.
        </p>
      </div>
      {children}
    </div>
  );
}

/** 표시 시각은 서버 시각이 아니라 한국 시각으로 고정한다. */
function formatWhen(iso: string): string {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Seoul',
  }).format(when);
}
