'use client';

import { useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import type { GeoReadiness } from '@/lib/observations';

import { ReadinessReport } from './ReadinessReport';
import styles from './geo.module.css';

/**
 * 주소 한 칸.
 *
 * 이 진단은 SEO 진단과 **같은 수집 경로**를 쓴다. 한 번 가져온 것으로 둘 다 잴 수
 * 있어야 대상 사이트에 두 번 요청하지 않는다.
 */
export function ReadinessForm() {
  const [url, setUrl] = useState('');
  const [report, setReport] = useState<GeoReadiness | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError(null);
    setReport(null);
    try {
      const response = await fetch('/api/geo-readiness', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

      if (!response.ok) {
        setError(
          typeof record['message'] === 'string' ? record['message'] : '진단하지 못했습니다.',
        );
        return;
      }
      setReport((record['report'] ?? null) as GeoReadiness | null);
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
    <form className={styles.runForm} onSubmit={submit} noValidate>
      <TextField
        label="측정할 주소"
        name="url"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="ondam.co.kr"
        hint="사이트맵과 내부 링크를 따라 여러 장을 가져옵니다. 한 장만 보면 사이트 전체를 봐야 판정되는 항목이 측정 불가로 남습니다."
        inputMode="url"
        required
      />
      <Button type="submit" busy={busy}>
        {busy ? '진단 중…' : '준비도 진단'}
      </Button>
      <FormError message={error} />
    </form>
    {report === null ? null : <ReadinessReport report={report} />}
    </>
  );
}
