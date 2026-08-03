'use client';

/**
 * 원고 검수 폼 (P2-11).
 *
 * 화면이 지키는 것:
 * - 발견마다 걸린 구절·유형·근거 조항·확인할 일이 함께 나온다 — 식별자만 주면
 *   사람이 할 수 있는 일이 없다.
 * - 서버의 면책 문구를 그대로 싣는다 — 이 도구가 무엇이 아닌지가 무엇인지만큼 중요하다.
 * - 발견이 없으면 "표시할 것이 없었다"고 말하지 "적법하다"고 말하지 않는다.
 */

import { useState } from 'react';

import styles from './medical.module.css';

interface Finding {
  readonly rule_id: string;
  readonly category_ko: string;
  readonly guidance_ko: string;
  readonly reference_ko: string;
  readonly excerpt: string;
  readonly offset: number | null;
}

interface ReviewResult {
  readonly findings: readonly Finding[];
  readonly disclaimer_ko: string;
  readonly reviewed_chars: number;
}

export function CopyReviewForm() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReviewResult | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || text.trim() === '') return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/medical-review', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const body: unknown = await response.json().catch(() => null);
      const source =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setResult(null);
        setError(
          typeof source.message === 'string' ? source.message : '검수하지 못했습니다.',
        );
        return;
      }
      setResult((source.result as ReviewResult | undefined) ?? null);
    } catch {
      setResult(null);
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <form onSubmit={submit}>
        <textarea
          className={styles.editor}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="검수할 원고를 붙여 넣으십시오 (블로그 글·페이지 문안 등)"
          aria-label="검수할 원고"
          rows={12}
          disabled={busy}
        />
        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={busy || text.trim() === ''}>
            {busy ? '검수 중…' : '검수'}
          </button>
          {error !== null && (
            <span role="alert" className={styles.error}>
              {error}
            </span>
          )}
        </div>
      </form>

      {result !== null && (
        <section className={styles.results} aria-label="검수 결과">
          {result.findings.length === 0 ? (
            <p className={styles.clean}>
              {result.reviewed_chars.toLocaleString('ko-KR')}자에서 표시할 표현을 찾지
              못했습니다 — 이것이 적법하다는 뜻은 아닙니다. 아래 안내를 확인하십시오.
            </p>
          ) : (
            <>
              <h2 className={styles.resultTitle}>
                검토 필요 {result.findings.length}곳
              </h2>
              <ol className={styles.findingList}>
                {result.findings.map((finding, index) => (
                  <li key={`${finding.rule_id}-${finding.offset ?? 'absence'}-${index}`}>
                    <article className={styles.finding}>
                      <p className={styles.findingHead}>
                        <span className={styles.category}>{finding.category_ko}</span>
                        <span className={styles.reference}>{finding.reference_ko}</span>
                      </p>
                      <p className={styles.excerpt}>{finding.excerpt}</p>
                      <p className={styles.guidance}>{finding.guidance_ko}</p>
                    </article>
                  </li>
                ))}
              </ol>
            </>
          )}
          <p className={styles.disclaimer}>{result.disclaimer_ko}</p>
        </section>
      )}
    </div>
  );
}
