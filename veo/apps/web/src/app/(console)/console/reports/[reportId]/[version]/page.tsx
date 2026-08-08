import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ErrorState } from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readReportVersion } from '@/lib/reports';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { ReportBody, readAudience, type Audience } from './ReportBody';

export const metadata: Metadata = {
  title: '리포트 본문',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * 발행된 리포트 한 판을 화면에서 읽는다.
 *
 * 지금까지 화면에는 목록·내보내기·공유 링크만 있었다. 본문을 읽으려면 파일로
 * 내려받아야 했다 — 서버에는 처음부터 창구가 있었는데 부르는 곳이 없었다
 * (`docs/audit/2026-08-08-server-ui-gap.md` §A-3).
 *
 * **독자는 주소로 가른다**(`?audience=marketing`). 탭을 자바스크립트로 만들지 않은
 * 이유는 둘이다 — 특정 독자의 판을 링크로 그대로 보낼 수 있고, 자바스크립트가 죽어도
 * 읽힌다. 이 화면은 읽히는 것이 전부다.
 *
 * 그리는 일은 `ReportBody` 가 한다. 콘솔은 로그인이 필요해 눈으로 못 여는 자리라,
 * 표현을 떼어 두고 시험으로 확인한다(`VisibilityReport` 와 같은 모양).
 */
export default async function ReportVersionPage({
  params,
  searchParams,
}: {
  readonly params: Promise<{ readonly reportId: string; readonly version: string }>;
  readonly searchParams: Promise<{ readonly audience?: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { reportId, version } = await params;
  const { audience } = await searchParams;

  return (
    <PermissionGate identity={identity} permission="report:read">
      <VersionContent
        reportId={reportId}
        version={version}
        audience={readAudience(audience)}
      />
    </PermissionGate>
  );
}

async function VersionContent({
  reportId,
  version,
  audience,
}: {
  readonly reportId: string;
  readonly version: string;
  readonly audience: Audience;
}) {
  const versionNumber = Number(version);
  if (!Number.isInteger(versionNumber) || versionNumber < 1) notFound();

  const found = await readReportVersion(reportId, versionNumber);
  if (!found.ok && found.reason === 'NOT_FOUND') notFound();
  if (!found.ok) {
    return (
      <div className={styles.page}>
        <ErrorState
          title="리포트를 불러오지 못했습니다"
          description={found.message ?? '서버에 연결하지 못했습니다.'}
        />
      </div>
    );
  }

  const detail = found.data;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>
          <Link href="/console/reports">리포트</Link> ·{' '}
          <Link href={`/console/reports/${reportId}`}>버전 목록</Link> · v
          {detail.version_number}
        </p>
        <h1 className={styles.title}>{detail.views[audience].title_ko}</h1>
        <p className={styles.lede}>{detail.title_ko}</p>
      </div>

      <ReportBody detail={detail} audience={audience} />
    </div>
  );
}
