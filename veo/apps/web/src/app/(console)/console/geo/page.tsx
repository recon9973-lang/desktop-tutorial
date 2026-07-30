import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import {
  readEngines,
  readJob,
  readObservationJobs,
  readPromptSets,
  readRun,
  readRuns,
  type EngineStatus,
  type Job,
} from '@/lib/observations';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { JobWatch } from './JobWatch';
import { ReadinessForm } from './ReadinessForm';
import { RunForm, type RunnableEngine } from './RunForm';
import { VisibilityReport } from './VisibilityReport';
import own from './geo.module.css';

export const metadata: Metadata = {
  title: 'GEO 준비도 · AI 가시성 관측',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * 실측으로 확인한 모델별 인용 지원 여부.
 *
 * 목록에 없는 모델을 "돌려주지 않는다" 고 단정하지 않는다 — 재보지 않은 것을 잰 것처럼
 * 말하는 것이기 때문이다. 넓히는 절차는 `docs/operations/verifying-citation-support.md`.
 */
const MODELS_BY_ENGINE: Record<string, readonly { id: string; citesSources: boolean }[]> = {
  OPENAI: [
    { id: 'gpt-5', citesSources: true },
    { id: 'gpt-4o', citesSources: true },
    { id: 'gpt-4.1', citesSources: false },
    { id: 'gpt-4o-mini', citesSources: false },
  ],
};

const ENGINE_LABELS: Record<string, string> = {
  OPENAI: 'ChatGPT (OpenAI)',
  ANTHROPIC: 'Claude (Anthropic)',
  GEMINI: 'Gemini (Google)',
  PERPLEXITY: 'Perplexity',
};

export default async function ConsoleGeoPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const identity = await requireConsoleIdentity();
  const params = await searchParams;

  return (
    <PermissionGate identity={identity} permission="observation:read">
      <ConsoleGeoContent jobId={single(params['job'])} runId={single(params['run'])} />
    </PermissionGate>
  );
}

function single(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

async function ConsoleGeoContent({
  jobId,
  runId,
}: {
  readonly jobId: string | null;
  readonly runId: string | null;
}) {
  const [engines, promptSets, runs, jobs] = await Promise.all([
    readEngines(),
    readPromptSets(),
    readRuns(),
    readObservationJobs(),
  ]);

  // 작업 번호로 들어왔는데 이미 끝났다면 결과로 바로 넘어간다. 사용자가 "완료" 만 보고
  // 결과를 다시 찾아 헤매게 두지 않는다.
  const watched = jobId === null ? null : await readJob(jobId);
  const watchedJob = watched !== null && watched.ok ? watched.data : null;
  const targetRunId = runId ?? watchedJob?.result_run_id ?? null;
  const detail = targetRunId === null ? null : await readRun(targetRunId);

  const usable: RunnableEngine[] = engines.ok
    ? engines.data.engines
        .filter((one) => one.usable)
        .map((one) => ({
          engine: one.engine,
          label: ENGINE_LABELS[one.engine] ?? one.engine,
          models: MODELS_BY_ENGINE[one.engine] ?? [],
        }))
        .filter((one) => one.models.length > 0)
    : [];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>GEO</h1>
        <p className={styles.lede}>
          GEO 화면은 두 가지를 완전히 분리해서 보여줍니다. 하나는 우리가 통제할 수 있는 페이지
          구조의 준비도이고, 다른 하나는 외부 AI 서비스의 응답을 표본으로 관측한 기록입니다.
        </p>
      </div>

      <p className={styles.callout}>
        준비도와 가시성 관측은 측정 대상도 방법도 다르므로, VEO는 두 결과를 하나의 점수로
        합치지 않습니다. 어느 화면에서도 합산 지표를 만들지 않습니다.
      </p>

      <div className={styles.separatedSections}>
        <section aria-labelledby="geo-observation-heading">
          <div className={styles.header}>
            <p className={styles.eyebrow}>1 / 2 · 외부 관측</p>
            <h2 id="geo-observation-heading" className={styles.sectionTitle}>
              AI 가시성 관측
            </h2>
            <p className={styles.sectionLede}>
              지정한 질의에 대해 외부 AI 서비스가 우리 사이트를 언급하거나 인용했는지를 표본
              관측한 기록입니다. 점수가 아니라 관측 결과이며, 같은 질의라도 응답은 달라질 수
              있습니다.
            </p>
          </div>

          {!engines.ok ? (
            <ErrorState
              title="엔진 상태를 불러오지 못했습니다"
              description={engines.message ?? '서버에 연결하지 못했습니다.'}
            />
          ) : (
            <EngineTable engines={engines.data.engines} note={engines.data.note_ko} />
          )}

          {watchedJob !== null ? <JobWatch job={watchedJob} /> : null}

          {promptSets.ok && promptSets.data.items.length > 0 && usable.length > 0 ? (
            <Card title="새 관측 실행" headingLevel={3}>
              <RunForm
                promptSets={promptSets.data.items.map((set) => ({
                  id: set.id,
                  label: `${set.name} ${set.version}`,
                  promptCount: set.prompts.length,
                }))}
                engines={usable}
              />
            </Card>
          ) : (
            <CannotRun
              hasPromptSets={promptSets.ok && promptSets.data.items.length > 0}
              hasEngines={usable.length > 0}
            />
          )}

          {detail !== null && detail.ok ? (
            <VisibilityReport run={detail.data.run} metrics={detail.data.metrics} />
          ) : detail !== null ? (
            <ErrorState
              title="결과를 불러오지 못했습니다"
              description={detail.message ?? '서버에 연결하지 못했습니다.'}
            />
          ) : null}

          <History
            runs={runs.ok ? runs.data.items : []}
            jobs={jobs.ok ? jobs.data.items : []}
            currentRunId={targetRunId}
          />
        </section>

        <hr className={styles.divider} />

        <section aria-labelledby="geo-readiness-heading">
          <div className={styles.header}>
            <p className={styles.eyebrow}>2 / 2 · 구조 평가</p>
            <h2 id="geo-readiness-heading" className={styles.sectionTitle}>
              GEO 준비도
            </h2>
            <p className={styles.sectionLede}>
              AI 답변 엔진이 페이지에 접근하고, 본문을 추출하고, 근거를 검증할 수 있는
              구조인지를 채점 명세에 따라 평가합니다. 우리가 고칠 수 있는 영역입니다.
            </p>
          </div>

          <Card title="준비도 진단" headingLevel={3}>
            <ReadinessForm />
          </Card>
        </section>
      </div>
    </div>
  );
}

