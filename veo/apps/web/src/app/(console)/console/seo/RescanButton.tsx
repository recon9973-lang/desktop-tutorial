'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button, FormError } from '@veo/ui';

/**
 * 재측정.
 *
 * 화면을 열 때는 다시 재지 않는다. 이 버튼을 누를 때만 실제로 대상 사이트를 가져온다 —
 * 사람이 "변경을 확인하겠다" 고 결정한 순간이다.
 */
export function RescanButton({ siteId }: { readonly siteId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ siteId }),
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
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Button onClick={run} busy={busy}>
        {busy ? '진단 중…' : '진단 실행'}
      </Button>
      <FormError message={error} />
    </div>
  );
}
