'use client';

import { useState, type FormEvent } from 'react';
import { Button, FormError } from '@veo/ui';

import type { KeywordLookup } from '@/lib/keywords';

import { KeywordReport } from './KeywordReport';
import styles from './keywords.module.css';

/**
 * 키워드 입력 칸.
 *
 * 결과를 주소창이 아니라 폼이 들고 있는다. 조회는 네이버 공식 API 를 실제로 부르는
 * 일이라, 화면을 새로 열 때마다 다시 부르면 안 된다 — 화면을 여는 일과 새로 조회하는
 * 일을 갈라 둔다.
 */
export function LookupForm() {
  const [keywords, setKeywords] = useState('');
  const [lookup, setLookup] = useState<KeywordLookup | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const count = keywords
    .split(/[\n,]/)
    .map((one) => one.trim())
    .filter((one) => one !== '').length;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError(null);
    setLookup(null);
    try {
      const response = await fetch('/api/keyword-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

      if (!response.ok) {
        setError(
          typeof record['message'] === 'string' ? record['message'] : '조회하지 못했습니다.',
        );
        return;
      }
      setLookup((record['lookup'] ?? null) as KeywordLookup | null);
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form className={styles.form} onSubmit={submit} noValidate>
        <label className={styles.label} htmlFor="keywords">
          조회할 키워드
        </label>
        <textarea
          id="keywords"
          className={styles.textarea}
          value={keywords}
          onChange={(event) => setKeywords(event.target.value)}
          placeholder={'강남 한의원\n허리디스크 치료\n교통사고 한방병원'}
          rows={5}
        />
        <p className={styles.hint}>
          줄바꿈이나 쉼표로 구분합니다. 한 번에 최대 20개까지 조회하며, 그 수만큼 네이버에
          요청을 보냅니다.
        </p>
        <Button type="submit" busy={busy}>
          {busy ? '조회 중…' : count === 0 ? '조회' : `${count}개 조회`}
        </Button>
        <FormError message={error} />
      </form>
      {lookup === null ? null : <KeywordReport lookup={lookup} />}
    </>
  );
}
