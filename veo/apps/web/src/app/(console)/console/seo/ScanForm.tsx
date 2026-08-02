'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import styles from './seo.module.css';

/**
 * 통상 소요 시간(초). 약속이 아니라 추정이다 — 실측 근거: 전체 크롤(최대 200장)
 * 수십 초 + 성능 실측 상위 5장(장당 16~60초, 2026-08-01 실측). 서버 타임아웃은
 * 240초이므로 그보다 크게 말하지 않는다.
 */
const TYPICAL_SECONDS = 120;
const HARD_LIMIT_SECONDS = 240;

function phaseFor(elapsed: number): string {
  if (elapsed < 10) return '페이지를 가져오는 중';
  if (elapsed < 70) return '사이트 전체를 크롤하는 중 (최대 200장)';
  return '성능 실측 중 (페이지당 16~60초)';
}

/**
 * 진단이 도는 동안 오른쪽 빈칸을 채우는 진행 표시.
 *
 * "남은 시간" 은 추정이고 추정이라고 말한다(약 N초). 추정을 넘기면 0초에서 멈춘
 * 채 거짓말하는 대신 "예상보다 오래 걸리고 있다" 로 바꿔 말한다 — 페이지 수는
 * 사이트마다 다르고, 우리는 재기 전에 그 수를 모른다.
 */
function ScanProgress() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const remaining = TYPICAL_SECONDS - elapsed;
  const ratio = Math.min(1, elapsed / TYPICAL_SECONDS);
  const degrees = Math.round(ratio * 360);

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
      <p className={styles.scanProgressPhase}>{phaseFor(elapsed)}</p>
      <p className={styles.scanProgressEta}>
        {remaining > 0
          ? `남은 시간 약 ${remaining}초`
          : `예상(${TYPICAL_SECONDS}초)보다 오래 걸리고 있습니다 — 페이지가 많은 사이트입니다 (최대 ${HARD_LIMIT_SECONDS}초)`}
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
export function ScanForm({ siteId }: { readonly siteId?: string }) {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rescan = siteId !== undefined;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
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

      const next =
        typeof body === 'object' && body !== null && 'siteId' in body
          ? String((body as { siteId: unknown }).siteId)
          : siteId;

      if (next !== undefined && next !== siteId) {
        router.push(`/console/seo?site=${next}`);
        return;
      }
      router.refresh();
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
      {busy ? <ScanProgress /> : null}
    </div>
  );
}
