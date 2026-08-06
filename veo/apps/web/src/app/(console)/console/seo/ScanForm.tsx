'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import styles from './seo.module.css';

/**
 * 이 사이트가 몇 초쯤 걸릴지. **페이지 수를 모르면 추정하지 않는다.**
 *
 * 예전에는 사이트와 무관하게 120초 고정이었다. 154페이지짜리 거래처를 재는 동안
 * 화면이 "예상(120초)보다 오래 걸리고 있습니다" 를 띄웠고, 사장님이 "무슨 문제지?"
 * 라고 물었다 — 정상 동작인데 고장으로 읽힌 것이다. 틀린 추정은 없느니만 못하다.
 *
 * 실측 근거(2026-08-07, venomad.com 154페이지, 워커): 총 154초 =
 * 수집 84.6 · 성능 측정 35.7 · 채점 20.9 · 저장 2.1. 수집이 장당 0.55초쯤이고
 * 나머지가 60초 안팎이라 `60 + 페이지수 × 0.6` 이 154페이지에서 152초로 맞는다.
 *
 * 처음 재는 사이트는 페이지 수를 **재기 전에는 알 수 없다.** 그때는 숫자를 지어내지
 * 않고 "얼마나 걸릴지는 페이지 수에 달렸다" 고 말한다.
 */
function estimateSeconds(expectedPages: number | undefined): number | null {
  if (expectedPages === undefined || expectedPages <= 0) return null;
  return Math.round(60 + expectedPages * 0.6);
}

function phaseFor(elapsed: number): string {
  if (elapsed < 10) return '페이지를 가져오는 중';
  if (elapsed < 70) return '사이트 전체를 크롤하는 중';
  return '성능 실측 중 (페이지당 16~60초)';
}

const POLL_MS = 4_000;

/**
 * 진행을 이만큼 연달아 못 물어보면 그만둔다.
 *
 * 예전에는 물어보기가 실패하면 그냥 `continue` 였다 — 탈출구가 없었다. 로그인이
 * 풀리거나 서버가 답을 못 주면 화면은 **영원히** 돌았고, 사용자는 오지 않을 결과를
 * 기다렸다. 죽은 작업을 "실행 중" 으로 보여주지 않겠다고 `is_stale` 까지 만들어 놓고,
 * 그 신호를 받으러 가는 길이 막히면 아무 소용이 없다.
 *
 * 15회 × 4초 = 1분. 잠깐의 네트워크 끊김은 넘기고, 진짜 고장은 1분 안에 말한다.
 */
const MAX_CONSECUTIVE_FAILURES = 15;

const TERMINAL = new Set([
  'SUCCEEDED',
  'PARTIAL_SUCCESS',
  'FAILED_FINAL',
  'FAILED_RETRYABLE',
  'CANCELLED',
  'EXPIRED',
]);

interface JobView {
  readonly status: string;
  readonly is_stale: boolean;
  readonly current_stage: string | null;
  readonly safe_error_message: string | null;
  readonly result_run_id: string | null;
  readonly note_ko: string;
}

function jobFrom(body: unknown): JobView | null {
  if (typeof body !== 'object' || body === null) return null;
  const job = (body as { job?: unknown }).job;
  return typeof job === 'object' && job !== null ? (job as JobView) : null;
}

/**
 * 진단이 도는 동안 오른쪽 빈칸을 채우는 진행 표시.
 *
 * "남은 시간" 은 추정이고 추정이라고 말한다(약 N초). **근거가 없으면 아예 말하지
 * 않는다** — 지난번 페이지 수를 모르는 첫 진단에서는 숫자도 고리도 내보내지 않는다.
 * 추정을 넘기면 0초에서 멈춘 채 거짓말하는 대신 "예상보다 오래 걸리고 있다" 로
 * 바꿔 말한다.
 */
function ScanProgress({
  stage,
  expectedPages,
}: {
  readonly stage: string | null;
  /** 지난번에 이 사이트에서 실제로 수집한 페이지 수. 처음 재는 곳이면 없다. */
  readonly expectedPages?: number;
}) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const estimate = estimateSeconds(expectedPages);
  const remaining = estimate === null ? null : estimate - elapsed;
  // 추정이 없으면 고리를 채우지 않는다 — 채울 근거가 없는데 채우면 그림이 거짓말한다.
  const degrees = estimate === null ? 0 : Math.round(Math.min(1, elapsed / estimate) * 360);

  return (
    <aside className={styles.scanProgress} role="status" aria-live="polite">
      <div
        className={styles.scanProgressRing}
        style={{
          background: `conic-gradient(var(--veo-color-accent) ${degrees}deg, var(--veo-color-bg-subtle) ${degrees}deg 360deg)`,
        }}
      >
        <div className={styles.scanProgressHole}>
          <b>{elapsed}</b>
          <span>초 경과</span>
        </div>
      </div>
      {/* 서버가 말한 단계가 있으면 그것이 사실이고, 없으면 경과 기반 추정이다. */}
      <p className={styles.scanProgressPhase}>{stage ?? phaseFor(elapsed)}</p>
      <p className={styles.scanProgressEta}>
        {estimate === null
          ? '얼마나 걸릴지는 페이지 수에 달렸습니다 — 처음 재는 곳이라 아직 알 수 없습니다. 끝나면 자동으로 열립니다.'
          : remaining !== null && remaining > 0
            ? `남은 시간 약 ${remaining}초 (지난번 ${expectedPages}페이지 기준)`
            : `예상(${estimate}초)보다 오래 걸리고 있습니다 — 지난번보다 페이지가 늘었을 수 있습니다. 작업은 계속 돌고 있고, 끝나면 자동으로 열립니다.`}
      </p>
    </aside>
  );
}

