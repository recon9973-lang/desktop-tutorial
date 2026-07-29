import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { ScanReport, type ReportView } from '@/components/ScanReport/ScanReport';
import { listCompanies } from '@/lib/companies';
import { readBands, readHistory, readSavedReport, type HistoryEntry } from '@/lib/scan-report';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { ScanForm } from './ScanForm';
import own from './seo.module.css';

export const metadata: Metadata = {
  title: 'SEO 기술 준비도',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * SEO 진단 결과.
 *
 * 화면을 열 때 **다시 재지 않는다.** 저장된 마지막 결과를 보여주고, 재측정은 사람이
 * 버튼을 눌렀을 때만 일어난다 — 같은 주소를 하루에 여러 번 다시 재는 것은 대상 사이트
 * 에도 우리 비용에도 부담이고, 변경을 확인하려는 것이 아니면 다시 잴 이유가 없다.
 */
export default async function SeoPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const identity = await requireConsoleIdentity();
  const params = await searchParams;

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <SeoContent
        siteId={single(params['site'])}
        runId={single(params['run'])}
        view={single(params['view']) === 'simple' ? 'simple' : 'detailed'}
      />
    </PermissionGate>
  );
}

function single(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

async function SeoContent({
  siteId,
  runId,
  view,
}: {
  readonly siteId: string | null;
  readonly runId: string | null;
  readonly view: ReportView;
}) {
  if (siteId === null) return <NewScan />;

  const [history, companies] = await Promise.all([readHistory(siteId), listCompanies()]);

  if (!history.ok) {
    return (
      <Shell>
        <ErrorState
          title="이력을 불러오지 못했습니다"
          description={history.message ?? '서버에 연결하지 못했습니다.'}
        />
      </Shell>
    );
  }

  const site = companies.ok
    ? companies.data.flatMap((company) => company.sites).find((one) => one.siteId === siteId)
    : undefined;
  const origin = site?.origin ?? '';

  const entries = history.data;
  const selected = runId === null ? entries[0] : entries.find((e) => e.scanRunId === runId);

  return (
    <Shell origin={origin}>
      <div className={own.toolbar}>
        <ScanForm siteId={siteId} />
        {selected === undefined ? null : (
          <ViewSwitch siteId={siteId} runId={selected.scanRunId} view={view} />
        )}
      </div>

      {entries.length === 0 ? (
        <EmptyState description="아직 진단하지 않았습니다. 위의 진단 실행을 누르면 결과가 여기에 쌓입니다." />
      ) : (
        <>
          <HistoryStrip
            entries={entries}
            siteId={siteId}
            selectedId={selected?.scanRunId ?? null}
            view={view}
          />
          {selected === undefined ? null : (
            <SavedReport scanRunId={selected.scanRunId} origin={origin} view={view} />
          )}
        </>
      )}
    </Shell>
  );
}

async function SavedReport({
  scanRunId,
  origin,
  view,
}: {
  readonly scanRunId: string;
  readonly origin: string;
  readonly view: ReportView;
}) {
  const result = await readSavedReport(scanRunId, origin);
  if (result === null) {
    return (
      <ErrorState
        title="저장된 결과를 불러오지 못했습니다"
        description="이 진단은 결과 본문이 남아 있지 않습니다. 다시 측정하면 이후로는 그대로 다시 열 수 있습니다."
      />
    );
  }

  const bands = await readBands(result.specId, result.specVersion);
  return <ScanReport result={result} bands={bands} view={view} />;
}

function HistoryStrip({
  entries,
  siteId,
  selectedId,
  view,
}: {
  readonly entries: readonly HistoryEntry[];
  readonly siteId: string;
  readonly selectedId: string | null;
  readonly view: ReportView;
}) {
  return (
    <section className={own.history} aria-labelledby="scan-history">
      <h2 id="scan-history" className={own.historyTitle}>
        측정 이력
      </h2>
      <ul className={own.historyList}>
        {entries.map((entry) => {
          const current = entry.scanRunId === selectedId;
          return (
            <li key={entry.scanRunId}>
              <Link
                href={`/console/seo?site=${siteId}&run=${entry.scanRunId}&view=${view}`}
                className={current ? `${own.historyItem} ${own.historyCurrent}` : own.historyItem}
                aria-current={current ? 'true' : undefined}
              >
                <span className={own.historyScore}>
                  {entry.score === null ? '—' : entry.score.toFixed(1)}
                </span>
                <span className={own.historyWhen}>{formatWhen(entry.startedAt)}</span>
                <span className={own.historyWho}>
                  {entry.requestedByName ?? '실행자 기록 없음'} · {entry.urlsCollected}페이지
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ViewSwitch({
  siteId,
  runId,
  view,
}: {
  readonly siteId: string;
  readonly runId: string;
  readonly view: ReportView;
}) {
  const base = `/console/seo?site=${siteId}&run=${runId}`;
  return (
    <nav className={own.views} aria-label="결과 보기 방식">
      <Link href={`${base}&view=simple`} aria-current={view === 'simple' ? 'page' : undefined}>
        간소화 · 업체 전달용
      </Link>
      <Link href={`${base}&view=detailed`} aria-current={view === 'detailed' ? 'page' : undefined}>
        상세 · 직원용
      </Link>
    </nav>
  );
}

/**
 * 첫 화면 — 주소 한 칸.
 *
 * 등록을 먼저 시키지 않는다. 넣으면 잰다. 이미 잰 주소는 아래 목록에서 바로 열 수 있고,
 * 그때는 다시 재지 않는다.
 */
async function NewScan() {
  const companies = await listCompanies();
  const measured = companies.ok
    ? companies.data.flatMap((company) =>
        company.sites.map((site) => ({ company: company.name, ...site })),
      )
    : [];

  return (
    <Shell>
      <Card title="주소를 넣으면 바로 진단합니다" headingLevel={2}>
        <ScanForm />
      </Card>

      {!companies.ok ? (
        <ErrorState
          title="지난 진단 목록을 불러오지 못했습니다"
          description={companies.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : measured.length === 0 ? null : (
        <section className={own.previous} aria-labelledby="measured-sites">
          <h2 id="measured-sites" className={own.historyTitle}>
            이미 진단한 주소
          </h2>
          <ul className={own.siteList}>
            {measured.map((site) => (
              <li key={site.siteId}>
                <Link href={`/console/seo?site=${site.siteId}`}>{site.origin}</Link>
                {site.company === site.origin.replace(/^https?:\/\/(www\.)?/, '') ? null : (
                  <span className={own.siteCompany}> · {site.company}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </Shell>
  );
}

function Shell({ origin, children }: { readonly origin?: string; readonly children: ReactNode }) {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>SEO 기술 준비도</h1>
        <p className={styles.lede}>
          {origin === undefined || origin === '' ? '' : `${origin} · `}
          검색엔진이 사이트를 발견·크롤링·해석·제공할 수 있는 상태인지 항목별로 확인합니다.
          순위 예측이 아니라 준비도입니다.
        </p>
      </div>
      {children}
    </div>
  );
}

/** 표시 시각은 서버 시각이 아니라 한국 시각으로 고정한다. */
function formatWhen(iso: string): string {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Seoul',
  }).format(when);
}
