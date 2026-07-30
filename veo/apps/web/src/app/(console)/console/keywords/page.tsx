import type { Metadata } from 'next';
import {
  Card,
  DATA_SOURCES,
  DATA_SOURCE_DESCRIPTIONS_KO,
  DATA_SOURCE_LABELS_KO,
  EmptyState,
} from '@veo/ui';

import { PermissionGate } from '@/components/PermissionGate';
import { readRecentKeywords } from '@/lib/keywords';
import { requireConsoleIdentity } from '@/lib/session';
import styles from '@/styles/page.module.css';

import { LookupForm } from './LookupForm';
import own from './keywords.module.css';

export const metadata: Metadata = {
  title: '키워드',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleKeywordsPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="keyword:read">
      <ConsoleKeywordsContent />
    </PermissionGate>
  );
}

async function ConsoleKeywordsContent() {
  const recent = await readRecentKeywords();

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

      <section className={styles.section} aria-labelledby="keywords-lookup-heading">
        <h2 id="keywords-lookup-heading" className={styles.sectionTitle}>
          키워드 조회
        </h2>
        <LookupForm />
      </section>

      {recent.ok && recent.data.entries.length > 0 ? (
        <section className={styles.section} aria-labelledby="keywords-recent-heading">
          <h2 id="keywords-recent-heading" className={styles.sectionTitle}>
            {recent.data.title_ko}
          </h2>
          {/*
            네이버가 발표하는 인기검색어 순위가 아니다. 우리 사용자가 최근 무엇을
            조회했는지일 뿐이고, 그렇게 적지 않으면 없는 권위를 빌려 쓰게 된다.
          */}
          <p className={styles.callout}>
            VEO 사용자가 최근 {recent.data.window_hours}시간 동안 조회한 키워드입니다.{' '}
            <strong>네이버가 발표하는 인기 순위가 아닙니다.</strong>
          </p>
          <ul className={own.recentList}>
            {recent.data.entries.map((entry) => (
              <li key={entry.normalized_keyword} className={own.recentItem}>
                {entry.normalized_keyword} · {entry.lookup_count}회
              </li>
            ))}
          </ul>
        </section>
      ) : null}

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

      {recent.ok ? null : (
        <EmptyState description="최근 조회 이력을 불러오지 못했습니다. 조회 자체는 위에서 바로 하실 수 있습니다." />
      )}
    </div>
  );
}
