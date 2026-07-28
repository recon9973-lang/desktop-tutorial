import type { Metadata } from 'next';
import { Card, EmptyState, StatusChip } from '@veo/ui';

import styles from '@/styles/page.module.css';

export const metadata: Metadata = {
  title: 'SEO 기술 준비도 점검',
  description:
    '검색엔진이 사이트를 발견·크롤링·해석·제공할 수 있는지 점검합니다. 검색 순위 예측이 아닙니다.',
};

const CATEGORIES = [
  {
    name: '크롤링·색인 가능성',
    detail: '검색엔진이 URL을 가져오고 색인할 수 있는지 확인합니다.',
  },
  {
    name: '온페이지 의미 구조',
    detail: '제목, 헤딩, 대체 텍스트 등 문서 구조가 해석 가능한지 확인합니다.',
  },
  {
    name: '콘텐츠 아키텍처',
    detail: '내부 링크, 브레드크럼, 페이지네이션 신호를 확인합니다.',
  },
  {
    name: '구조화 데이터',
    detail: 'JSON-LD가 파싱되고 화면 내용과 일치하는지 확인합니다.',
  },
  {
    name: '성능·사용성',
    detail: '핵심 웹 지표와 모바일 사용성 관련 항목을 확인합니다.',
  },
];

export default function SeoToolPage() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>무료 도구</p>
        <h1 className={styles.title}>SEO 기술 준비도 점검</h1>
        <p className={styles.lede}>
          검색엔진이 사이트를 발견하고, 크롤링하고, 해석하고, 결과에 제공할 수 있는 기술·운영
          준비도를 점검합니다. 검색 순위를 예측하거나 보장하는 값이 아닙니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="seo-result-heading">
        <h2 id="seo-result-heading" className={styles.sectionTitle}>
          점검 결과
        </h2>
        <EmptyState description="이 화면은 아직 측정 엔진과 연결되어 있지 않습니다. 연결되면 점검한 URL의 결과가 근거와 함께 이곳에 표시됩니다." />
      </section>

      <section className={styles.section} aria-labelledby="seo-categories-heading">
        <h2 id="seo-categories-heading" className={styles.sectionTitle}>
          점검 영역
        </h2>
        <Card title="채점 명세가 정의하는 영역" headingLevel={3}>
          <dl className={styles.definitionList}>
            {CATEGORIES.map((category) => (
              <div key={category.name} className={styles.definitionRow}>
                <dt>{category.name}</dt>
                <dd>{category.detail}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <p className={styles.callout}>
          영역별 가중치와 심각도 계수는 코드가 아니라 버전이 붙은 채점 명세
          <span className={styles.token}> veo.seo.readiness </span>
          에만 정의되어 있습니다.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="seo-verdict-heading">
        <h2 id="seo-verdict-heading" className={styles.sectionTitle}>
          판정 읽는 법
        </h2>
        <dl className={styles.legendList}>
          <div className={styles.legendRow}>
            <dt className={styles.legendTerm}>
              <StatusChip status="NOT_APPLICABLE" />
            </dt>
            <dd className={styles.legendDescription}>
              해당 사이트에 존재하지 않는 요소는 감점하지 않고 채점 분모에서 제외합니다.
            </dd>
          </div>
          <div className={styles.legendRow}>
            <dt className={styles.legendTerm}>
              <StatusChip status="UNKNOWN" />
            </dt>
            <dd className={styles.legendDescription}>
              근거를 수집하지 못한 항목은 실패로 처리하지 않고, 측정 범위를 낮춘 사실로 남깁니다.
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
