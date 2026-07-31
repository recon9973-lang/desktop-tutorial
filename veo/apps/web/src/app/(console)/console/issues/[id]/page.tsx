import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Card, ErrorState } from '@veo/ui';

import { evidenceKindLabel, ownerLabel } from '@/lib/issues';
import { readIssue } from '@/lib/issues-api';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import { IssueCard } from '../IssueCard';
import own from '../issues.module.css';

export const metadata: Metadata = {
  title: '이슈 상세',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleIssueDetailPage({
  params,
}: {
  readonly params: Promise<{ readonly id: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { id } = await params;

  return (
    <PermissionGate identity={identity} permission="issue:read">
      <IssueDetailContent issueId={id} />
    </PermissionGate>
  );
}

async function IssueDetailContent({ issueId }: { readonly issueId: string }) {
  const found = await readIssue(issueId);
  if (!found.ok && found.reason === 'NOT_FOUND') notFound();
  if (!found.ok) {
    return (
      <div className={styles.page}>
        <ErrorState
          title="이슈를 불러오지 못했습니다"
          description={found.message ?? '서버에 연결하지 못했습니다.'}
        />
      </div>
    );
  }

  const issue = found.data;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>
          <Link href="/console/issues">이슈</Link> · {issue.check_id}
        </p>
        <h1 className={styles.title}>{issue.title_ko}</h1>
        <p className={styles.lede}>{issue.summary_ko}</p>
      </div>

      <section className={styles.section} aria-labelledby="issue-state-heading">
        <h2 id="issue-state-heading" className={styles.sectionTitle}>
          지금 상태
        </h2>
        <ul className={own.issueList}>
          <IssueCard issue={issue} linkToDetail={false} />
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="issue-evidence-heading">
        <h2 id="issue-evidence-heading" className={styles.sectionTitle}>
          근거 {issue.evidence.length}건
        </h2>
        <p className={styles.callout}>
          이 지적이 무엇을 보고 내려졌는지입니다. 수집 시각과 내용 해시가 함께 남아 있어,
          나중에도 <strong>판정된 내용이 수집된 내용이었음</strong>을 보일 수 있습니다.
        </p>

        {/*
          찾지 못한 근거를 조용히 빼지 않는다. 빼면 지적이 실제보다 튼튼해 보인다.
        */}
        {issue.missing_evidence_count > 0 ? (
          <p className={own.unverifiedTotal}>
            이 지적이 부르는 근거 {issue.missing_evidence_count}건을 찾지 못했습니다. 그만큼은
            지금 확인할 수 없습니다.
          </p>
        ) : null}

        {issue.evidence.length > 0 ? (
          <ul className={own.evidenceList}>
            {issue.evidence.map((record) => (
              <li key={record.evidence_id} className={own.evidence}>
                <p className={own.evidenceHead}>
                  <span className={own.evidenceKind}>{evidenceKindLabel(record.kind)}</span>
                  {record.url !== null ? (
                    <span className={own.evidenceUrl}>{record.url}</span>
                  ) : null}
                </p>
                {record.excerpt !== null && record.excerpt !== '' ? (
                  <pre className={own.excerpt}>{record.excerpt}</pre>
                ) : (
                  <p className={own.noExcerpt}>발췌가 저장되지 않았습니다.</p>
                )}
                <p className={own.evidenceMeta}>
                  수집 {formatWhen(record.collected_at)} · 해시{' '}
                  <span className={own.hash}>{record.content_hash.slice(0, 16)}…</span>
                </p>
              </li>
            ))}
          </ul>
        ) : issue.missing_evidence_count === 0 ? (
          <p className={own.noMoves}>이 지적에는 인용된 근거가 없습니다.</p>
        ) : null}
      </section>

      <section className={styles.section} aria-labelledby="issue-urls-heading">
        <h2 id="issue-urls-heading" className={styles.sectionTitle}>
          영향 URL {issue.affected_urls.length}개
        </h2>
        <ul className={styles.list}>
          {issue.affected_urls.map((url) => (
            <li key={url}>{url}</li>
          ))}
        </ul>
      </section>

      {issue.remediation_summary_ko !== null ? (
        <section className={styles.section} aria-labelledby="issue-fix-heading">
          <h2 id="issue-fix-heading" className={styles.sectionTitle}>
            조치 방법
          </h2>
          <Card title={`담당 ${ownerLabel(issue.remediation_owner)}`} headingLevel={3}>
            <p className={styles.prose}>{issue.remediation_summary_ko}</p>
            {issue.remediation_steps_ko !== null ? (
              <p className={styles.prose}>{issue.remediation_steps_ko}</p>
            ) : null}
            {issue.fix_example !== null ? (
              <pre className={own.excerpt}>{issue.fix_example}</pre>
            ) : null}
          </Card>
          {issue.reverification_note_ko !== null ? (
            <p className={styles.callout}>
              재측정 범위: {issue.reverification_note_ko} — 사이트 전체를 다시 진단하지
              않습니다.
            </p>
          ) : null}
        </section>
      ) : null}

      <section className={styles.section} aria-labelledby="issue-history-heading">
        <h2 id="issue-history-heading" className={styles.sectionTitle}>
          이력
        </h2>
        <p className={styles.callout}>{issue.recurrence.summary_ko}</p>
        <ul className={own.historyList}>
          {issue.history.map((entry) => (
            <li key={`${entry.at}-${entry.action}`} className={own.historyEntry}>
              <span className={own.historyWhen}>{formatWhen(entry.at)}</span>
              <span>{entry.summary_ko}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

/** 서버에서 그린다. 시간대를 한국 기준으로 고정해 두 곳에서 다른 시각이 보이지 않게 한다. */
function formatWhen(value: string): string {
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return value;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Seoul',
  }).format(at);
}