/**
 * 주소 한 칸.
 *
 * 업체를 먼저 등록하게 하지 않는다 — 영업 중에 주소 하나를 넣어 보는 것이 이 도구의 첫
 * 쓰임인데, 그 앞에 등록 절차를 세우면 쓰지 않게 된다. 넣으면 잰다. 저장은 결과가 나온
 * 뒤 주소를 기준으로 알아서 된다.
 */
export function ScanForm({
  siteId,
  expectedPages,
  pollMs = POLL_MS,
}: {
  readonly siteId?: string;
  /** 지난번에 이 사이트에서 실제로 수집한 페이지 수 — 소요 시간 추정의 유일한 근거다. */
  readonly expectedPages?: number;
  /** 시험에서만 줄인다 — 성질은 주기와 무관하다. */
  readonly pollMs?: number;
}) {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rescan = siteId !== undefined;

  /** 작업이 끝날 때까지 진행을 물어본다. 끝난 방식에 맞는 다음 행동을 돌려준다. */
  async function watch(jobId: string, nextSiteId: string): Promise<void> {
    let failures = 0;

    for (;;) {
      await new Promise((resolve) => window.setTimeout(resolve, pollMs));
      let job: JobView | null = null;
      try {
        const response = await fetch(`/api/scan?job=${encodeURIComponent(jobId)}`);
        if (response.status === 401 || response.status === 403) {
          // 다시 물어봐야 계속 같은 답이다. 사용자가 할 일을 바로 말해 준다.
          setError('로그인이 풀렸습니다. 다시 로그인하시면 진행 상황을 볼 수 있습니다.');
          return;
        }
        if (response.ok) {
          job = jobFrom(await response.json().catch(() => null));
        }
      } catch {
        // 한 번 못 물어본 것은 실패가 아니다 — 아래에서 세고 넘어간다.
      }

      if (job === null) {
        failures += 1;
        if (failures >= MAX_CONSECUTIVE_FAILURES) {
          // 여기가 없으면 화면이 영원히 돈다. 진단 자체는 서버에서 계속 돌 수 있으므로
          // "실패했다" 가 아니라 "물어볼 수 없다" 라고 말한다(0-A).
          setError(
            '진행 상황을 물어볼 수 없습니다. 진단은 서버에서 계속 돌고 있을 수 있으니, ' +
              '잠시 후 이 화면을 새로 고쳐 결과가 있는지 확인해 주십시오.',
          );
          return;
        }
        continue;
      }
      failures = 0;

      setStage(job.current_stage);

      if (job.is_stale) {
        // 서버가 재시작해 돌던 작업의 소식이 끊겼다 — "실행 중"인 척하지 않는다.
        setError(job.note_ko || '진행 상황을 알 수 없습니다. 다시 측정해 주십시오.');
        return;
      }
      if (!TERMINAL.has(job.status)) continue;

      if (job.status === 'SUCCEEDED' || job.status === 'PARTIAL_SUCCESS') {
        const run = job.result_run_id;
        router.push(
          run === null
            ? `/console/seo?site=${nextSiteId}`
            : `/console/seo?site=${nextSiteId}&run=${run}`,
        );
        router.refresh();
        return;
      }
      setError(job.safe_error_message ?? '진단하지 못했습니다.');
      return;
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setStage(null);
    setError(null);
    try {
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rescan ? { siteId } : { url }),
      });
      const body: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        const message =
          typeof body === 'object' && body !== null && 'message' in body
            ? String((body as { message: unknown }).message)
            : '진단하지 못했습니다.';
        setError(message);
        return;
      }

      const parsed =
        typeof body === 'object' && body !== null
          ? (body as { siteId?: unknown; jobId?: unknown })
          : {};
      const nextSiteId = typeof parsed.siteId === 'string' ? parsed.siteId : siteId;
      const jobId = typeof parsed.jobId === 'string' ? parsed.jobId : null;

      if (nextSiteId === undefined) {
        setError('진단하지 못했습니다.');
        return;
      }
      if (jobId === null) {
        // 작업 표를 못 받은 옛 응답 — 저장은 됐을 수 있으므로 화면만 새로 연다.
        router.push(`/console/seo?site=${nextSiteId}`);
        router.refresh();
        return;
      }
      await watch(jobId, nextSiteId);
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={busy ? styles.scanFormRow : undefined}>
      <form className={styles.scanForm} onSubmit={submit} noValidate>
        {rescan ? null : (
          <TextField
            label="측정할 주소"
            name="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="ondam.co.kr"
            hint="주소창에서 복사해 붙여 넣으셔도 됩니다. 결과는 자동으로 저장됩니다."
            inputMode="url"
            required
          />
        )}
        <Button type="submit" busy={busy}>
          {busy ? '진단 중…' : rescan ? '다시 측정' : '진단'}
        </Button>
        <FormError message={error} />
      </form>
      {busy ? <ScanProgress stage={stage} expectedPages={expectedPages} /> : null}
    </div>
  );
}
