import 'server-only';

import { listCompanies, type Company } from '@/lib/companies';
import { readIssues } from '@/lib/issues-api';
import { listReportableRuns, listReports } from '@/lib/reports';
import { readEngines, readPromptSets, readRuns } from '@/lib/observations';
import { readHistory, type HistoryEntry } from '@/lib/scan-report';

/**
 * 거래처 한 곳의 화면 — **이 업체에 무슨 일이 있었나.**
 *
 * ## 왜 이 화면이 필요했나
 *
 * 4단계가 통째로 비어 있었다(사장님 2026-08-09):
 * *"진단 업체 등록 - 자동 진단 - 데이터 수집 - **업체별 대시보드에 수집 진단 결과 노출**"*.
 * 앞의 세 단계는 돌고 있었고 자료도 쌓여 있었는데, 그 자료를 **거래처 단위로** 보여
 * 주는 자리가 없었다. 업체 관리 화면은 이름과 주소만 보여 주고, `/console/dashboard`
 * 는 맡은 곳 전부를 하나의 평균으로 뭉갠다. 거래처를 만나서 열 화면이 없었다.
 *
 * ## 배치는 경쟁사에서 가져왔다
 *
 * `docs/research/2026-08-09-geo-dashboard-benchmark.md` 참조. GPTO 화면 캡처 5장을
 * 판독한 결과 그 화면의 문법은 점수가 아니라 **`기존 → 현재`** 였다. 아홉 덩어리 중
 * 절대값 하나만 보여 주는 칸이 없다.
 *
 * 그 문법을 그대로 쓰되 **재료는 우리 것으로** 채운다. 저들의 일곱 칸은 전부 AI 답변
 * 관측을 먹는데 우리 `observation_runs` 는 0행이다. 대신 우리에게는 저들에게 없는
 * SEO 45건·GEO 19건 진단이 47회 쌓여 있다.
 *
 * ## 두 가지는 베끼지 않는다
 *
 * **1. 조건이 다르면 증감을 그리지 않는다.** 저 화면은 `19% → 55%` 를 조건 표기 없이
 * 낸다. 우리는 :attr:`HistoryEntry.comparableWithLatest` 가 참일 때만 화살표를 그리고,
 * 거짓이면 그 이유를 대신 적는다(ADR 0010).
 *
 * **2. 빈 칸을 0 으로 채우지 않는다.** AI 답변 축은 아직 한 번도 안 돌았다. `0%` 라고
 * 쓰면 "쟀는데 언급이 없었다" 로 읽힌다. 재지 않은 것은 재지 않았다고 쓰고, **무엇을
 * 하면 채워지는지**를 함께 적는다(ADR 0002 · `lib/dashboard.ts:22`).
 *
 * ## 새로 재지 않는다
 *
 * 여기서 대상 사이트에 요청이 나가지 않는다. 이미 저장된 것만 모은다 — 화면 하나를
 * 열었다고 거래처 서버를 두드리면, 화면을 자주 여는 것이 곧 부하가 된다.
 */

/** 하나의 눈금(SEO 또는 GEO)이 이 사이트에서 어떻게 움직였나. */
export interface ScaleTrack {
  readonly kind: 'SEO' | 'GEO';
  /** 가장 최근 진단. 한 번도 안 쟀으면 `null`. */
  readonly latest: HistoryEntry | null;
  /**
   * 직전 진단 — **조건이 같을 때만** 채운다.
   *
   * 명세 판이 바뀌었거나 훑은 장수가 달라졌으면 두 숫자는 같은 자를 쓴 값이 아니다.
   * 그때 화살표를 그리면 우리가 자를 바꾼 것을 거래처가 개선/악화로 읽는다.
   */
  readonly previous: HistoryEntry | null;
  /** `previous` 가 비어 있는 이유. 비교할 수 있으면 `null`. */
  readonly incomparableReasonKo: string | null;
  /** 추이용. 최신이 앞. 조건이 섞여 있을 수 있으므로 **점만 찍고 선을 잇지 않는다.** */
  readonly history: readonly HistoryEntry[];
}

/** AI 답변 축의 상태. 값이 아니라 **왜 값이 없는가**를 들고 있다. */
export type ObservationSlot =
  | { readonly state: 'NO_ENGINE'; readonly whyKo: string; readonly nextKo: string }
  | { readonly state: 'NO_PROMPT_SET'; readonly whyKo: string; readonly nextKo: string }
  | { readonly state: 'NEVER_RUN'; readonly whyKo: string; readonly nextKo: string }
  | {
      readonly state: 'MEASURED';
      readonly runId: string;
      readonly summaryKo: string;
      readonly finishedAt: string | null;
      readonly repetitionsPerPrompt: number;
      readonly promptCount: number;
    };

