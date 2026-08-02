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
 *
 * 측정 이력(2026-08-02): 완료된 진단은 이 브라우저의 localStorage 에 자동으로
 * 남는다 — 서버에는 아무것도 저장하지 않는다(익명 방문자의 URL 을 수집하지 않는
 * 공개 표면의 경계). 같은 주소를 다시 재면 지난 점수와의 차이를 보여준다.
 * 직원 전체가 공유하는 이력은 콘솔(로그인) 스캔이 맡는다 — 그쪽은 DB 에 남는다.
 */

import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import Link from 'next/link';

import type { ScanCheckRow, ScanResult, ScanVerdict } from '@/lib/scan-api-types';
import {
  HISTORY_LIMIT,
  getHistorySnapshot,
  getServerHistorySnapshot,
  subscribeHistory,
  writeHistory,
  type HistoryEntry,
} from '@/lib/scan-history';

import styles from './public-checker.module.css';

type Filter = 'ALL' | ScanVerdict;

interface ScanError {
  readonly message: string;
}

function shortDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
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

export interface CheckerCopy {
  readonly scoreLabel: string;
  readonly activeLabel: string;
  readonly activeSub: string;
  readonly otherHref: string;
  readonly otherLabel: string;
  readonly otherSub: string;
}

const COPY: Record<'SEO' | 'GEO', CheckerCopy> = {
  SEO: {
    scoreLabel: 'SEO 준비도',
    activeLabel: 'SEO',
    activeSub: '검색엔진 준비도',
    otherHref: '/tools/geo',
    otherLabel: 'GEO',
    otherSub: '같은 주소로 AI 답변 엔진 준비도 확인 →',
  },
  GEO: {
    scoreLabel: 'GEO 준비도',
    activeLabel: 'GEO',
    activeSub: 'AI 답변 엔진 준비도',
    otherHref: '/tools/seo',
    otherLabel: 'SEO',
    otherSub: '같은 주소로 검색엔진 준비도 확인 →',
  },
};

