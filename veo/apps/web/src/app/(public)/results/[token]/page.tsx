import type { Metadata } from 'next';
import { Card, EmptyState } from '@veo/ui';

import styles from '@/styles/page.module.css';

export const metadata: Metadata = {
  title: '공유 리포트',
  description: '공유 링크로 열람하는 VEO 점검 리포트입니다.',
  robots: { index: false, follow: false },
};

interface ResultsPageProps {
  params: Promise<{ token: string }>;
}

export default async function ResultsPage({ params }: ResultsPageProps) {
  const { token } = await params;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>공유 리포트</p>
        <h1 className={styles.title}>점검 리포트</h1>
        <p className={styles.lede}>
          이 페이지는 공유 링크로 열람하는 읽기 전용 리포트입니다. 로그인 없이 열 수 있으므로
          링크를 받은 사람만 볼 수 있도록 관리해 주세요.
        </p>
      </div>

      <section className={styles.section} aria-labelledby="report-meta-heading">
        <h2 id="report-meta-heading" className={styles.sectionTitle}>
          리포트 정보
        </h2>
        <Card title="공유 링크" headingLevel={3}>
          <dl className={styles.definitionList}>
            <div className={styles.definitionRow}>
              <dt>공유 토큰</dt>
              <dd>
                <span className={styles.token}>{token}</span>
              </dd>
            </div>
            <div className={styles.definitionRow}>
              <dt>열람 범위</dt>
              <dd>읽기 전용입니다. 이 링크로는 프로젝트 설정을 변경할 수 없습니다.</dd>
            </div>
          </dl>
        </Card>
      </section>

      <section className={styles.section} aria-labelledby="report-body-heading">
        <h2 id="report-body-heading" className={styles.sectionTitle}>
          리포트 내용
        </h2>
        <EmptyState description="이 화면은 아직 리포트 API와 연결되어 있지 않습니다. 연결되면 이 토큰에 해당하는 점검 결과가 채점 기준 버전·측정 범위·신뢰도와 함께 표시됩니다." />
      </section>
    </div>
  );
}
