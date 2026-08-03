import 'server-only';

import { listCompanies, type MeasuredSite } from '@/lib/companies';
import { readHistory, type HistoryEntry } from '@/lib/scan-report';

/**
 * 전 거래처의 지금 상태 — 한 화면에서.
 *
 * 대시보드는 "전체 현황 요약" 이라고 적혀 있었지만 실제로는 **업체 이름과 주소만**
 * 보여줬다. 담당자가 아침에 열어서 "오늘 어디부터 볼까" 를 정할 수 없는 화면이었다.
 *
 * 여기서 모으는 것은 **이미 다른 탭이 갖고 있는 값들**이다. 새로 재지 않는다 — 대시보드가
 * 자기만의 측정을 하면 진단 화면의 숫자와 어긋나는 날이 오고, 그때 어느 쪽을 믿어야 할지
 * 알 수 없다(0-D).
 *
 * **못 읽은 사이트를 0으로 만들지 않는다.** 점수가 `null` 인 것은 "0점" 이 아니라
 * "아직 재지 않았거나 못 읽었다" 이고, 그 둘을 같은 칸에 두면 평균이 조용히 내려간다.
 */

export interface SiteStatus {
  readonly siteId: string;
  readonly label: string;
  readonly origin: string;
  readonly company: string;
  /** 최근 SEO 점수. 잰 적 없거나 못 읽었으면 `null` — 0이 아니다. */
  readonly score: number | null;
  /** 직전 대비 증감. 같은 명세끼리만 뺀다. 비교할 수 없으면 `null`. */
  readonly delta: number | null;
  /** 마지막 측정 이후 지난 날 수. 잰 적 없으면 `null`. */
  readonly daysSince: number | null;
  readonly measuredAt: string | null;
}

export interface DashboardData {
  readonly sites: readonly SiteStatus[];
  readonly companyCount: number;
  /** 점수를 아는 사이트 수. 평균의 분모다. */
  readonly measuredCount: number;
  /** 한 번도 재지 않은 사이트 수. 0점이 아니라 **모름**이다. */
  readonly unmeasuredCount: number;
  readonly averageScore: number | null;
  /** 14일 넘게 방치된 사이트. 다음 일감의 후보다. */
  readonly staleCount: number;
  readonly droppedCount: number;
  readonly improvedCount: number;
}

const STALE_DAYS = 14;
/** 이 미만의 변화는 반올림·표본 차이일 수 있다. 회귀 경보와 같은 문턱을 쓴다. */
const MEANINGFUL_DELTA = 0.1;

function statusOf(
  site: MeasuredSite & { readonly company: string },
  entries: readonly HistoryEntry[],
  now: number,
): SiteStatus {
  const label = site.displayName !== '' ? site.displayName : site.origin;
  const latest = entries[0];
  const previous = entries[1];

  if (latest === undefined) {
    return {
      siteId: site.siteId,
      label,
      origin: site.origin,
      company: site.company,
      score: null,
      delta: null,
      daysSince: null,
      measuredAt: null,
    };
  }

  // 명세가 다르면 빼지 않는다 — 사이트는 그대로인데 채점 규칙이 바뀐 차이다.
  const comparable =
    previous !== undefined &&
    previous.score !== null &&
    latest.score !== null &&
    previous.specVersion === latest.specVersion;
  const delta = comparable ? (latest.score ?? 0) - (previous?.score ?? 0) : null;

  const measuredAt = new Date(latest.startedAt).getTime();
  const daysSince = Number.isFinite(measuredAt)
    ? Math.floor((now - measuredAt) / 86_400_000)
    : null;

  return {
    siteId: site.siteId,
    label,
    origin: site.origin,
    company: site.company,
    score: latest.score,
    delta,
    daysSince,
    measuredAt: latest.startedAt,
  };
}

export async function readDashboard(now: number = Date.now()): Promise<DashboardData | null> {
  const companies = await listCompanies();
  if (!companies.ok) return null;

  const sites = companies.data.flatMap((company) =>
    company.sites.map((site) => ({ ...site, company: company.name })),
  );

  // 사이트마다 이력을 한 번씩 읽는다. 거래처가 많아지면 이 자리가 먼저 느려지므로,
  // 그때는 서버에 요약 엔드포인트를 두는 것이 맞다 — 화면에서 더 잘게 나누는 것이 아니라.
  const histories = await Promise.all(
    sites.map(async (site) => ({ site, history: await readHistory(site.siteId) })),
  );

  const rows = histories.map(({ site, history }) =>
    statusOf(site, history.ok ? history.data : [], now),
  );

  const measured = rows.filter((row) => row.score !== null);
  const total = measured.reduce((sum, row) => sum + (row.score ?? 0), 0);

  return {
    // 낮은 점수가 위로 — 대시보드를 여는 이유는 "어디부터 볼까" 이다.
    // 점수를 모르는 사이트는 맨 아래가 아니라 **맨 위**에 온다: 재지 않은 것이야말로
    // 가장 먼저 처리할 일이다.
    sites: [...rows].sort((a, b) => {
      if (a.score === null && b.score === null) return a.label.localeCompare(b.label);
      if (a.score === null) return -1;
      if (b.score === null) return 1;
      return a.score - b.score;
    }),
    companyCount: companies.data.length,
    measuredCount: measured.length,
    unmeasuredCount: rows.length - measured.length,
    averageScore: measured.length === 0 ? null : total / measured.length,
    staleCount: rows.filter(
      (row) => row.daysSince !== null && row.daysSince >= STALE_DAYS,
    ).length,
    droppedCount: rows.filter((row) => row.delta !== null && row.delta <= -MEANINGFUL_DELTA)
      .length,
    improvedCount: rows.filter((row) => row.delta !== null && row.delta >= MEANINGFUL_DELTA)
      .length,
  };
}
