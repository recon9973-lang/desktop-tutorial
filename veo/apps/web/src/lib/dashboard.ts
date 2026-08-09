import 'server-only';

import { listCompanies } from '@/lib/companies';
import { readIssues } from '@/lib/issues-api';
import { listReports } from '@/lib/reports';
import { readHistory } from '@/lib/scan-report';
import { readPageSpeedQuota } from '@/lib/usage';

/**
 * 대시보드 — **뭐가 밀려 있나**.
 *
 * 이 화면은 두 번 방향을 틀었다. 처음에는 업체 이름과 주소만 있어 업체 관리와 같은
 * 일을 했고, 다음에는 SEO 점수만 모아서 나머지 여섯 영역이 눌러 보기 전에는 보이지
 * 않았다. 지금은 **영역마다 자기 숫자를 하나씩** 들고 있다(사용자 결정).
 *
 * 왼쪽 사이드바를 한 벌 더 만들지 않는다. 이름만 나열하면 두 벌이 되고 반드시 어긋난다 —
 * 각 줄은 사이드바가 말할 수 없는 **숫자**를 하나 들고 있어야 자리값을 한다(0-D).
 *
 * 새로 재지 않는다. 다른 탭이 이미 가진 값만 모은다. 대시보드가 자기만의 측정을 하면
 * 그 탭의 숫자와 어긋나는 날이 오고, 그때 어느 쪽을 믿을지 알 수 없다.
 *
 * **없는 숫자를 지어내지 않는다.** 못 읽었거나 아직 없으면 `value` 가 `null` 이고
 * 화면에는 "—" 가 나온다. 0 과 모름은 다른 말이고, 0 으로 적으면 "다 처리했다" 로
 * 읽힌다.
 */

export type AreaTone = 'plain' | 'warn' | 'fail';

export interface AreaRow {
  readonly key: string;
  /** 사이드바와 **같은 이름**을 쓴다. 여기서만 다르게 부르면 같은 화면이 둘로 보인다. */
  readonly label: string;
  readonly href: string;
  /** 이 영역이 무엇에 답하는지 한 줄. */
  readonly hint: string;
  /** 큰 숫자. 못 읽었거나 아직 없으면 `null` — 0 이 아니다. */
  readonly value: number | null;
  readonly unit: string;
  /** 숫자 밑에 붙는 사정. 밀린 것이 있으면 그것을 말한다. */
  readonly note: string;
  readonly tone: AreaTone;
}

export interface DashboardData {
  readonly areas: readonly AreaRow[];
  /** 맡은 거래처 수. 머리말에 쓴다. */
  readonly siteCount: number;
}

const STALE_DAYS = 14;
const DAY = 86_400_000;

/**
 * 진단 — 맡은 곳의 점수와, 아직 재지 않았거나 오래된 곳.
 *
 * 업체 목록을 **넘겨받는다.** 여기서 다시 부르면 같은 목록을 두 번 읽게 되고, 그 한 번이
 * 세 왕복(고객·프로젝트·사이트)이다. 서버가 한국에서 멀 때 그것이 그대로 대기 시간이다.
 */
async function diagnosisRow(
  now: number,
  sites: readonly { readonly siteId: string }[],
): Promise<AreaRow> {
  const base = {
    key: 'seo',
    label: '진단',
    href: '/console/seo',
    hint: 'SEO·GEO 준비도',
    unit: '점',
  } as const;

  if (sites.length === 0) {
    return { ...base, value: null, note: '등록된 측정 주소가 없습니다', tone: 'plain' };
  }

  const histories = await Promise.all(sites.map((site) => readHistory(site.siteId)));
  const latest = histories.map((history) => (history.ok ? history.data[0] : undefined));

  // 잰 곳만 분모에 넣는다. 재지 않은 곳을 0 으로 세면 평균이 조용히 내려가고, 아무도
  // 그 이유를 모른다.
  const scored = latest.filter((entry) => entry?.score != null);
  const total = scored.reduce((sum, entry) => sum + (entry?.score ?? 0), 0);
  const unmeasured = latest.length - scored.length;
  const stale = latest.filter((entry) => {
    if (entry === undefined) return false;
    const at = new Date(entry.startedAt).getTime();
    return Number.isFinite(at) && now - at >= STALE_DAYS * DAY;
  }).length;

  // "한 번도 안 잼" 과 "오래됨" 은 다른 일이다. 접으면 다른 일이 같은 일이 된다.
  const pending: string[] = [];
  if (unmeasured > 0) pending.push(`미측정 ${unmeasured}곳`);
  if (stale > 0) pending.push(`${STALE_DAYS}일 경과 ${stale}곳`);

  return {
    ...base,
    // 자료 층에서 깎지 않는다. 표기는 화면이 `formatScore` 로 정한다.
    value: scored.length === 0 ? null : total / scored.length,
    note: pending.length > 0 ? pending.join(' · ') : `맡은 ${sites.length}곳 모두 최신입니다`,
    tone: unmeasured > 0 || stale > 0 ? 'warn' : 'plain',
  };
}