export interface SiteBoard {
  readonly siteId: string;
  readonly projectId: string;
  readonly origin: string;
  readonly displayName: string;
  readonly isPrimary: boolean;
  readonly seo: ScaleTrack;
  readonly geo: ScaleTrack;
}

export interface IssueTally {
  readonly open: number;
  readonly recurring: number;
  readonly closed: number;
}

export interface ClientBoard {
  readonly company: Company;
  readonly sites: readonly SiteBoard[];
  /** 못 읽었으면 `null` — 0 건이 아니다. */
  readonly issues: IssueTally | null;
  readonly reports: { readonly total: number; readonly unpublished: number } | null;
  /** 리포트로 만들 수 있는데 아직 안 만든 진단 수. 못 읽었으면 `null`. */
  readonly reportableRuns: number | null;
  readonly observation: ObservationSlot;
}

function trackOf(kind: 'SEO' | 'GEO', history: readonly HistoryEntry[]): ScaleTrack {
  const latest = history[0] ?? null;
  const candidate = history[1] ?? null;

  if (candidate === null) {
    return {
      kind,
      latest,
      previous: null,
      // 한 번만 잰 것은 "조건이 달라서 못 비교" 가 아니다. 둘을 같은 말로 적으면
      // 자를 바꾼 자리와 이제 막 시작한 자리가 구별되지 않는다.
      incomparableReasonKo: latest === null ? null : '이번이 첫 진단입니다',
      history,
    };
  }

  if (!candidate.comparableWithLatest) {
    return {
      kind,
      latest,
      previous: null,
      incomparableReasonKo:
        candidate.incomparableReasonKo ??
        '직전 진단과 측정 조건이 달라 증감을 표시하지 않습니다',
      history,
    };
  }

  return { kind, latest, previous: candidate, incomparableReasonKo: null, history };
}

/**
 * AI 답변 축이 왜 비어 있는가 — **막힌 자리를 하나만 짚는다.**
 *
 * 세 가지가 다 없을 때 셋을 다 늘어놓으면 무엇부터 할지 알 수 없다. 앞의 것이 없으면
 * 뒤의 것은 물어볼 수도 없으므로 순서대로 하나만 말한다.
 */
async function observationSlot(projectIds: readonly string[]): Promise<ObservationSlot> {
  const [engines, promptSets, runs] = await Promise.all([
    readEngines(),
    readPromptSets(),
    readRuns(),
  ]);

  const usable = engines.ok ? engines.data.engines.filter((engine) => engine.usable) : [];
  if (usable.length === 0) {
    return {
      state: 'NO_ENGINE',
      whyKo: '쓸 수 있는 AI 엔진이 없습니다.',
      nextKo: 'GEO 화면에서 엔진 상태를 확인하고 열쇠를 등록하면 관측을 시작할 수 있습니다.',
    };
  }

  const mine = promptSets.ok
    ? promptSets.data.items.filter((set) => projectIds.includes(set.project_id))
    : [];
  if (mine.length === 0) {
    return {
      state: 'NO_PROMPT_SET',
      whyKo: '이 업체의 질문 집합이 없습니다.',
      // 개수·주기·반복은 **이미 정해져 있다**(`docs/observation-engine.md` §9,
      // 사장님 결정 2026-08-08). 화면이 다른 수를 권하면 그 자리에서 설계가 두 벌이 된다.
      nextKo:
        '거래처의 손님이 AI에게 실제로 물을 만한 질문을 등록해야 관측이 시작됩니다. ' +
        '확정된 설계는 핵심 질문 5~8개(주 1회)와 확장 질문 20개 안팎(월 1회)입니다.',
    };
  }

  const setIds = mine.map((set) => set.id);
  // 수동 실행은 사람이 그 순간 고른 질문이라 추이가 아니다(`observations.ts:148`).
  // 정기 실행만 "관측이 돌고 있다" 의 근거로 친다.
  const scheduled = runs.ok
    ? runs.data.items.filter(
        (run) => setIds.includes(run.prompt_set_id) && run.kind !== 'MANUAL',
      )
    : [];

  if (scheduled.length === 0) {
    return {
      state: 'NEVER_RUN',
      whyKo: '질문은 등록되어 있으나 아직 한 번도 관측하지 않았습니다.',
      nextKo: 'GEO 화면에서 관측을 실행하면 이 자리에 언급률과 인용 출처가 채워집니다.',
    };
  }

  const newest = scheduled.reduce((best, run) =>
    (run.started_at ?? '') > (best.started_at ?? '') ? run : best,
  );
  const promptCount =
    mine.find((set) => set.id === newest.prompt_set_id)?.prompts.length ?? 0;

  return {
    state: 'MEASURED',
    runId: newest.id,
    summaryKo: newest.summary_ko,
    finishedAt: newest.finished_at,
    repetitionsPerPrompt: newest.repetitions_per_prompt,
    promptCount,
  };
}

