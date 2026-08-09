/**
 * 거래처 화면 — **지어낸 숫자가 나가지 않는다.**
 *
 * 이 화면은 경쟁사(GPTO) 화면 배치를 참고해서 만들었고
 * (`docs/research/2026-08-09-geo-dashboard-benchmark.md`), 그 배치에서 **일부러 베끼지
 * 않은 것 두 가지**가 이 파일이 지키는 전부다.
 *
 * 1. **조건이 다르면 증감을 그리지 않는다.** 저 화면은 `19% → 55%` 를 조건 표기 없이
 *    낸다. 명세 판이나 훑은 장수가 달라졌으면 두 숫자는 같은 자로 잰 값이 아니고,
 *    그때 화살표를 그리면 **우리가 자를 바꾼 일**이 거래처의 개선/악화로 읽힌다.
 *
 * 2. **아직 안 켠 축을 0 으로 채우지 않는다.** AI 답변 관측은 한 번도 안 돌았다.
 *    `0%` 는 "쟀는데 언급이 없었다" 로 읽히는데 그것은 재지 않은 것과 다른 말이다.
 *
 * 글로 적어 두면 다음에 화면을 손볼 때 "빈 칸이 허전하니 0 을 넣자" 가 다시 들어온다.
 * 어기려면 이 시험을 고쳐야 하고, 고친 것은 커밋에 남는다.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const listCompanies = vi.fn();
const readHistory = vi.fn();
const readIssues = vi.fn();
const listReports = vi.fn();
const listReportableRuns = vi.fn();
const readEngines = vi.fn();
const readPromptSets = vi.fn();
const readRuns = vi.fn();

vi.mock('server-only', () => ({}));
vi.mock('@/lib/companies', () => ({ listCompanies }));
vi.mock('@/lib/scan-report', () => ({ readHistory }));
vi.mock('@/lib/issues-api', () => ({ readIssues }));
vi.mock('@/lib/reports', () => ({ listReports, listReportableRuns }));
vi.mock('@/lib/observations', () => ({ readEngines, readPromptSets, readRuns }));

const { readClientBoard } = await import('./client-dashboard');

const CUSTOMER = 'cus-1';
const PROJECT = 'prj-1';
const SITE = 'site-1';

function entry(
  score: number | null,
  overrides: Partial<{
    scanRunId: string;
    comparableWithLatest: boolean;
    incomparableReasonKo: string | null;
    specVersion: string;
  }> = {},
) {
  return {
    scanRunId: overrides.scanRunId ?? `run-${score}`,
    startedAt: '2026-08-08T00:00:00Z',
    status: 'SUCCEEDED',
    urlsCollected: 10,
    score,
    bandId: null,
    coverage: 1,
    confidence: 1,
    specVersion: overrides.specVersion ?? '1.9.1',
    requestedByName: null,
    comparableWithLatest: overrides.comparableWithLatest ?? true,
    incomparableReasonKo: overrides.incomparableReasonKo ?? null,
  };
}

/** SEO 이력만 정하고 나머지는 조용한 기본값으로 둔다. */
function withSeoHistory(history: ReturnType<typeof entry>[]) {
  readHistory.mockImplementation((_siteId: string, kind: 'SEO' | 'GEO' = 'SEO') =>
    Promise.resolve({ ok: true, data: kind === 'SEO' ? history : [] }),
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  listCompanies.mockResolvedValue({
    ok: true,
    data: [
      {
        customerId: CUSTOMER,
        name: '참사랑한의원',
        industry: null,
        address: '서울시 어딘가',
        isRegistered: true,
        sites: [
          {
            siteId: SITE,
            origin: 'https://example.kr',
            displayName: 'example.kr',
            isPrimary: true,
            projectId: PROJECT,
          },
        ],
        projects: [{ id: PROJECT, name: '기본' }],
      },
    ],
  });

  withSeoHistory([]);
  readIssues.mockResolvedValue({ ok: true, data: [] });
  listReports.mockResolvedValue({ ok: true, data: [] });
  listReportableRuns.mockResolvedValue({ ok: true, data: [] });
  readEngines.mockResolvedValue({ ok: true, data: { engines: [], usable_count: 0, note_ko: '' } });
  readPromptSets.mockResolvedValue({ ok: true, data: { items: [], total: 0 } });
  readRuns.mockResolvedValue({ ok: true, data: { items: [], total: 0 } });
});

