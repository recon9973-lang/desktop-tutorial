import type { Metadata } from 'next';
import { Card, EmptyState } from '@veo/ui';

import styles from '@/styles/page.module.css';

export const metadata: Metadata = {
  title: 'GEO 준비도 점검',
  description:
    'AI 답변 엔진이 페이지에 접근하고, 내용을 추출하고, 사실을 검증할 수 있는 구조인지 점검합니다.',
};

export default function GeoToolPage() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>무료 도구</p>
        <h1 className={styles.title}>GEO 준비도 점검</h1>
        <p className={styles.lede}>
          AI 답변 엔진이 페이지에 접근하고, 내용을 추출하고, 근거를 확인할 수 있는 구조인지
          점검합니다. 실제로 AI 답변에 인용되었는지는 이 점수가 아니라 별도의 가시성 관측
          결과로만 확인합니다.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="geo-result-heading">
        <h2 id="geo-result-heading" className={styles.sectionTitle}>
          점검 결과
        </h2>
        <EmptyState description="이 화면은 아직 측정 엔진과 연결되어 있지 않습니다. 연결되면 점검한 URL의 준비도 결과가 근거와 함께 이곳에 표시됩니다." />
      </section>

      <section className={styles.section} aria-labelledby="geo-separation-heading">
        <h2 id="geo-separation-heading" className={styles.sectionTitle}>
          준비도와 가시성은 다른 지표입니다
        </h2>
        <div className={styles.gridTwo}>
          <Card
            title="GEO 준비도"
            headingLevel={3}
            description="우리가 통제할 수 있는 페이지 구조를 평가합니다."
          >
            <ul className={styles.list}>
              <li>AI 크롤러 접근 허용 여부</li>
              <li>본문 추출 가능성과 의미 구조</li>
              <li>출처·작성자·갱신 시각 등 검증 가능한 근거 표기</li>
              <li>구조화 데이터와 화면 내용의 일치</li>
            </ul>
          </Card>
          <Card
            title="AI 가시성 관측"
            headingLevel={3}
            description="외부 AI 서비스의 응답을 표본으로 관측한 기록입니다."
          >
            <ul className={styles.list}>
              <li>지정한 질의에 대해 언급·인용이 관측되었는지 여부</li>
              <li>관측을 수행한 시각과 표본 수</li>
              <li>같은 질의라도 응답이 달라질 수 있다는 전제</li>
            </ul>
          </Card>
        </div>
        <p className={styles.callout}>
          두 결과는 서로 다른 것을 측정하므로 하나의 점수로 합치지 않습니다. 준비도가 높아도
          가시성이 관측되지 않을 수 있고, 그 반대도 가능합니다.
        </p>
      </section>
    </div>
  );
}
