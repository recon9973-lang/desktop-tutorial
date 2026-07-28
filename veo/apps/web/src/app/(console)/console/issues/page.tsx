import type { Metadata } from 'next';
import { Card, EmptyState } from '@veo/ui';

import { SEVERITIES } from '@/lib/scoring';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '이슈',
};


export default async function ConsoleIssuesPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="issue:read">
      <ConsoleIssuesContent />
    </PermissionGate>
  );
}

function ConsoleIssuesContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>이슈</h1>
        <p className={styles.lede}>
          점검에서 실패 또는 주의로 판정된 항목을 심각도와 담당 역할별로 모아 봅니다. 각 이슈는
          어떤 검사에서 어떤 근거로 나왔는지를 함께 보관합니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="issues-list-heading">
        <h2 id="issues-list-heading" className={styles.sectionTitle}>
          조치가 필요한 항목
        </h2>
        <EmptyState description="점검을 실행하면 실패·주의로 판정된 항목이 근거와 함께 이곳에 모입니다." />
      </section>

      <section className={styles.section} aria-labelledby="issues-severity-heading">
        <h2 id="issues-severity-heading" className={styles.sectionTitle}>
          심각도 구분
        </h2>
        <Card title="채점 명세가 정의하는 심각도" headingLevel={3}>
          <dl className={styles.definitionList}>
            {SEVERITIES.map((severity) => (
              <div key={severity.id} className={styles.definitionRow}>
                <dt>
                  {severity.label} <span className={styles.token}>{severity.id}</span>
                </dt>
                <dd>{severity.meaning}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <p className={styles.callout}>
          심각도별 감점 계수는 프론트엔드가 아니라 채점 명세에만 정의되어 있습니다. 화면은 계산
          결과와 그 근거만 표시합니다.
        </p>
      </section>
    </div>
  );
}
