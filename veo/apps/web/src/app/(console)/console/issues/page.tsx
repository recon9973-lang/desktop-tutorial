import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { claimedButUnverified, inWorkOrder, type Issue } from '@/lib/issues';
import { readIssues } from '@/lib/issues-api';
import { listCompanies } from '@/lib/companies';
import { readSeverities } from '@/lib/scoring-api';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import { IssueCard } from './IssueCard';
import own from './issues.module.css';

export const metadata: Metadata = {
  title: '이슈',
};

export const dynamic = 'force-dynamic';

export default async function ConsoleIssuesPage({
  searchParams,
}: {
  readonly searchParams: Promise<{ readonly project?: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { project } = await searchParams;

  return (
    <PermissionGate identity={identity} permission="issue:read">
      <ConsoleIssuesContent projectId={project ?? null} />
    </PermissionGate>
  );
}

async function ConsoleIssuesContent({ projectId }: { readonly projectId: string | null }) {
  const companies = await listCompanies();
  const projects = companies.ok
    ? companies.data.flatMap((company) =>
        company.projects.map((one) => ({ ...one, company: company.name })),
      )
    : [];
  const found = await readIssues(projectId);
  // 심각도 어휘는 채점 명세를 쥐고 있는 엔진이 정의한다. 화면이 목록을 들고 있으면
  // 엔진이 어휘를 늘려도 그대로 옛 목록을 보여 주고, 빠진 항목은 애초에 없는 것처럼
  // 보이므로 아무도 알아채지 못한다.
  const severities = await readSeverities();
  const issues: readonly Issue[] = found.ok ? inWorkOrder(found.data) : [];
  const open = issues.filter((issue) => issue.is_open);
  const unverified = claimedButUnverified(issues);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>이슈</h1>
        <p className={styles.lede}>
          진단에서 실패 또는 주의로 판정된 항목입니다. 각 항목은 어떤 검사에서 어떤 근거로
          나왔는지를 함께 보관합니다. <strong>이슈는 재측정이 닫습니다</strong> — 담당자가
          &lsquo;수정했다&rsquo;고 보고한 것은 아직 열린 문제입니다.
        </p>
      </div>

      {projects.length > 1 ? (
        <nav className={own.projectTabs} aria-label="프로젝트 선택">
          <Link
            href="/console/issues"
            className={projectId === null ? own.projectTabActive : own.projectTab}
          >
            전체
          </Link>
          {projects.map((one) => (
            <Link
              key={one.id}
              href={`/console/issues?project=${encodeURIComponent(one.id)}`}
              className={one.id === projectId ? own.projectTabActive : own.projectTab}
            >
              {one.company} · {one.name}
            </Link>
          ))}
        </nav>
      ) : null}

      {!found.ok ? (
        <ErrorState
          title="이슈를 불러오지 못했습니다"
          description={found.message ?? '서버에 연결하지 못했습니다.'}
        />
      ) : (
        <>
          <section className={styles.section} aria-labelledby="issues-list-heading">
            <h2 id="issues-list-heading" className={styles.sectionTitle}>
              조치가 필요한 항목 {open.length}건
            </h2>

            {/*
              이 숫자를 열린 건수에서 빼지 않는다. 빼는 순간 "수정 보고" 가 "해결" 자리로
              옮겨 앉고, 남는 것은 바뀐 것 없는 사이트 위의 깨끗한 대시보드다.
            */}
            {unverified > 0 ? (
              <p className={own.unverifiedTotal}>
                이 중 <strong>{unverified}건</strong>은 수정했다고 보고되었을 뿐 재측정으로
                확인되지 않았습니다. 위 건수에 그대로 포함되어 있습니다.
              </p>
            ) : null}

            {open.length > 0 ? (
              <ul className={own.issueList}>
                {open.map((issue) => (
                  <IssueCard key={issue.id} issue={issue} />
                ))}
              </ul>
            ) : issues.length > 0 ? (
              <EmptyState description="열려 있는 문제가 없습니다." />
            ) : (
              <EmptyState description="진단을 실행하면 실패·주의로 판정된 항목이 근거와 함께 이곳에 모입니다." />
            )}
          </section>

          {issues.length > open.length ? (
            <section className={styles.section} aria-labelledby="issues-closed-heading">
              <h2 id="issues-closed-heading" className={styles.sectionTitle}>
                닫힌 항목 {issues.length - open.length}건
              </h2>
              <p className={styles.callout}>
                &lsquo;재측정으로 해결 확인&rsquo;은 측정이고, &lsquo;조치하지 않음&rsquo;은
                결정입니다. 둘 다 더 볼 일이 없다는 뜻일 뿐, 같은 말이 아닙니다.
              </p>
              <ul className={own.issueList}>
                {issues
                  .filter((issue) => !issue.is_open)
                  .map((issue) => (
                    <IssueCard key={issue.id} issue={issue} />
                  ))}
              </ul>
            </section>
          ) : null}
        </>
      )}

      <section className={styles.section} aria-labelledby="issues-severity-heading">
        <h2 id="issues-severity-heading" className={styles.sectionTitle}>
          심각도 구분
        </h2>
        {!severities.ok ? (
          <ErrorState
            title="심각도 구분을 불러오지 못했습니다"
            description={
              severities.message ??
              '채점 명세를 쥐고 있는 엔진에 연결하지 못했습니다. 임의로 적어 둔 목록을 대신 보여 주지 않습니다.'
            }
          />
        ) : (
          <Card title="채점 명세가 정의하는 심각도" headingLevel={3}>
            <dl className={styles.definitionList}>
              {severities.data.map((severity) => (
                <div key={severity.id} className={styles.definitionRow}>
                  <dt>
                    {severity.label_ko} <span className={styles.token}>{severity.id}</span>
                  </dt>
                  <dd>{severity.meaning_ko}</dd>
                </div>
              ))}
            </dl>
          </Card>
        )}
        <p className={styles.callout}>
          심각도별 감점 계수는 프론트엔드가 아니라 채점 명세에만 정의되어 있습니다. 화면은 계산
          결과와 그 근거만 표시합니다.
        </p>
      </section>
    </div>
  );
}
