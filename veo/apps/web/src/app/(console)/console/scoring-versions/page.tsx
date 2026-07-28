import type { Metadata } from 'next';
import { Card, DataSourceBadge } from '@veo/ui';

import { PUBLISHED_SCORING_SPECS } from '@/lib/scoring';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '채점 기준 버전',
};


export default async function ConsoleScoringVersionsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scoring_spec:read">
      <ConsoleScoringVersionsContent />
    </PermissionGate>
  );
}

function ConsoleScoringVersionsContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>채점 기준 버전</h1>
        <p className={styles.lede}>
          모든 점수는 버전이 붙은 채점 명세로 계산됩니다. 명세가 바뀌면 점수도 달라질 수 있으므로,
          리포트에는 계산에 사용한 버전이 항상 함께 기록됩니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="specs-heading">
        <h2 id="specs-heading" className={styles.sectionTitle}>
          발행된 명세
        </h2>
        <div className={styles.gridTwo}>
          {PUBLISHED_SCORING_SPECS.map((spec) => (
            <Card
              key={spec.specId}
              title={spec.domain}
              headingLevel={3}
              description={spec.meaning}
              footer={
                <DataSourceBadge source="CALCULATED" collectedAt={spec.effectiveAt} />
              }
            >
              <dl className={styles.definitionList}>
                <div className={styles.definitionRow}>
                  <dt>명세 ID</dt>
                  <dd>
                    <span className={styles.token}>{spec.specId}</span>
                  </dd>
                </div>
                <div className={styles.definitionRow}>
                  <dt>버전</dt>
                  <dd>{spec.version}</dd>
                </div>
                <div className={styles.definitionRow}>
                  <dt>상태</dt>
                  <dd>{spec.status}</dd>
                </div>
                <div className={styles.definitionRow}>
                  <dt>방법론</dt>
                  <dd>{spec.methodologyOwner}</dd>
                </div>
                <div className={styles.definitionRow}>
                  <dt>구현</dt>
                  <dd>{spec.implementationOwner}</dd>
                </div>
              </dl>
            </Card>
          ))}
        </div>
      </section>

      <section className={styles.section} aria-labelledby="specs-policy-heading">
        <h2 id="specs-policy-heading" className={styles.sectionTitle}>
          버전 취급 규칙
        </h2>
        <ul className={styles.list}>
          <li>서로 다른 명세 버전으로 계산한 점수는 직접 비교하지 않습니다.</li>
          <li>가중치·심각도·상한 값은 명세에만 존재하며 화면이나 코드에 복제하지 않습니다.</li>
          <li>발행된 명세는 수정하지 않고 새 버전으로 발행합니다.</li>
        </ul>
      </section>
    </div>
  );
}
