import type { Metadata } from 'next';
import { CHECK_STATUSES, CHECK_STATUS_DESCRIPTORS, Card, EmptyState, ScoreCard, StatusChip } from '@veo/ui';

import { PUBLISHED_SCORING_SPECS, specLabel } from '@/lib/scoring';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: 'SEO 기술 준비도',
};

const SEO_SPEC = PUBLISHED_SCORING_SPECS[0];


export default async function ConsoleSeoPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <ConsoleSeoContent />
    </PermissionGate>
  );
}

function ConsoleSeoContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>SEO 기술 준비도</h1>
        <p className={styles.lede}>
          검색엔진이 사이트를 발견·크롤링·해석·제공할 수 있는 상태인지 항목별로 확인합니다.
          순위 예측이 아니라 준비도입니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="seo-score-heading">
        <h2 id="seo-score-heading" className={styles.sectionTitle}>
          현재 점수
        </h2>
        {SEO_SPEC === undefined ? null : (
          <ScoreCard
            title="SEO 기술 준비도"
            score={null}
            specVersion={specLabel(SEO_SPEC)}
            coverage={0}
            confidence={0}
            note="평가된 항목이 없어 점수를 계산하지 않았습니다."
          />
        )}
      </section>

      <section className={styles.section} aria-labelledby="seo-checks-heading">
        <h2 id="seo-checks-heading" className={styles.sectionTitle}>
          항목별 판정
        </h2>
        <EmptyState description="점검을 실행하면 항목별 판정과 그 근거가 이곳에 표시됩니다." />
      </section>

      <section className={styles.section} aria-labelledby="seo-legend-heading">
        <h2 id="seo-legend-heading" className={styles.sectionTitle}>
          판정 표기 안내
        </h2>
        <Card title="다섯 가지 판정 상태" headingLevel={3}>
          <dl className={styles.legendList}>
            {CHECK_STATUSES.map((status) => (
              <div key={status} className={styles.legendRow}>
                <dt className={styles.legendTerm}>
                  <StatusChip status={status} />
                </dt>
                <dd className={styles.legendDescription}>
                  {CHECK_STATUS_DESCRIPTORS[status].meaning}
                </dd>
              </div>
            ))}
          </dl>
        </Card>
      </section>
    </div>
  );
}