async function issuesRow(): Promise<AreaRow> {
  const base = {
    key: 'issues',
    label: '이슈',
    href: '/console/issues',
    hint: '조치가 필요한 항목',
    unit: '건',
  } as const;

  const found = await readIssues(null);
  if (!found.ok) {
    return { ...base, value: null, note: '불러오지 못했습니다', tone: 'plain' };
  }

  const open = found.data.filter((issue) => issue.is_open);
  // 재발한 것은 처음 보는 것과 같은 무게가 아니다 — 고쳤다고 믿고 넘어간 자리다.
  const recurring = open.filter((issue) => issue.recurrence_count > 0).length;

  return {
    ...base,
    value: open.length,
    note: recurring > 0 ? `재발 ${recurring}건 포함` : '재발 없음',
    tone: recurring > 0 ? 'fail' : open.length > 0 ? 'warn' : 'plain',
  };
}

async function reportsRow(): Promise<AreaRow> {
  const base = {
    key: 'reports',
    label: '리포트',
    href: '/console/reports',
    hint: '공유용 리포트',
    unit: '건',
  } as const;

  const found = await listReports(null);
  if (!found.ok) {
    return { ...base, value: null, note: '불러오지 못했습니다', tone: 'plain' };
  }

  // 만들어 두고 한 번도 발행하지 않은 것 — 거래처에 아직 가지 않은 리포트다.
  const unpublished = found.data.filter((row) => row.latest_version_number === null).length;

  return {
    ...base,
    value: found.data.length,
    note: unpublished > 0 ? `미발행 ${unpublished}건` : '모두 발행됨',
    tone: unpublished > 0 ? 'warn' : 'plain',
  };
}

async function usageRow(): Promise<AreaRow> {
  const base = {
    key: 'usage',
    label: '사용량',
    href: '/console/usage',
    hint: '외부 API 한도',
    unit: '%',
  } as const;

  const quota = await readPageSpeedQuota();
  if (!quota.ok) {
    return { ...base, value: null, note: '불러오지 못했습니다', tone: 'plain' };
  }

  return {
    ...base,
    value: Math.round(quota.data.used_ratio * 100),
    // 남은 양이 아니라 **전체에서 나간 양**이다. 한도는 키에 걸리고 키는 하나다.
    note: `오늘 ${quota.data.calls_today}/${quota.data.daily_quota}회 · 우리 몫 ${quota.data.calls_by_this_organization}회`,
    tone: quota.data.is_exhausted ? 'fail' : quota.data.is_warning ? 'warn' : 'plain',
  };
}

export async function readDashboard(now: number = Date.now()): Promise<DashboardData | null> {
  // 맡은 곳만 센다. 영업 중에 한 번 재 본 주소가 "14일 방치" 로 잡히면, 하지 않아도
  // 될 일이 할 일 목록에 올라온다.
  //
  // 목록은 **한 번만** 읽고 진단 줄에 넘긴다. 두 번 읽으면 세 왕복을 두 번 낸다.
  const companies = await listCompanies({ registered: true });
  if (!companies.ok) return null;
  const sites = companies.data.flatMap((company) => company.sites);

  // 영역끼리는 서로를 필요로 하지 않는다. 줄을 세우면 영역 수만큼 왕복이 늘어난다.
  const [diagnosis, issues, reports, usage] = await Promise.all([
    diagnosisRow(now, sites),
    issuesRow(),
    reportsRow(),
    usageRow(),
  ]);

  return {
    // 밀린 것이 있는 영역이 위로. 같은 급이면 정해진 순서대로 — 매번 자리가 바뀌면
    // 눈이 위치를 기억하지 못한다.
    areas: [diagnosis, issues, reports, usage],
    siteCount: sites.length,
  };
}
