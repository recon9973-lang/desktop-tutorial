'use client';

/**
 * 거래처 전달 링크 (P2-10a) — 버전 하나를 로그인 없이 열리는 주소로.
 *
 * 화면이 지키는 것: 링크는 **복사본의 발행**이라는 사실이 문구로 보인다 — 지금 이
 * 순간의 문서가 굳고, 이후 재발행해도 이 링크의 내용은 바뀌지 않는다(엔진의 문장
 * 그대로). 만료일도 함께 보여 잊힌 링크가 영원한 척하지 않는다.
 */

import { useState } from 'react';

import styles from '../reports.module.css';

interface ShareResult {
  readonly url: string;
  readonly expiresAt: string | null;
  readonly noteKo: string | null;
}

export function ShareLinkButton({
  reportId,
  version,
}: {
  readonly reportId: string;
  readonly version: number;
}) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ShareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function share(): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/report-share', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ reportId, version }),
      });
      const body: unknown = await response.json().catch(() => null);
      const source =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok || typeof source.url !== 'string') {
        setError(
          typeof source.message === 'string' ? source.message : '공유 링크를 만들지 못했습니다.',
        );
        return;
      }
      setResult({
        url: source.url,
        expiresAt: typeof source.expiresAt === 'string' ? source.expiresAt : null,
        noteKo: typeof source.noteKo === 'string' ? source.noteKo : null,
      });
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  if (result !== null) {
    return (
      <span className={styles.shareResult}>
        <code className={styles.shareUrl}>{result.url}</code>
        <button
          type="button"
          className={styles.versionExport}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(result.url);
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1600);
            } catch {
              // 클립보드 권한이 없으면 조용히 둔다 — 주소는 화면에 있으니 직접 긁으면 된다.
            }
          }}
        >
          {copied ? '복사됨 ✓' : '주소 복사'}
        </button>
        <span className={styles.shareNote}>
          {formatExpiry(result.expiresAt)}
          {result.noteKo === null ? '' : ` · ${result.noteKo}`}
        </span>
      </span>
    );
  }

  return (
    <>
      <button
        type="button"
        className={styles.versionExport}
        onClick={share}
        disabled={busy}
      >
        {busy ? '링크 만드는 중…' : '거래처 전달 링크'}
      </button>
      {error === null ? null : (
        <span role="alert" className={styles.shareError}>
          {error}
        </span>
      )}
    </>
  );
}

function formatExpiry(iso: string | null): string {
  if (iso === null) return '';
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return '';
  const formatted = new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeZone: 'Asia/Seoul',
  }).format(at);
  return `${formatted}까지 열립니다`;
}
