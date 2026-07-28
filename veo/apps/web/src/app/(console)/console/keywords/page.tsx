import type { Metadata } from 'next';
import {
  Card,
  DATA_SOURCES,
  DATA_SOURCE_DESCRIPTIONS_KO,
  DATA_SOURCE_LABELS_KO,
  EmptyState,
} from '@veo/ui';

import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: '키워드',
};


export default async function ConsoleKeywordsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="keyword:read">
      <ConsoleKeywordsContent />
    </PermissionGate>
  );
}

function ConsoleKeywordsContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>네이버 키워드</h1>
        <p className={styles.lede}>
          네이버 검색 수요와 경쟁 상황을 확인합니다. 값마다 어느 출처에서 언제 수집했는지를
          함께 표시하며, 서로 다른 출처의 값을 하나로 합쳐 표시하지 않습니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="keywords-list-heading">
        <h2 id="keywords-list-heading" className={styles.sectionTitle}>
          키워드 목록
        </h2>
        <EmptyState description="등록된 키워드가 없습니다. 키워드를 등록하면 출처별 수집 값과 수집 시각이 이곳에 표시됩니다." />
      </section>

      <section className={styles.section} aria-labelledby="keywords-source-heading">
        <h2 id="keywords-source-heading" className={styles.sectionTitle}>
          출처 표기 규칙
        </h2>
        <Card title="출처 구분" headingLevel={3}>
          <dl className={styles.definitionList}>
            {DATA_SOURCES.map((source) => (
              <div key={source} className={styles.definitionRow}>
                <dt>{DATA_SOURCE_LABELS_KO[source]}</dt>
                <dd>{DATA_SOURCE_DESCRIPTIONS_KO[source]}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <p className={styles.callout}>
          데이터랩 지수는 조건에 따라 정규화된 상대값입니다. 검색광고 API의 조회수와 같은 축에
          놓고 비교하지 않으며, 두 값을 곱하거나 더해 새로운 지표를 만들지 않습니다.
        </p>
      </section>
    </div>
  );
}
