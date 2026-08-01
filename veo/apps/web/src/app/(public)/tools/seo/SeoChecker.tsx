'use client';

/**
 * 공개 SEO 진단 — 확정 시안(2026-08-02)의 구현.
 *
 * 구조는 시안 그대로: 점수 밴드(게이지 + 단계 카드)를 상단 전폭에, 아래 한 컬럼
 * 체크리스트, 각 항목은 `details` 로 접혀 있고 열면 이유·조치 코드·담당이 나온다.
 *
 * 화면이 지키는 것:
 * - 숫자를 만들지 않는다 — 점수·이득(+N점)·카운트 전부 서버 산식 값 그대로.
 * - 통과와 측정 불가를 섞지 않는다 — 측정 불가는 회색 물음표, 이유가 함께 나온다.
 * - 점수 밖 영역(연동 필요 등)은 갈라 그린다 — 순위와 무관한 일을 하고 점수가
 *   오르는 착시를 만들지 않는다.
 * - GEO 는 숫자를 지어내지 않는다 — 같은 주소로 GEO 진단을 여는 링크만 둔다.
 */

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

import type { ScanCheckRow, ScanResult, ScanVerdict } from '@/lib/scan-api-types';

import styles from './seo-checker.module.css';

type Filter = 'ALL' | ScanVerdict;

interface ScanError {
  readonly message: string;
}

const VERDICT_ICON: Record<ScanVerdict, { readonly mark: string; readonly className: string; readonly label: string }> = {
  FAIL: { mark: '✕', className: styles.iconFail ?? '', label: '실패' },
  WARNING: { mark: '–', className: styles.iconWarn ?? '', label: '주의' },
  PASS: { mark: '✓', className: styles.iconPass ?? '', label: '통과' },
  UNKNOWN: { mark: '?', className: styles.iconNa ?? '', label: '측정 불가' },
  NOT_APPLICABLE: { mark: '·', className: styles.iconNa ?? '', label: '해당 없음' },
};

function gaugeStyle(score: number | null): React.CSSProperties {
  const ratio = score === null ? 0 : Math.max(0, Math.min(100, score)) / 100;
  const degrees = ratio * 180;
  return {
    background: `conic-gradient(from 270deg, var(--veo-status-fail-border) 0 ${degrees}deg, var(--veo-color-border) ${degrees}deg 180deg, transparent 180deg 360deg)`,
  };
}

