import type { Metadata } from 'next';
import Link from 'next/link';
import { EmptyState, ErrorState } from '@veo/ui';

import { listReportVersions, type ReportVersionRow } from '@/lib/reports';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import own from '../reports.module.css';

import { ShareLinkButton } from './ShareLinkButton';

/**
 * 리포트 버전 목록 — "발행했는데 볼 수 없는" 상태를 끝내는 화면 (E7).
 *
 * 열람은 엔진의 HTML 내보내기를 그대로 연다. 세 형식(HTML·CSV·XLSX)은 같은
 * 스냅샷의 같은 표기라는 것이 엔진 계약이므로, 화면이 문서를 다시 그리면 그
 * 계약이 네 번째 표기를 만들게 된다 — 그래서 다시 그리지 않는다.
 */

export const metadata: Metadata = {
  title: '리포트 버전',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

const FORMAT_LABELS: Record<string, string> = {
  html: 'HTML',
  csv: 'CSV',
  xlsx: '엑셀',
};

export default async function ReportVersionsPage({
  params,
}: {
  readonly params: Promise<{ readonly reportId: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { reportId } = await params;

  return (
    <PermissionGate identity={identity} permission="report:read">
      <ReportVersionsContent reportId={reportId} />
    </PermissionGate>
  );
}

async function ReportVersionsContent({ reportId }: { readonly reportId: string }) {
  const versions = await listReportVersions(reportId);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>
          <Link href="/console/reports">리포트</Link> · 버전
        </p>
        <h1 className={styles.title}>
          {versions.ok && versions.data.length > 0 ? versions.data[0]!.title_ko : '리포트 버전'}
        </h1>
        <p className={styles.lede}>
          발행된 버전은 고칠 수 없습니다. 각 버전에는 발행 시각과 내용 해시가 붙어 있어,
          업체에 전달한 문서가 어느 버전이었는지 나중에도 맞춰 볼 수 있습니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="versions-heading">
        <h2 id="versions-heading" className={styles.sectionTitle}>
          발행된 버전
        </h2>
        {!versions.ok ? (
          <ErrorState
            title="버전 목록을 불러오지 못했습니다"
            description={versions.message ?? '서버에 연결하지 못했습니다.'}
          />
        ) : versions.data.length === 0 ? (
          <EmptyState description="이 리포트에는 아직 발행된 버전이 없습니다." />
        ) : (
          <ul className={own.reportList}>
            {versions.data.map((version) => (
              <VersionItem key={version.version_number} version={version} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function VersionItem({ version }: { readonly version: ReportVersionRow }) {
  const openHref = exportHref(version, 'html');
  return (
    <li className={own.report}>
      <p className={own.reportHead}>
        <span className={own.version}>v{version.version_number}</span>
        <span className={own.reportTitle}>{version.title_ko}</span>
      </p>
      <p className={own.reportMeta}>
        발행 {formatWhen(version.generated_at)}
        {version.measurement_window_start !== null && version.measurement_window_end !== null
          ? ` · 측정 구간 ${formatWhen(version.measurement_window_start)} ~ ${formatWhen(version.measurement_window_end)}`
          : ''}
      </p>
      <p className={own.hash}>{version.content_hash}</p>
      <p className={own.versionActions}>
        {/*
          본문을 화면에서 읽는 자리. 예전에는 내보내기(HTML 파일)뿐이라 문서를 보려면
          내려받아야 했다 — 서버에는 창구가 있었는데 부르는 곳이 없었다(0-E).
        */}
        <Link
          href={`/console/reports/${version.report_id}/${version.version_number}`}
          className={own.versionOpen}
        >
          본문 읽기
        </Link>
        {version.export_formats.includes('html') ? (
          <a href={openHref} target="_blank" rel="noreferrer" className={own.versionOpen}>
            HTML 로 열기
          </a>
        ) : null}
        {version.export_formats
          .filter((format) => format !== 'html')
          .map((format) => (
            <a key={format} href={exportHref(version, format)} className={own.versionExport}>
              {FORMAT_LABELS[format] ?? format.toUpperCase()} 내려받기
            </a>
          ))}
        {/* 거래처 전달 — 로그인 없이 열리는 링크. 지금 이 순간의 문서가 굳는다. */}
        <ShareLinkButton reportId={version.report_id} version={version.version_number} />
      </p>
    </li>
  );
}

function exportHref(version: ReportVersionRow, format: string): string {
  const query = new URLSearchParams({
    report: version.report_id,
    version: String(version.version_number),
    format,
  });
  return `/api/report-export?${query.toString()}`;
}

/** 서버에서 그린다. 시간대를 한국 기준으로 고정해 두 곳에서 다른 시각이 보이지 않게 한다. */
function formatWhen(value: string | null): string {
  if (value === null) return '시각 기록 없음';
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return value;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Seoul',
  }).format(at);
}