export function PublicChecker({ kind }: { readonly kind: 'SEO' | 'GEO' }) {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ScanError | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [filter, setFilter] = useState<Filter>('ALL');
  const [previous, setPrevious] = useState<HistoryEntry | null>(null);
  // 이력은 외부 스토어다 — 서버 렌더에서는 빈 목록으로 그려 hydration 을 맞추고,
  // 마운트 뒤 스토리지 값으로 갈아탄다. writeHistory 가 알림을 쏘면 다시 그린다.
  const history = useSyncExternalStore(
    subscribeHistory,
    getHistorySnapshot,
    getServerHistorySnapshot,
  );
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
        body: JSON.stringify({ url: url.trim(), kind }),
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
      const scanned = record.result as ScanResult;
      setResult(scanned);
      setFilter('ALL');
      // 따로 저장 버튼 없이 기록된다. 지난 측정(같은 주소·같은 종류)이 있으면
      // 이번 점수 옆에 차이로 나온다 — 최신이 맨 앞이므로 첫 일치가 직전 기록이다.
      setPrevious(
        history.find((entry) => entry.kind === kind && entry.url === scanned.targetUrl) ?? null,
      );
      writeHistory(
        [
          {
            url: scanned.targetUrl,
            kind,
            score: scanned.score.value,
            band: scanned.score.bandLabel,
            at: new Date().toISOString(),
          },
          ...history,
        ].slice(0, HISTORY_LIMIT),
      );
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
          {kind === 'SEO' ? (
            <span className={`${styles.mode} ${styles.modeOn}`} role="tab" aria-selected="true">
              SEO 점수
            </span>
          ) : (
            <Link className={styles.mode} href="/tools/seo" role="tab" aria-selected="false">
              SEO 점수
            </Link>
          )}
          {kind === 'GEO' ? (
            <span className={`${styles.mode} ${styles.modeOn}`} role="tab" aria-selected="true">
              GEO 점수
            </span>
          ) : (
            <Link className={styles.mode} href="/tools/geo" role="tab" aria-selected="false">
              GEO 점수
            </Link>
          )}
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

      {result ? (
        <Report
          result={result}
          kind={kind}
          filter={filter}
          onFilter={setFilter}
          reportRef={reportRef}
          previous={previous}
        />
      ) : history.length > 0 ? (
        <section className={styles.history} aria-label="최근 측정 기록">
          <h2 className={styles.historyTitle}>최근 측정 기록</h2>
          <p className={styles.historySub}>
            이 브라우저에만 저장됩니다 — 주소를 누르면 다시 진단할 수 있습니다.
          </p>
          <ul className={styles.historyList}>
            {history.slice(0, 8).map((entry) => (
              <li key={`${entry.at}-${entry.url}`}>
                <button
                  type="button"
                  className={styles.historyRow}
                  onClick={() => setUrl(entry.url)}
                >
                  <span className={styles.historyKind}>{entry.kind}</span>
                  <span className={styles.historyUrl}>{entry.url}</span>
                  <span className={`${styles.historyScore} ${styles.mono}`}>
                    {entry.score === null ? '—' : entry.score.toFixed(1)}
                  </span>
                  <span className={styles.historyDate}>{shortDate(entry.at)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function Report({
  result,
  kind,
  filter,
  onFilter,
  reportRef,
  previous,
}: {
  readonly result: ScanResult;
  readonly kind: 'SEO' | 'GEO';
  readonly filter: Filter;
  readonly onFilter: (next: Filter) => void;
  readonly reportRef: React.RefObject<HTMLDivElement | null>;
  readonly previous: HistoryEntry | null;
}) {
  const copy = COPY[kind];
  const quality =
    result.score.value === null || result.reach === 0
      ? null
      : result.score.value / result.reach;

  return (
    <div ref={reportRef} className={styles.report}>
      <section className={styles.scoreband} aria-label="점수 요약">
        <div>
          <div className={styles.gauge}>
            <div className={styles.gaugeArc} style={gaugeStyle(result.score.value)} />
            <div className={styles.gaugeHole} />
            <div className={styles.gaugeVal}>
              <b>{result.score.value === null ? '—' : result.score.value.toFixed(1)}</b>
              <span>{copy.scoreLabel}</span>
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
            {previous?.score != null && result.score.value !== null ? (
              <div className={styles.prevLine}>
                지난 측정({shortDate(previous.at)}){' '}
                <b className={styles.mono}>{previous.score.toFixed(1)}</b>
                {' → '}
                <b
                  className={`${styles.mono} ${
                    result.score.value >= previous.score ? styles.deltaUp : styles.deltaDown
                  }`}
                >
                  {result.score.value >= previous.score ? '▲' : '▼'}
                  {Math.abs(result.score.value - previous.score).toFixed(1)}
                </b>
              </div>
            ) : null}
            <button type="button" className={styles.pdfButton} onClick={() => window.print()}>
              ⬇ PDF 보고서
            </button>
          </div>
          {result.exposure?.isBlocked ? (
            <p className={styles.exposure} role="alert">
              ⚠ 노출 차단 — {result.exposure.labels.join(' · ') || '접근이 막혀 있습니다'}.
              구조 점수와 별개로, 지금은 어떤 엔진도 이 페이지에 닿지 못합니다.
            </p>
          ) : null}
        </div>

        <div className={styles.twincol}>
          <div className={`${styles.twin} ${styles.twinOn}`}>
            <span>
              <span className={styles.twinLabel}>{copy.activeLabel}</span>
              <span className={styles.twinSub}>{copy.activeSub}</span>
            </span>
            <b className={styles.mono}>
              {result.score.value === null ? '—' : result.score.value.toFixed(1)}
            </b>
          </div>
          <Link className={styles.twin} href={copy.otherHref}>
            <span>
              <span className={styles.twinLabel}>{copy.otherLabel}</span>
              <span className={styles.twinSub}>{copy.otherSub}</span>
            </span>
          </Link>
        </div>

        <ul
          className={styles.stagegrid}
          aria-label={kind === 'SEO' ? '검색 여정 단계별 점수' : '영역별 점수'}
        >
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
  const broken = row.verdict === 'FAIL' || row.verdict === 'WARNING';
  // 진단 문장은 수집기의 것을 그대로 — 없으면 판정 요약(note)으로.
  const diagnosis = row.detail ?? row.note;
  const hasDetail = Boolean(diagnosis || row.fix || row.codeExample);
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

  // 실패·주의는 처음부터 열려 있다 — 진단과 조치가 "더보기" 뒤에 숨지 않는다.
  return (
    <details className={styles.item} open={broken}>
      <summary>
        {summary}
        <span className={styles.moreButton} aria-hidden="true">
          <span className={styles.moreClosed}>자세히 ▾</span>
          <span className={styles.moreOpen}>접기 ▴</span>
        </span>
      </summary>
      <div className={styles.fixPane}>
        {diagnosis ? (
          <>
            <h4 className={styles.paneLabel}>진단 결과</h4>
            <p className={styles.fixWhy}>{diagnosis}</p>
          </>
        ) : null}
        {row.fix ? (
          <>
            <h4 className={styles.paneLabel}>이렇게 고치세요</h4>
            <p className={styles.fixWhy}>{row.fix}</p>
          </>
        ) : null}
        {row.codeExample ? <CodeBlock code={row.codeExample} /> : null}
        <p className={styles.fixOwner}>
          담당: <b>{row.owner === 'DEVELOPER' ? '개발' : row.owner === 'CONTENT' ? '콘텐츠' : row.owner === 'HOSTING' ? '호스팅' : row.owner}</b>
          {' · '}심각도 {row.severity}
        </p>
      </div>
    </details>
  );
}

function CodeBlock({ code }: { readonly code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className={styles.codeWrap}>
      <h4 className={styles.paneLabel}>붙여넣을 코드</h4>
      <button
        type="button"
        className={styles.copyButton}
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1600);
          } catch {
            // 클립보드 권한이 없으면 조용히 둔다 — 코드는 화면에 있으니 직접 긁으면 된다.
          }
        }}
      >
        {copied ? '복사됨 ✓' : '코드 복사'}
      </button>
      <pre className={styles.code}>{code}</pre>
    </div>
  );
}