export function SeoChecker() {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ScanError | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [filter, setFilter] = useState<Filter>('ALL');
  const reportRef = useRef<HTMLDivElement | null>(null);

  // 인쇄(PDF 저장) 직전에 접힌 항목을 전부 연다 — 닫힌 details 는 인쇄되지 않는다.
  useEffect(() => {
    const openAll = () => {
      reportRef.current
        ?.querySelectorAll('details')
        .forEach((element) => element.setAttribute('open', ''));
    };
    window.addEventListener('beforeprint', openAll);
    return () => window.removeEventListener('beforeprint', openAll);
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || url.trim() === '') {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/public-scan', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), kind: 'SEO' }),
      });
      const body: unknown = await response.json();
      const record = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setResult(null);
        setError({
          message:
            typeof record.message === 'string'
              ? record.message
              : '진단 중 문제가 발생했습니다. 다시 시도해 주십시오.',
        });
        return;
      }
      setResult(record.result as ScanResult);
      setFilter('ALL');
    } catch {
      setResult(null);
      setError({ message: '진단 중 연결이 끊겼습니다. 다시 시도해 주십시오.' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <form className={styles.hero} onSubmit={submit}>
        <h1 className={styles.heroTitle}>SEO·GEO 점수 체크</h1>
        <p className={styles.heroSub}>
          주소 하나면 됩니다 — 검색엔진과 AI 답변 엔진이 이 페이지를 읽을 수 있는지 확인합니다
        </p>
        <div className={styles.searchbar}>
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.co.kr"
            aria-label="진단할 주소"
            inputMode="url"
            autoComplete="url"
          />
          <button type="submit" disabled={busy}>
            {busy ? '진단 중…' : '진단하기'}
          </button>
        </div>
        <div className={styles.modes} role="tablist" aria-label="진단 종류">
          <span className={`${styles.mode} ${styles.modeOn}`} role="tab" aria-selected="true">
            SEO 점수
          </span>
          <Link className={styles.mode} href="/tools/geo" role="tab" aria-selected="false">
            GEO 점수
          </Link>
        </div>
        {busy ? (
          <p className={styles.progress} role="status">
            페이지를 가져와 검사하는 중입니다 — 보통 10~30초 걸립니다.
          </p>
        ) : null}
        {error ? (
          <p className={styles.error} role="alert">
            {error.message}
          </p>
        ) : null}
      </form>

      {result ? <Report result={result} filter={filter} onFilter={setFilter} reportRef={reportRef} /> : null}
    </div>
  );
}

function Report({
  result,
  filter,
  onFilter,
  reportRef,
}: {
  readonly result: ScanResult;
  readonly filter: Filter;
  readonly onFilter: (next: Filter) => void;
  readonly reportRef: React.RefObject<HTMLDivElement | null>;
}) {
  const quality =
    result.score.value === null || result.reach === 0
      ? null
      : result.score.value / result.reach;

  return (
    <div ref={reportRef}>
      <section className={styles.scoreband} aria-label="점수 요약">
        <div>
          <div className={styles.gauge}>
            <div className={styles.gaugeArc} style={gaugeStyle(result.score.value)} />
            <div className={styles.gaugeHole} />
            <div className={styles.gaugeVal}>
              <b>{result.score.value === null ? '—' : result.score.value.toFixed(1)}</b>
              <span>SEO 준비도</span>
            </div>
          </div>
          <div className={styles.gaugeSub}>
            {result.score.bandLabel ? (
              <span className={styles.bandChip}>{result.score.bandLabel}</span>
            ) : (
              <span className={styles.bandChip}>측정 불가</span>
            )}
            {result.score.value !== null && quality !== null ? (
              <div>
                도달률 <b className={styles.mono}>{result.reach.toFixed(2)}</b> × 품질{' '}
                <b className={styles.mono}>{quality.toFixed(1)}</b>
              </div>
            ) : null}
            <button type="button" className={styles.pdfButton} onClick={() => window.print()}>
              ⬇ PDF 보고서
            </button>
          </div>
        </div>

        <div className={styles.twincol}>
          <div className={`${styles.twin} ${styles.twinOn}`}>
            <span>
              <span className={styles.twinLabel}>SEO</span>
              <span className={styles.twinSub}>검색엔진 준비도</span>
            </span>
            <b className={styles.mono}>
              {result.score.value === null ? '—' : result.score.value.toFixed(1)}
            </b>
          </div>
          <Link className={styles.twin} href="/tools/geo">
            <span>
              <span className={styles.twinLabel}>GEO</span>
              <span className={styles.twinSub}>같은 주소로 AI 답변 엔진 준비도 확인 →</span>
            </span>
          </Link>
        </div>

        <ul className={styles.stagegrid} aria-label="검색 여정 단계별 점수">
          {result.stages.map((stage) => (
            <li key={stage.categoryId} className={stage.isGate ? styles.stageGate : styles.stage}>
              <span className={styles.stageName}>
                {stage.name}
                {stage.isGate ? <small> · 관문</small> : null}
              </span>
              <span className={styles.stageTrack}>
                <i style={{ width: `${stage.score ?? 0}%` }} />
              </span>
              <span className={`${styles.stageValue} ${styles.mono}`}>
                {stage.score === null ? '—' : Math.round(stage.score)}
                <small>/100</small>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <div className={styles.body}>
        <p className={styles.scope}>{result.scopeNotice}</p>

        <div className={styles.filters} role="group" aria-label="상태별 필터">
          <FilterChip current={filter} value="ALL" onFilter={onFilter} label="전체" count={result.checks.length} />
          <FilterChip current={filter} value="FAIL" onFilter={onFilter} label="실패" count={result.counts.failed} />
          <FilterChip current={filter} value="WARNING" onFilter={onFilter} label="주의" count={result.counts.warned} />
          <FilterChip current={filter} value="PASS" onFilter={onFilter} label="통과" count={result.counts.passed} />
          <FilterChip
            current={filter}
            value="UNKNOWN"
            onFilter={onFilter}
            label="측정 불가"
            count={result.counts.unknown}
          />
        </div>

        {result.previews && filter === 'ALL' ? <Previews result={result} /> : null}

        <CheckSections checks={result.checks} filter={filter} />

        <div className={styles.cta}>
          <span>
            <b>전체 사이트 진단 — 최대 200장</b>
            <span className={styles.ctaSub}>
              페이지 간 중복·고아 페이지·깨진 링크까지 판정하고, 어느 페이지가 문제인지
              목록으로 드립니다
            </span>
          </span>
          <Link href="/login" className={styles.ctaButton}>
            콘솔에서 진단하기
          </Link>
        </div>
      </div>
    </div>
  );
}

function FilterChip({
  current,
  value,
  onFilter,
  label,
  count,
}: {
  readonly current: Filter;
  readonly value: Filter;
  readonly onFilter: (next: Filter) => void;
  readonly label: string;
  readonly count: number;
}) {
  const on = current === value;
  return (
    <button
      type="button"
      className={on ? `${styles.filterChip} ${styles.filterOn}` : styles.filterChip}
      aria-pressed={on}
      onClick={() => onFilter(value)}
    >
      {label} <span className={styles.mono}>{count}</span>
    </button>
  );
}

function Previews({ result }: { readonly result: ScanResult }) {
  const previews = result.previews;
  if (previews === null) {
    return null;
  }
  let host = result.targetUrl;
  try {
    host = new URL(result.targetUrl).host;
  } catch {
    // 주소가 이상하면 원문 그대로 둔다 — 미리보기가 죽을 이유는 아니다.
  }
  return (
    <div className={styles.previews}>
      <div className={styles.preview}>
        <h3>
          구글 검색결과 미리보기 <span className={styles.previewSource}>SERP</span>
        </h3>
        <div className={styles.serp}>
          <div className={styles.serpUrl}>{host}</div>
          <div className={styles.serpTitle}>{previews.serpTitle ?? '(제목 없음)'}</div>
          <div className={styles.serpDescription}>
            {previews.serpDescription ?? (
              <i>메타 설명이 없어 구글이 본문을 무작위로 잘라 씁니다</i>
            )}
          </div>
        </div>
      </div>
      <div className={styles.preview}>
        <h3>
          카카오톡 공유 미리보기 <span className={styles.previewSource}>OG</span>
        </h3>
        <div className={styles.kakao}>
          <div className={styles.kakaoImage}>
            {previews.hasOgImage ? '공유 이미지 있음' : 'og:image 없음'}
          </div>
          <div className={styles.kakaoBody}>
            <div className={styles.kakaoTitle}>{previews.ogTitle ?? host}</div>
            <div className={styles.kakaoDescription}>
              {previews.ogDescription ?? '설명 없음'}
            </div>
            <div className={styles.kakaoUrl}>{host}</div>
          </div>
        </div>
        {!previews.ogTitle || !previews.hasOgImage ? (
          <p className={styles.previewNote}>
            ✕ 공유 태그가 부족합니다 — 공유 시 빈 카드로 보입니다
          </p>
        ) : null}
      </div>
    </div>
  );
}

interface Section {
  readonly categoryId: string;
  readonly categoryName: string;
  readonly outsideScore: boolean;
  readonly rows: ScanCheckRow[];
}

function toSections(checks: readonly ScanCheckRow[]): Section[] {
  const sections: Section[] = [];
  const byId = new Map<string, Section>();
  for (const row of checks) {
    let section = byId.get(row.categoryId);
    if (section === undefined) {
      section = {
        categoryId: row.categoryId,
        categoryName: row.categoryName,
        outsideScore: row.outsideScore,
        rows: [],
      };
      byId.set(row.categoryId, section);
      sections.push(section);
    }
    section.rows.push(row);
  }
  // 섹션 안에서는 고칠 것이 먼저 — 실패, 주의, 측정 불가, 통과, 해당 없음 순.
  const order: Record<ScanVerdict, number> = {
    FAIL: 0,
    WARNING: 1,
    UNKNOWN: 2,
    PASS: 3,
    NOT_APPLICABLE: 4,
  };
  for (const section of sections) {
    section.rows.sort(
      (a, b) => order[a.verdict] - order[b.verdict] || a.checkId.localeCompare(b.checkId),
    );
  }
  return sections;
}

function CheckSections({
  checks,
  filter,
}: {
  readonly checks: readonly ScanCheckRow[];
  readonly filter: Filter;
}) {
  const sections = toSections(checks);
  return (
    <>
      {sections.map((section) => {
        const rows =
          filter === 'ALL'
            ? section.rows
            : section.rows.filter((row) => row.verdict === filter);
        if (rows.length === 0) {
          return null;
        }
        const failed = section.rows.filter((row) => row.verdict === 'FAIL').length;
        const warned = section.rows.filter((row) => row.verdict === 'WARNING').length;
        return (
          <section key={section.categoryId} className={styles.checkSection}>
            <h2 className={styles.sectionHead}>
              {section.categoryName}
              {section.outsideScore ? (
                <span className={styles.tagOut}>점수 밖 · 연동 필요</span>
              ) : failed + warned > 0 ? (
                <span className={styles.tagBad}>
                  {failed > 0 ? `실패 ${failed}` : ''}
                  {failed > 0 && warned > 0 ? ' · ' : ''}
                  {warned > 0 ? `주의 ${warned}` : ''}
                </span>
              ) : (
                <span className={styles.tagOk}>통과</span>
              )}
            </h2>
            {rows.map((row) => (
              <CheckItem key={row.checkId} row={row} />
            ))}
          </section>
        );
      })}
    </>
  );
}

function CheckItem({ row }: { readonly row: ScanCheckRow }) {
  const icon = VERDICT_ICON[row.verdict];
  const hasDetail = Boolean(row.note || row.codeExample);
  const gain =
    row.blockedByCap && row.verdict !== 'PASS'
      ? '상한에 막힘'
      : row.gainPoints !== null && row.gainPoints > 0
        ? `+${row.gainPoints.toFixed(1)}점`
        : null;

  const summary = (
    <>
      <span className={`${styles.icon} ${icon.className}`} aria-hidden="true">
        {icon.mark}
      </span>
      <span className={styles.itemBody}>
        <span className={styles.itemTitle}>
          <span className={styles.srOnly}>{icon.label}: </span>
          {row.title}
        </span>
        {row.note ? <span className={styles.itemNote}>{row.note}</span> : null}
      </span>
      <span className={styles.itemRight}>
        {gain ? <span className={styles.gain}>{gain}</span> : null}
        {row.outsideScore ? <span className={styles.gainZero}>점수 밖</span> : null}
      </span>
    </>
  );

  if (!hasDetail) {
    return <div className={styles.itemStatic}>{summary}</div>;
  }

  return (
    <details className={styles.item}>
      <summary>
        {summary}
        <span className={styles.moreButton} aria-hidden="true">
          <span className={styles.moreClosed}>더보기 ▾</span>
          <span className={styles.moreOpen}>접기 ▴</span>
        </span>
      </summary>
      <div className={styles.fixPane}>
        {row.note ? <p className={styles.fixWhy}>{row.note}</p> : null}
        {row.codeExample ? <pre className={styles.code}>{row.codeExample}</pre> : null}
        <p className={styles.fixOwner}>
          담당: <b>{row.owner === 'DEVELOPER' ? '개발' : row.owner === 'CONTENT' ? '콘텐츠' : row.owner === 'HOSTING' ? '호스팅' : row.owner}</b>
          {' · '}심각도 {row.severity}
        </p>
      </div>
    </details>
  );
}
