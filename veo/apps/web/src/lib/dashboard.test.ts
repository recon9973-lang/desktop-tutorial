/**
 * 대시보드 — 뭐가 밀려 있나.
 *
 * 영역마다 자기 숫자를 하나씩 든다. 여기서 지키는 것은 **없는 숫자를 지어내지 않는 것**
 * 하나다: 못 읽었거나 아직 없으면 `null` 이고, 0 으로 적으면 "다 처리했다" 로 읽힌다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const listCompanies = vi.fn();
const readHistory = vi.fn();
const readIssues = vi.fn();
const listReports = vi.fn();
const readPageSpeedQuota = vi.fn();

vi.mock('server-only', () => ({}));
vi.mock('@/lib/companies', () => ({ listCompanies }));
vi.mock('@/lib/scan-report', () => ({ readHistory }));
vi.mock('@/lib/issues-api', () => ({ readIssues }));
vi.mock('@/lib/reports', () => ({ listReports }));
vi.mock('@/lib/usage', () => ({ readPageSpeedQuota }));

const { readDashboard } = await import('./dashboard');

const NOW = new Date('2026-08-04T09:00:00Z').getTime();
const DAY = 86_400_000;

function entry(score: number | null, daysAgo: number) {
  return {
    scanRunId: `run-${score}-${daysAgo}`,
    startedAt: new Date(NOW - daysAgo * DAY).toISOString(),
    score,
    specVersion: '1.9.0',
    urlsCollected: 10,
    status: 'SCORED',
    bandId: null,
    coverage: 1,
    confidence: 1,
    requestedByName: null,
    comparableWithLatest: true,
  };
}

function withSites(count: number) {
  const sites = Array.from({ length: count }, (_, index) => ({
    siteId: `s${index}`,
    origin: `https://s${index}.example/`,
    displayName: `사이트${index}`,
    projectId: 'p',
    isPrimary: false,
  }));
  listCompanies.mockResolvedValue({
    ok: true,
    data: [{ customerId: 'c1', name: '온담', isRegistered: true, sites, projects: [] }],
    meta: {},
  });
}

function area(data: Awaited<ReturnType<typeof readDashboard>>, key: string) {
  return data?.areas.find((one) => one.key === key);
}

beforeEach(() => {
  listCompanies.mockReset();
  readHistory.mockReset();
  readIssues.mockReset();
  listReports.mockReset();
  readPageSpeedQuota.mockReset();

  withSites(1);
  readHistory.mockResolvedValue({ ok: true, data: [entry(80, 1)], meta: {} });
  readIssues.mockResolvedValue({ ok: true, data: [], meta: {} });
  listReports.mockResolvedValue({ ok: true, data: [], meta: {} });
  readPageSpeedQuota.mockResolvedValue({
    ok: true,
    data: {
      provider: 'pagespeed',
      calls_today: 10,
      calls_by_this_organization: 4,
      daily_quota: 100,
      remaining: 90,
      used_ratio: 0.1,
      is_warning: false,
      is_exhausted: false,
    },
    meta: {},
  });
});

describe('영역마다 자기 숫자를 든다', () => {
  it('사이드바를 한 벌 더 만들지 않는다 — 모든 줄이 숫자 자리를 갖는다', async () => {
    const data = await readDashboard(NOW);

    expect(data?.areas.length).toBeGreaterThanOrEqual(4);
    for (const row of data?.areas ?? []) {
      expect(row.href).toMatch(/^\/console\//);
      expect(row.label).not.toBe('');
    }
  });

  it('진단은 평균 점수를 든다', async () => {
    const data = await readDashboard(NOW);

    expect(area(data, 'seo')?.value).toBe(80);
  });

  it('이슈는 미해결 건수를 든다 — 닫힌 것은 세지 않는다', async () => {
    readIssues.mockResolvedValue({
      ok: true,
      data: [
        { is_open: true, recurrence_count: 0 },
        { is_open: true, recurrence_count: 0 },
        { is_open: false, recurrence_count: 0 },
      ],
      meta: {},
    });

    const data = await readDashboard(NOW);

    expect(area(data, 'issues')?.value).toBe(2);
  });

  it('재발한 이슈가 있으면 더 센 색을 쓴다', async () => {
    readIssues.mockResolvedValue({
      ok: true,
      data: [{ is_open: true, recurrence_count: 2 }],
      meta: {},
    });

    const data = await readDashboard(NOW);

    expect(area(data, 'issues')?.tone).toBe('fail');
  });

  it('사용량은 전체에서 나간 비율을 든다 — 우리 몫이 아니다', async () => {
    const data = await readDashboard(NOW);

    // 우리 조직은 4회지만 키 전체로는 10%가 나갔다. 우리 몫을 그리면 "아직 여유 있다"
    // 고 읽는 동안 키가 막힌다.
    expect(area(data, 'usage')?.value).toBe(10);
  });
});

describe('없는 숫자를 지어내지 않는다', () => {
  it('한 번도 재지 않았으면 평균이 없다 — 0이 아니다', async () => {
    readHistory.mockResolvedValue({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    expect(area(data, 'seo')?.value).toBeNull();
  });

  it('평균의 분모는 잰 곳뿐이다', async () => {
    withSites(2);
    readHistory
      .mockResolvedValueOnce({ ok: true, data: [entry(80, 1)], meta: {} })
      .mockResolvedValueOnce({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    // 80 과 (없음) 의 평균은 40 이 아니라 80 이다.
    expect(area(data, 'seo')?.value).toBe(80);
  });

  it('이슈를 못 읽으면 0건이라고 하지 않는다', async () => {
    readIssues.mockResolvedValue({ ok: false, reason: 'SERVER_ERROR', message: null });

    const data = await readDashboard(NOW);

    // 0 으로 적으면 "다 처리했다" 로 읽힌다.
    expect(area(data, 'issues')?.value).toBeNull();
  });

  it('사용량을 못 읽으면 0%라고 하지 않는다', async () => {
    readPageSpeedQuota.mockResolvedValue({ ok: false, reason: 'SERVER_ERROR', message: null });

    const data = await readDashboard(NOW);

    expect(area(data, 'usage')?.value).toBeNull();
  });
});

describe('밀린 것을 말한다', () => {
  it('재지 않은 곳과 오래된 곳을 따로 적는다', async () => {
    withSites(2);
    readHistory
      .mockResolvedValueOnce({ ok: true, data: [entry(80, 20)], meta: {} })
      .mockResolvedValueOnce({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    // 접으면 "한 번도 안 잼" 과 "오래됨" 이 같은 일이 된다.
    expect(area(data, 'seo')?.note).toContain('미측정 1곳');
    expect(area(data, 'seo')?.note).toContain('14일 경과 1곳');
  });

  it('밀린 것이 없으면 색을 쓰지 않는다', async () => {
    const data = await readDashboard(NOW);

    expect(area(data, 'seo')?.tone).toBe('plain');
  });

  it('한 번도 발행하지 않은 리포트를 센다', async () => {
    listReports.mockResolvedValue({
      ok: true,
      data: [{ latest_version_number: 1 }, { latest_version_number: null }],
      meta: {},
    });

    const data = await readDashboard(NOW);

    expect(area(data, 'reports')?.note).toContain('미발행 1건');
  });
});

describe('맡은 곳만 센다', () => {
  it('거래처로 등록된 것만 읽는다', async () => {
    await readDashboard(NOW);

    // 영업 중에 한 번 재 본 주소가 "14일 방치" 로 잡히면, 하지 않아도 될 일이 올라온다.
    for (const call of listCompanies.mock.calls) {
      expect(call[0]).toEqual({ registered: true });
    }
  });
});

describe('현황을 못 읽으면 빈 화면으로 꾸미지 않는다', () => {
  it('업체 목록이 실패하면 null 이다', async () => {
    listCompanies.mockResolvedValue({ ok: false, reason: 'SIGNED_OUT', message: null });

    expect(await readDashboard(NOW)).toBeNull();
  });
});
