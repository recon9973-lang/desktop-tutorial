/**
 * 대시보드 — 오늘 어디부터 볼까.
 *
 * 이 화면은 "전체 현황 요약" 이라면서 업체 이름과 주소만 보여줬다. 지금은 다른 탭이
 * 이미 갖고 있는 값을 모은다.
 *
 * 모으는 순간 생기는 위험이 하나 있다: **재지 않은 곳을 0으로 세는 것.** 그러면 평균이
 * 조용히 내려가고, 아무도 그 이유를 모른다. `null` 은 0이 아니라 "모른다" 이고, 그 둘을
 * 같은 칸에 두지 않는 것이 여기서 지키는 전부다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

const listCompanies = vi.fn();
const readHistory = vi.fn();

vi.mock('server-only', () => ({}));
vi.mock('@/lib/companies', () => ({ listCompanies }));
vi.mock('@/lib/scan-report', () => ({ readHistory }));

const { readDashboard } = await import('./dashboard');

const NOW = new Date('2026-08-04T09:00:00Z').getTime();
const DAY = 86_400_000;

function site(id: string, name: string) {
  return { siteId: id, origin: `https://${id}.example/`, displayName: name, projectId: 'p' };
}

function entry(score: number | null, daysAgo: number, specVersion = '1.9.0') {
  return {
    scanRunId: `run-${score}-${daysAgo}`,
    startedAt: new Date(NOW - daysAgo * DAY).toISOString(),
    score,
    specVersion,
    urlsCollected: 10,
    status: 'SCORED',
    bandId: null,
    coverage: 1,
    confidence: 1,
    requestedByName: null,
    comparableWithLatest: true,
  };
}

function companiesWith(sites: ReturnType<typeof site>[]) {
  return { ok: true as const, data: [{ name: '온담', sites }], meta: {} };
}

beforeEach(() => {
  listCompanies.mockReset();
  readHistory.mockReset();
});

describe('재지 않은 곳을 0으로 세지 않는다', () => {
  it('평균의 분모는 잰 곳뿐이다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A'), site('b', 'B')]));
    readHistory
      .mockResolvedValueOnce({ ok: true, data: [entry(80, 1)], meta: {} })
      .mockResolvedValueOnce({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    // 80 과 (없음) 의 평균은 40 이 아니라 80 이다.
    expect(data?.averageScore).toBe(80);
    expect(data?.measuredCount).toBe(1);
    expect(data?.unmeasuredCount).toBe(1);
  });

  it('아무 곳도 재지 않았으면 평균이 없다 — 0이 아니다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A')]));
    readHistory.mockResolvedValue({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    expect(data?.averageScore).toBeNull();
  });

  it('이력을 못 읽은 곳도 0이 아니라 모름이다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A')]));
    readHistory.mockResolvedValue({ ok: false, reason: 'SERVER_ERROR', message: null });

    const data = await readDashboard(NOW);

    expect(data?.sites[0]?.score).toBeNull();
    expect(data?.averageScore).toBeNull();
  });
});

describe('볼 순서대로 정렬한다', () => {
  it('재지 않은 곳이 맨 위 — 가장 먼저 처리할 일이다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', '잰곳'), site('b', '안잰곳')]));
    readHistory
      .mockResolvedValueOnce({ ok: true, data: [entry(30, 1)], meta: {} })
      .mockResolvedValueOnce({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    expect(data?.sites[0]?.label).toBe('안잰곳');
  });

  it('그다음은 점수가 낮은 순', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', '높음'), site('b', '낮음')]));
    readHistory
      .mockResolvedValueOnce({ ok: true, data: [entry(90, 1)], meta: {} })
      .mockResolvedValueOnce({ ok: true, data: [entry(40, 1)], meta: {} });

    const data = await readDashboard(NOW);

    expect(data?.sites.map((one) => one.label)).toEqual(['낮음', '높음']);
  });
});

describe('증감은 같은 명세끼리만 뺀다', () => {
  it('명세가 같으면 뺀다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A')]));
    readHistory.mockResolvedValue({
      ok: true,
      data: [entry(70, 1), entry(75, 3)],
      meta: {},
    });

    const data = await readDashboard(NOW);

    expect(data?.sites[0]?.delta).toBeCloseTo(-5);
    expect(data?.droppedCount).toBe(1);
  });

  it('명세가 다르면 빼지 않는다 — 사이트가 아니라 규칙이 바뀐 차이다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A')]));
    readHistory.mockResolvedValue({
      ok: true,
      data: [entry(70, 1, '1.9.0'), entry(75, 3, '1.8.0')],
      meta: {},
    });

    const data = await readDashboard(NOW);

    expect(data?.sites[0]?.delta).toBeNull();
    expect(data?.droppedCount).toBe(0);
  });
});

describe('방치된 곳을 센다', () => {
  it('14일이 지나면 방치로 센다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A')]));
    readHistory.mockResolvedValue({ ok: true, data: [entry(70, 20)], meta: {} });

    const data = await readDashboard(NOW);

    expect(data?.staleCount).toBe(1);
    expect(data?.sites[0]?.daysSince).toBe(20);
  });

  it('한 번도 재지 않은 곳은 "방치" 로 세지 않는다 — 다른 말이다', async () => {
    listCompanies.mockResolvedValue(companiesWith([site('a', 'A')]));
    readHistory.mockResolvedValue({ ok: true, data: [], meta: {} });

    const data = await readDashboard(NOW);

    expect(data?.staleCount).toBe(0);
    expect(data?.sites[0]?.daysSince).toBeNull();
  });
});

describe('현황을 못 읽으면 빈 화면으로 꾸미지 않는다', () => {
  it('업체 목록이 실패하면 null 이다', async () => {
    listCompanies.mockResolvedValue({ ok: false, reason: 'SIGNED_OUT', message: null });

    expect(await readDashboard(NOW)).toBeNull();
  });
});
