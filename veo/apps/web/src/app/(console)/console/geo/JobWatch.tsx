'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import styles from './geo.module.css';

interface JobView {
  readonly id: string;
  readonly status: string;
  readonly is_stale: boolean;
  readonly progress: number;
  readonly current_stage: string | null;
  readonly stages: readonly string[];
  readonly safe_error_message: string | null;
  readonly result_run_id: string | null;
  readonly note_ko: string;
}

const POLL_MS = 4_000;

const TERMINAL = new Set([
  'SUCCEEDED',
  'PARTIAL_SUCCESS',
  'FAILED_FINAL',
  'FAILED_RETRYABLE',
  'CANCELLED',
  'EXPIRED',
]);

/**
 * 도는 관측을 지켜본다.
 *
 * 이 컴포넌트가 조심하는 것 하나: **`status` 만 보고 그리지 않는다.** 서버가 재시작하면
 * 돌던 작업은 죽는데 행은 `RUNNING` 인 채 남는다. `is_stale` 이 참이면 그것이 아직
 * 도는지 우리도 모르고, 그때 "실행 중" 이라고 계속 돌려 주면 사용자는 오지 않을 결과를
 * 무한정 기다린다. 그래서 멈추고, 모른다고 말한다.
 */
export function JobWatch({ job: initial }: { readonly job: JobView }) {
  const router = useRouter();
  const [job, setJob] = useState(initial);

  const settled = TERMINAL.has(job.status) || job.is_stale;

  useEffect(() => {
    if (settled) return;

    let alive = true;
    const timer = setInterval(() => {
      void (async () => {
        try {
          const response = await fetch(`/api/observation?job=${encodeURIComponent(job.id)}`);
          if (!response.ok || !alive) return;
          const body: unknown = await response.json();
          const next =
            typeof body === 'object' && body !== null
              ? ((body as { job?: JobView }).job ?? null)
              : null;
          if (next === null || !alive) return;

          setJob(next);
          if (TERMINAL.has(next.status)) {
            // 결과가 생겼다. 서버 컴포넌트를 다시 그려 지표를 가져온다.
            router.refresh();
          }
        } catch {
          // 한 번 못 물어본 것은 실패가 아니다. 다음 주기에 다시 묻는다.
        }
      })();
    }, POLL_MS);

    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [job.id, settled, router]);

  if (job.is_stale) {
    return (
      <div className={styles.jobPanel} role="status">
        <p className={styles.jobHeadline}>진행 상황을 알 수 없습니다</p>
        <p className={styles.jobNote}>{job.note_ko}</p>
      </div>
    );
  }

  if (job.status === 'FAILED_FINAL' || job.status === 'FAILED_RETRYABLE') {
    return (
      <div className={styles.jobPanelFailed} role="status">
        <p className={styles.jobHeadline}>관측하지 못했습니다</p>
        <p className={styles.jobNote}>
          {job.safe_error_message ?? '원인을 확인할 수 없습니다.'}
        </p>
      </div>
    );
  }

  if (TERMINAL.has(job.status)) return null;

  const percent = Math.round(job.progress * 100);

  return (
    <div className={styles.jobPanel} role="status" aria-live="polite">
      <p className={styles.jobHeadline}>
        관측하는 중입니다 — {job.current_stage ?? '준비'} ({percent}%)
      </p>
      <div
        className={styles.progressTrack}
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="관측 진행률"
      >
        <div className={styles.progressFill} style={{ width: `${percent}%` }} />
      </div>
      <ol className={styles.stages}>
        {job.stages.map((stage) => (
          <li key={stage} className={stage === job.current_stage ? styles.stageNow : styles.stage}>
            {stage}
          </li>
        ))}
      </ol>
      <p className={styles.jobNote}>
        이 화면을 닫아도 실행은 계속됩니다. 나중에 다시 열어 결과를 보실 수 있습니다.
      </p>
    </div>
  );
}
