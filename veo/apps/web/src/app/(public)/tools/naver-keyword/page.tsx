import type { Metadata } from 'next';
import { Card, DATA_SOURCES, DATA_SOURCE_DESCRIPTIONS_KO, DATA_SOURCE_LABELS_KO } from '@veo/ui';

import styles from '@/styles/page.module.css';

import { KeywordLookupForm } from './KeywordLookupForm';

export const metadata: Metadata = {
  title: '네이버 키워드 점검',
  description:
    '네이버 검색 수요와 경쟁 상황을 출처와 수집 시각을 밝혀 보여줍니다. 데이터랩 지수는 절대 검색량이 아닙니다.',
};

export default function NaverKeywordToolPage() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>무료 도구</p>
        <h1 className={styles.title}>네이버 키워드 점검</h1>
        <p className={styles.lede}>
          네이버 검색 수요와 경쟁 상황을 확인합니다. 화면에 표시되는 모든 값에는 어느 출처에서
          언제 수집했는지가 함께 표시됩니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="keyword-lookup-heading">
        <h2 id="keyword-lookup-heading" className={styles.sectionTitle}>
          키워드 조회
        </h2>
        <KeywordLookupForm />
      </section>

      <section className={styles.section} aria-labelledby="keyword-sources-heading">
        <h2 id="keyword-sources-heading" className={styles.sectionTitle}>
          값의 출처 구분
        </h2>
        <Card title="VEO가 사용하는 출처" headingLevel={3}>
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
          네이버 데이터랩은 기간·기기·성별 등 조건에 따라 상대적으로 정규화된 지수를
          제공합니다. 검색 횟수 자체가 아니므로 다른 출처의 절대값과 직접 비교하지 않습니다.
        </p>
      </section>
    </div>
  );
}