/**
 * 아는 엔진을 전부 보여준다. 쓸 수 없는 것도 이유와 함께.
 *
 * 못 쓰는 엔진을 목록에서 빼면 "여기 있는 게 전부" 로 읽히고, 자격증명만 넣으면 잴 수
 * 있었던 것을 아무도 모른 채 지나간다.
 */
function EngineTable({
  engines,
  note,
}: {
  readonly engines: readonly EngineStatus[];
  readonly note: string;
}) {
  return (
    <Card title="AI 엔진 상태" headingLevel={3} tone="flat">
      <ul className={own.engineList}>
        {engines.map((one) => (
          <li key={one.engine} className={own.engineRow}>
            <span className={own.engineName}>{ENGINE_LABELS[one.engine] ?? one.engine}</span>
            <span className={one.usable ? own.engineOk : own.engineOff}>
              {one.state_label_ko}
            </span>
          </li>
        ))}
      </ul>
      <p className={own.pending}>{note}</p>
    </Card>
  );
}

function CannotRun({
  hasPromptSets,
  hasEngines,
}: {
  readonly hasPromptSets: boolean;
  readonly hasEngines: boolean;
}) {
  if (!hasEngines) {
    return (
      <EmptyState
        title="쓸 수 있는 AI 엔진이 없습니다"
        description="자격증명이 등록된 엔진이 없어 관측을 실행할 수 없습니다. 위 목록에서 각 엔진의 상태를 확인하십시오."
      />
    );
  }
  if (!hasPromptSets) {
    return (
      <EmptyState
        title="질문 집합이 없습니다"
        description="관측은 미리 정해 둔 질문 목록으로 실행합니다. 질문 집합을 먼저 만들어 주십시오 — 브랜드에 불리한 질문을 빼고 만들면 노출률이 실제보다 높게 나옵니다."
      />
    );
  }
  return null;
}

/** 지난 실행. 실패와 부분 실행도 그대로 둔다 — 빼면 없던 일이 된다. */
function History({
  runs,
  jobs,
  currentRunId,
}: {
  readonly runs: readonly { id: string; summary_ko: string; is_complete: boolean }[];
  readonly jobs: readonly Job[];
  readonly currentRunId: string | null;
}) {
  const failed = jobs.filter(
    (job) => job.status.startsWith('FAILED') || job.is_stale || job.status === 'CANCELLED',
  );

  if (runs.length === 0 && failed.length === 0) {
    return <EmptyState description="아직 실행한 관측이 없습니다." />;
  }

  return (
    <Card title="지난 관측" headingLevel={3} tone="flat">
      <ul className={own.historyList}>
        {runs.map((run) => (
          <li key={run.id} className={own.historyRow}>
            <Link href={`/console/geo?run=${run.id}`} className={own.historyLink}>
              {run.summary_ko}
            </Link>
            {!run.is_complete ? <span className={own.partialTag}>부분 측정</span> : null}
            {run.id === currentRunId ? <span className={own.currentTag}>보는 중</span> : null}
          </li>
        ))}
        {failed.map((job) => (
          <li key={job.id} className={own.historyRow}>
            <span className={own.failedText}>
              {job.is_stale
                ? '진행 상황을 알 수 없는 실행 — 결과가 남지 않았을 수 있습니다'
                : (job.safe_error_message ?? '실행하지 못했습니다')}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