/**
 * 거래처 하나의 화면 자료를 모은다. 업체를 못 찾으면 `null`.
 *
 * 사이트마다 SEO·GEO 이력을 **각각** 읽는다. 한 번의 진단이 두 눈금을 따로 저장하므로
 * 한쪽 이력으로 다른 쪽 증감을 그리면 화면이 거짓말을 한다(`scan-report.ts:78`).
 */
export async function readClientBoard(customerId: string): Promise<ClientBoard | null> {
  // 걸러내지 않는다. 이 화면은 링크로 들어오는 자리라, 아직 거래처로 올리지 않은
  // 업체를 열었을 때 "없습니다" 가 나오면 안 된다.
  const companies = await listCompanies();
  if (!companies.ok) return null;

  const company = companies.data.find((row) => row.customerId === customerId);
  if (company === undefined) return null;

  const projectIds = company.projects.map((project) => project.id);

  const [siteBoards, issues, reports, reportable, observation] = await Promise.all([
    Promise.all(
      company.sites.map(async (site): Promise<SiteBoard> => {
        const [seo, geo] = await Promise.all([
          readHistory(site.siteId, 'SEO'),
          readHistory(site.siteId, 'GEO'),
        ]);
        return {
          siteId: site.siteId,
          projectId: site.projectId,
          origin: site.origin,
          displayName: site.displayName,
          isPrimary: site.isPrimary,
          seo: trackOf('SEO', seo.ok ? seo.data : []),
          geo: trackOf('GEO', geo.ok ? geo.data : []),
        };
      }),
    ),
    tallyIssues(projectIds),
    tallyReports(projectIds),
    tallyReportable(projectIds),
    observationSlot(projectIds),
  ]);

  return {
    company,
    sites: siteBoards,
    issues,
    reports,
    reportableRuns: reportable,
    observation,
  };
}

async function tallyIssues(projectIds: readonly string[]): Promise<IssueTally | null> {
  if (projectIds.length === 0) return { open: 0, recurring: 0, closed: 0 };

  const perProject = await Promise.all(projectIds.map((id) => readIssues(id)));
  // 한 프로젝트라도 못 읽었으면 합계를 내지 않는다. 일부만 더한 값을 전체인 척
  // 내놓으면 "이슈 3건" 이 실제로는 30건일 수 있다.
  if (perProject.some((outcome) => !outcome.ok)) return null;

  const all = perProject.flatMap((outcome) => (outcome.ok ? outcome.data : []));
  const open = all.filter((issue) => issue.is_open);

  return {
    open: open.length,
    recurring: open.filter((issue) => issue.recurrence_count > 0).length,
    closed: all.length - open.length,
  };
}

async function tallyReports(
  projectIds: readonly string[],
): Promise<{ total: number; unpublished: number } | null> {
  if (projectIds.length === 0) return { total: 0, unpublished: 0 };

  const perProject = await Promise.all(projectIds.map((id) => listReports(id)));
  if (perProject.some((outcome) => !outcome.ok)) return null;

  const rows = perProject.flatMap((outcome) => (outcome.ok ? outcome.data : []));
  return {
    total: rows.length,
    unpublished: rows.filter((row) => row.latest_version_number === null).length,
  };
}

async function tallyReportable(projectIds: readonly string[]): Promise<number | null> {
  if (projectIds.length === 0) return 0;

  const perProject = await Promise.all(projectIds.map((id) => listReportableRuns(id)));
  if (perProject.some((outcome) => !outcome.ok)) return null;

  return perProject.reduce(
    (sum, outcome) => sum + (outcome.ok ? outcome.data.length : 0),
    0,
  );
}

/**
 * 이 거래처의 이슈만 보여 주는 주소.
 *
 * 프로젝트가 정확히 하나일 때만 거른다. 여럿인데 하나만 골라 보내면 나머지가 조용히
 * 빠지고, 그 화면의 건수가 이 카드의 합계와 어긋난다 — 두 숫자가 다르면 사람은 어느
 * 쪽도 믿지 않는다.
 */
export function issuesHref(board: ClientBoard): string {
  const only = board.company.projects.length === 1 ? board.company.projects[0] : undefined;
  return only === undefined
    ? '/console/issues'
    : `/console/issues?project=${encodeURIComponent(only.id)}`;
}

/** 리포트도 같은 규칙. 하나일 때만 거른다. */
export function reportsHref(board: ClientBoard): string {
  const only = board.company.projects.length === 1 ? board.company.projects[0] : undefined;
  return only === undefined
    ? '/console/reports'
    : `/console/reports?project=${encodeURIComponent(only.id)}`;
}
