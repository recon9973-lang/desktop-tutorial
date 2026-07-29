'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';
import { Button, FormError, TextField } from '@veo/ui';

import styles from './seo.module.css';

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
  );
}
