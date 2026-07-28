import type { Metadata } from 'next';
import Link from 'next/link';
import { Card, EmptyState, ScoreCard } from '@veo/ui';

import { PUBLISHED_SCORING_SPECS, specLabel } from '@/lib/scoring';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '대시보드',
};

const [SEO_SPEC, GEO_SPEC] = PUBLISHED_SCORING_SPECS;


export default async function ConsoleDashboardPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="scan:read">
      <ConsoleDashboardContent />
    </PermissionGate>
  );
}

function ConsoleDashboardContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>대시보드</h1>
        <p className={styles.lede}>
          등록한 프로젝트의 준비도와 조치가 필요한 이슈를 한 곳에서 확인합니다. 아직 측정을
          실행하지 않았으므로 점수는 계산되지 않았습니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="dashboard-scores-heading">
        <h2 id="dashboard-scores-heading" className={styles.sectionTitle}>
          준비도 요약
        </h2>
        <div className={styles.gridTwo}>
          {SEO_SPEC === undefined ? null : (
            <ScoreCard
              title="SEO 기술 준비도"
              score={null}
              specVersion={specLabel(SEO_SPEC)}
              coverage={0}
              confidence={0}
              note="아직 이 프로젝트에서 점검을 실행하지 않아 평가된 항목이 없습니다."
            />
          )}
          {GEO_SPEC === undefined ? null : (
            <ScoreCard
              title="GEO 준비도"
              score={null}
              specVersion={specLabel(GEO_SPEC)}
              coverage={0}
              confidence={0}
              note="아직 이 프로젝트에서 점검을 실행하지 않아 평가된 항목이 없습니다."
            />
          )}
        </div>
        <p className={styles.callout}>
          측정 범위가 0%라는 것은 점수가 0점이라는 뜻이 아닙니다. 평가된 항목이 없어 점수를
          계산할 수 없는 상태를 그대로 표시한 것입니다.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="dashboard-activity-heading">
        <h2 id="dashboard-activity-heading" className={styles.sectionTitle}>
          최근 점검 기록
        </h2>
        <EmptyState description="점검을 실행하면 실행 시각, 적용한 채점 기준 버전, 결과 요약이 이곳에 쌓입니다." />
      </section>

      <section className={styles.section} aria-labelledby="dashboard-next-heading">
        <h2 id="dashboard-next-heading" className={styles.sectionTitle}>
          바로 가기
        </h2>
        <div className={styles.grid}>
          <Card title="프로젝트" headingLevel={3} tone="flat">
            <p className={styles.linkCardText}>
              측정 대상 사이트를 등록하고 점검 범위를 정합니다.
            </p>
            <p>
              <Link href="/console/projects">프로젝트로 이동</Link>
            </p>
          </Card>
          <Card title="채점 기준 버전" headingLevel={3} tone="flat">
            <p className={styles.linkCardText}>
              현재 적용 중인 채점 명세와 발효 시각을 확인합니다.
            </p>
            <p>
              <Link href="/console/scoring-versions">채점 기준 버전으로 이동</Link>
            </p>
          </Card>
        </div>
      </section>
    </div>
  );
}
