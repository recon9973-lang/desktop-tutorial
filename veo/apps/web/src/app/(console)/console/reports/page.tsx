import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { listCompanies } from '@/lib/companies';
import { listReportableRuns, listReports, type ReportRow } from '@/lib/reports';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import { PublishForm } from './PublishForm';
import own from './reports.module.css';
import { formatWhen } from '@/lib/when';

export const metadata: Metadata = {
  title: '리포트',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleReportsPage({
  searchParams,
}: {
  readonly searchParams: Promise<{ readonly project?: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { project } = await searchParams;

  return (
    <PermissionGate identity={identity} permission="report:read">
      <ConsoleReportsContent projectId={project ?? null} />
    </PermissionGate>
  );
}

async function ConsoleReportsContent({ projectId }: { readonly projectId: string | null }) {
  const companies = await listCompanies();
  const projects = companies.ok
    ? companies.data.flatMap((company) =>
        company.projects.map((one) => ({ ...one, company: company.name })),
      )
    : [];
  const selected = projectId ?? projects[0]?.id ?? null;
  const reports = await listReports(selected);
  const runs = selected === null ? null : await listReportableRuns(selected);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>리포트</h1>
        <p className={styles.lede}>
          업체에 전달하는 문서입니다. <strong>숫자는 진단 실행에서만 옵니다</strong> — 이
          화면에는 점수를 손으로 넣는 칸이 없습니다. 발행한 버전은 고칠 수 없고, 다시 재면
          새 버전이 붙습니다.
        </p>
      </div>

      {projects.length > 1 ? (
        <nav className={own.projectTabs} aria-label="프로젝트 선택">
          {projects.map((one) => (
            <Link
              key={one.id}
              href={`/console/reports?project=${encodeURIComponent(one.id)}`}
              className={one.id === selected ? own.projectTabActive : own.projectTab}
            >
              {one.company} · {one.name}
            </Link>
          ))}
        </nav>
      ) : null}

      <section className={styles.section} aria-labelledby="reports-new-heading">
        <h2 id="reports-new-heading" className={styles.sectionTitle}>
          새 리포트 발행
        </h2>
        {selected === null ? (
          <EmptyState description="프로젝트가 없습니다. 업체 화면에서 측정할 주소를 먼저 등록해 주십시오." />
        ) : runs !== null && !runs.ok ? (
          <ErrorState
            title="진단 목록을 불러오지 못했습니다"
            description={runs.message ?? '서버에 연결하지 못했습니다.'}
          />
        ) : runs !== null && runs.ok ? (
          <PublishForm
            runs={runs.data.map((run) => ({
              scanRunId: run.scan_run_id,
              label: `${formatWhen(run.started_at)} · ${run.urls_collected}페이지 · ${run.status}`,
            }))}
          />
        ) : null}
      </section>

      <section className={styles.section} aria-labelledby="reports-list-heading">
        <h2 id="reports-list-heading" className={styles.sectionTitle}>
          발행된 리포트
        </h2>
        {!reports.ok ? (
          <ErrorState
            title="리포트를 불러오지 못했습니다"
            description={reports.message ?? '서버에 연결하지 못했습니다.'}
          />
        ) : reports.data.length === 0 ? (
          <EmptyState description="아직 발행한 리포트가 없습니다." />
        ) : (
          <ul className={own.reportList}>
            {reports.data.map((report) => (
              <ReportItem key={report.report_id} report={report} />
            ))}
          </ul>
        )}
      </section>

      <section className={styles.section} aria-labelledby="reports-policy-heading">
        <h2 id="reports-policy-heading" className={styles.sectionTitle}>
          리포트에 항상 들어가는 것
        </h2>
        <Card title="숫자 옆에 늘 붙는 정보" headingLevel={3}>
          <ul className={styles.list}>
            <li>계산에 사용한 채점 명세와 버전·체크섬</li>
            <li>측정 범위와 신뢰도</li>
            <li>각 값의 출처와 수집 시각</li>
            <li>측정하지 못한 항목과 그 이유 — 0점으로 바뀌지 않습니다</li>
          </ul>
        </Card>
      </section>
    </div>
  );
}

function ReportItem({ report }: { readonly report: ReportRow }) {
  return (
    <li className={own.report}>
      <p className={own.reportHead}>
        <span className={own.reportTitle}>{report.title}</span>
        {report.latest_version_number !== null ? (
          <span className={own.version}>v{report.latest_version_number}</span>
        ) : (
          // 감추지 않는다. 만들다 만 것이 흔적 없이 사라지면 왜 없는지 아무도 모른다.
          <span className={own.unpublished}>발행된 버전 없음</span>
        )}
      </p>
      <p className={own.reportMeta}>
        만든 날 {formatWhen(report.created_at)}
        {report.latest_generated_at !== null
          ? ` · 최신 버전 ${formatWhen(report.latest_generated_at)}`
          : ''}
      </p>
      {/*
        내용 해시를 보인다. 고객에게 전달한 문서가 어느 버전이었는지 나중에 맞춰 볼 수
        있어야 하고, 그러려면 사람이 눈으로 비교할 무언가가 화면에 있어야 한다.
      */}
      {report.latest_content_hash !== null ? (
        <p className={own.hash}>{report.latest_content_hash.slice(0, 23)}…</p>
      ) : null}
      {/* 발행된 버전이 있어야 볼 것이 있다 — 없는 문에 링크를 달지 않는다. */}
      {report.latest_version_number !== null ? (
        <p className={own.versionActions}>
          <Link
            href={`/console/reports/${encodeURIComponent(report.report_id)}`}
            className={own.reportLink}
          >
            버전 열람·내보내기 →
          </Link>
        </p>
      ) : null}
    </li>
  );
}

/** 서버에서 그린다. 시간대를 한국 기준으로 고정해 두 곳에서 다른 시각이 보이지 않게 한다. */