describe('증감은 조건이 같을 때만', () => {
  it('직전 진단이 비교 가능하면 그 값을 들고 온다', async () => {
    withSeoHistory([entry(71.03), entry(64.2, { scanRunId: 'older' })]);

    const board = await readClientBoard(CUSTOMER);

    expect(board?.sites[0]?.seo.previous?.score).toBe(64.2);
    expect(board?.sites[0]?.seo.incomparableReasonKo).toBeNull();
  });

  it('조건이 다르면 직전 값을 비우고 이유를 들고 온다', async () => {
    withSeoHistory([
      entry(71.03),
      entry(64.2, {
        scanRunId: 'older',
        comparableWithLatest: false,
        incomparableReasonKo: '명세 판이 다릅니다',
      }),
    ]);

    const board = await readClientBoard(CUSTOMER);

    // 값이 있는데도 비운다. 이것을 그리면 우리가 자를 바꾼 일이 개선으로 읽힌다.
    expect(board?.sites[0]?.seo.previous).toBeNull();
    expect(board?.sites[0]?.seo.incomparableReasonKo).toBe('명세 판이 다릅니다');
  });

  it('이유가 안 왔어도 비교 가능으로 넘기지 않는다', async () => {
    withSeoHistory([
      entry(71.03),
      entry(64.2, { scanRunId: 'older', comparableWithLatest: false }),
    ]);

    const board = await readClientBoard(CUSTOMER);

    expect(board?.sites[0]?.seo.previous).toBeNull();
    expect(board?.sites[0]?.seo.incomparableReasonKo).not.toBeNull();
  });

  it('첫 진단과 조건 불일치를 같은 말로 적지 않는다', async () => {
    withSeoHistory([entry(71.03)]);

    const board = await readClientBoard(CUSTOMER);

    expect(board?.sites[0]?.seo.incomparableReasonKo).toBe('이번이 첫 진단입니다');
  });

  it('한 번도 안 쟀으면 이유도 없다 — 없는 것에 사정을 붙이지 않는다', async () => {
    withSeoHistory([]);

    const board = await readClientBoard(CUSTOMER);

    expect(board?.sites[0]?.seo.latest).toBeNull();
    expect(board?.sites[0]?.seo.incomparableReasonKo).toBeNull();
  });
});

describe('SEO 와 GEO 는 각자의 이력을 쓴다', () => {
  it('한쪽 이력으로 다른 쪽을 그리지 않는다', async () => {
    readHistory.mockImplementation((_siteId: string, kind: 'SEO' | 'GEO' = 'SEO') =>
      Promise.resolve({
        ok: true,
        data: kind === 'SEO' ? [entry(71.03)] : [entry(40.5, { scanRunId: 'geo' })],
      }),
    );

    const board = await readClientBoard(CUSTOMER);

    expect(board?.sites[0]?.seo.latest?.score).toBe(71.03);
    expect(board?.sites[0]?.geo.latest?.score).toBe(40.5);
  });
});

