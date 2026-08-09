'use client';

/**
 * 무료 네이버 키워드 조회 폼 — E3: "연결 안 됨" 껍데기를 실제 배선으로 교체.
 *
 * 화면이 지키는 것:
 * - 숫자를 만들지 않는다 — 값이 없으면 왜 없는지(비공개·최소 단위 미만·못 받음)를
 *   그대로 쓴다. 빈 값은 0 이 아니다.
 * - 엔진의 거절 사유("최대 5개까지" 등)는 엔진의 문장 그대로 보여준다.
 * - 조회 기록은 어디에도 저장하지 않는다 — 공개 표면의 경계 그대로.
 */

import { useState } from 'react';
import { formatCount } from '@veo/ui';

import type {
  KeywordFigure,
  KeywordLookupResult,
} from '@/lib/public-keywords-types';

import styles from './keyword-tool.module.css';

const ABSENT_LABELS: Record<string, string> = {
  SUPPRESSED_BY_PROVIDER: '비공개',
  BELOW_PROVIDER_THRESHOLD: '최소 단위 미만',
  MISSING: '값 없음',
};

function FigureCell({ figure }: { readonly figure: KeywordFigure }) {
  if (figure.value === null) {
    return (
      <td className={`${styles.num} ${styles.absent}`}>
        {ABSENT_LABELS[figure.quality] ?? '값 없음'}
      </td>
    );
  }
  const approximate = figure.quality === 'ROUNDED' || figure.quality === 'RANGE';
  return (
    <td className={styles.num}>
      {approximate ? '약 ' : ''}
      {formatCount(figure.value)}
    </td>
  );
}

function splitKeywords(raw: string): string[] {
  const parts = raw
    .split(/[,\n]/)
    .map((part) => part.trim())
    .filter((part) => part !== '');
  return [...new Set(parts)];
}

export function KeywordLookupForm() {
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KeywordLookupResult | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const keywords = splitKeywords(input);
    if (keywords.length === 0 || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/public-keyword-lookup', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ keywords }),
      });
      const body: unknown = await response.json().catch(() => null);
      const source =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setResult(null);
        setError(
          typeof source.message === 'string'
            ? source.message
            : '조회 중 문제가 발생했습니다. 다시 시도해 주십시오.',
        );
        return;
      }
      setResult((source.result as KeywordLookupResult | undefined) ?? null);
    } catch {
      setResult(null);
      setError('조회 중 문제가 발생했습니다. 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <form onSubmit={submit} aria-busy={busy}>
        <div className={styles.searchbar}>
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="예: 강남 피부과, 임플란트 가격"
            aria-label="조회할 키워드 (쉼표로 구분, 최대 5개)"
            disabled={busy}
          />
          <button type="submit" disabled={busy || splitKeywords(input).length === 0}>
            {busy ? '조회 중…' : '조회'}
          </button>
        </div>
        <p className={styles.hint}>쉼표로 구분해 한 번에 최대 5개까지 조회할 수 있습니다.</p>
      </form>

      {error !== null && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {result !== null && (
        <div>
          <div className={styles.tablewrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">키워드</th>
                  <th scope="col" className={styles.numHeader}>
                    월간 검색수 (전체)
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    PC
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    모바일
                  </th>
                  <th scope="col">경쟁 정도</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => (
                  <tr key={row.normalizedKeyword}>
                    <td className={styles.keywordCell}>
                      {row.keyword}
                      {row.normalizedKeyword !== row.keyword && (
                        <span className={styles.normalized}>
                          조회 기준: {row.normalizedKeyword}
                        </span>
                      )}
                    </td>
                    <FigureCell figure={row.total} />
                    <FigureCell figure={row.pc} />
                    <FigureCell figure={row.mobile} />
                    <td>{row.competitionLabel ?? <span className={styles.absent}>—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className={styles.notices}>
            {result.noticesKo.map((notice) => (
              <li key={notice}>{notice}</li>
            ))}
            {result.scopeNoticeKo !== '' && <li>{result.scopeNoticeKo}</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