describe('AI 답변 칸은 값이 아니라 막힌 자리를 든다', () => {
  it('쓸 수 있는 엔진이 없으면 거기서 멈춘다', async () => {
    readEngines.mockResolvedValue({
      ok: true,
      data: { engines: [{ engine: 'OPENAI', usable: false }], usable_count: 0, note_ko: '' },
    });

    const board = await readClientBoard(CUSTOMER);

    expect(board?.observation.state).toBe('NO_ENGINE');
  });

  it('엔진은 있고 질문 집합이 없으면 질문을 가리킨다', async () => {
    readEngines.mockResolvedValue({
      ok: true,
      data: { engines: [{ engine: 'OPENAI', usable: true }], usable_count: 1, note_ko: '' },
    });

    const board = await readClientBoard(CUSTOMER);

    expect(board?.observation.state).toBe('NO_PROMPT_SET');
  });

  it('남의 프로젝트 질문 집합을 우리 것으로 세지 않는다', async () => {
    readEngines.mockResolvedValue({
      ok: true,
      data: { engines: [{ engine: 'OPENAI', usable: true }], usable_count: 1, note_ko: '' },
    });
    readPromptSets.mockResolvedValue({
      ok: true,
      data: { items: [{ id: 'ps-x', project_id: 'someone-else', prompts: [] }], total: 1 },
    });

    const board = await readClientBoard(CUSTOMER);

    expect(board?.observation.state).toBe('NO_PROMPT_SET');
  });

  it('수동 실행은 관측이 돌고 있다는 근거가 아니다', async () => {
    readEngines.mockResolvedValue({
      ok: true,
      data: { engines: [{ engine: 'OPENAI', usable: true }], usable_count: 1, note_ko: '' },
    });
    readPromptSets.mockResolvedValue({
      ok: true,
      data: { items: [{ id: 'ps-1', project_id: PROJECT, prompts: [{ prompt_id: 'p1' }] }], total: 1 },
    });
    readRuns.mockResolvedValue({
      ok: true,
      data: {
        items: [
          { id: 'run-1', prompt_set_id: 'ps-1', kind: 'MANUAL', started_at: '2026-08-01' },
        ],
        total: 1,
      },
    });

    const board = await readClientBoard(CUSTOMER);

    // 사람이 그 순간 고른 검색어를 잰 것이라 추이가 아니다(`observations.ts:148`).
    expect(board?.observation.state).toBe('NEVER_RUN');
  });

  it('정기 실행이 있으면 표본 크기를 함께 들고 온다', async () => {
    readEngines.mockResolvedValue({
      ok: true,
      data: { engines: [{ engine: 'OPENAI', usable: true }], usable_count: 1, note_ko: '' },
    });
    readPromptSets.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            id: 'ps-1',
            project_id: PROJECT,
            prompts: [{ prompt_id: 'p1' }, { prompt_id: 'p2' }, { prompt_id: 'p3' }],
          },
        ],
        total: 1,
      },
    });
    readRuns.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            id: 'run-old',
            prompt_set_id: 'ps-1',
            kind: 'SCHEDULED',
            started_at: '2026-07-01',
            summary_ko: '옛것',
            repetitions_per_prompt: 3,
            finished_at: '2026-07-01',
          },
          {
            id: 'run-new',
            prompt_set_id: 'ps-1',
            kind: 'SCHEDULED',
            started_at: '2026-08-01',
            summary_ko: '최근',
            repetitions_per_prompt: 5,
            finished_at: '2026-08-01',
          },
        ],
        total: 2,
      },
    });

    const board = await readClientBoard(CUSTOMER);

    expect(board?.observation).toMatchObject({
      state: 'MEASURED',
      runId: 'run-new',
      // 표본을 함께 내지 않으면 언급률만 보고 정밀도를 오해한다. 질문 3개 x 반복 5회는
      // 오차 폭이 ±20pp 를 넘는다 — 그 사실이 화면에 남아 있어야 한다.
      promptCount: 3,
      repetitionsPerPrompt: 5,
    });
  });
});

describe('셀 수 없으면 0 이라고 하지 않는다', () => {
  it('이슈를 한 프로젝트라도 못 읽으면 합계를 비운다', async () => {
    readIssues.mockResolvedValue({ ok: false, message: '연결 실패' });

    const board = await readClientBoard(CUSTOMER);

    // 일부만 더한 값을 전체인 척 내면 "이슈 3건" 이 실제로는 30건일 수 있다.
    expect(board?.issues).toBeNull();
  });

  it('리포트를 못 읽으면 합계를 비운다', async () => {
    listReports.mockResolvedValue({ ok: false, message: '연결 실패' });

    const board = await readClientBoard(CUSTOMER);

    expect(board?.reports).toBeNull();
  });

  it('열린 것과 닫은 것을 따로 센다', async () => {
    readIssues.mockResolvedValue({
      ok: true,
      data: [
        { id: 'i1', is_open: true, recurrence_count: 0 },
        { id: 'i2', is_open: true, recurrence_count: 2 },
        { id: 'i3', is_open: false, recurrence_count: 0 },
      ],
    });

    const board = await readClientBoard(CUSTOMER);

    expect(board?.issues).toEqual({ open: 2, recurring: 1, closed: 1 });
  });
});

describe('업체를 못 찾으면 자료를 지어내지 않는다', () => {
  it('없는 업체는 null', async () => {
    const board = await readClientBoard('없는-업체');
    expect(board).toBeNull();
  });

  it('목록을 못 읽어도 null — 빈 화면을 "자료 없음" 으로 그리지 않는다', async () => {
    listCompanies.mockResolvedValue({ ok: false, message: '연결 실패' });
    const board = await readClientBoard(CUSTOMER);
    expect(board).toBeNull();
  });
});
