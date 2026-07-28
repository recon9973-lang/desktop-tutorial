import Link from 'next/link';
import { Card, StatusChip } from '@veo/ui';

import { PUBLIC_NAV } from '@/lib/navigation';
import styles from '@/styles/page.module.css';

export default function HomePage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>SEO · GEO · Naver Keyword Intelligence</p>
        <h1 className={styles.heroTitle}>
          검색엔진과 AI 답변 엔진이 내 사이트를 읽을 수 있는 상태인지 확인합니다
        </h1>
        <p className={styles.lede}>
          VEO는 사이트의 기술·구조 준비도를 공개된 채점 명세에 따라 점검하고, 네이버 검색
          수요를 출처와 수집 시각과 함께 보여줍니다. 판정 하나하나에 근거와 신뢰도를 남깁니다.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="veo-tools-heading">
        <h2 id="veo-tools-heading" className={styles.sectionTitle}>
          무료 점검 도구
        </h2>
        <div className={styles.grid}>
          {PUBLIC_NAV.map((item) => (
            <Link key={item.href} href={item.href} className={styles.linkCard}>
              <h3 className={styles.linkCardTitle}>{item.label}</h3>
              <p className={styles.linkCardText}>{item.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className={styles.section} aria-labelledby="veo-verdicts-heading">
        <h2 id="veo-verdicts-heading" className={styles.sectionTitle}>
          판정 표기 방식
        </h2>
        <p className={styles.sectionLede}>
          모든 점검 항목은 다섯 가지 상태 중 하나로 표시됩니다. 색만으로 구분하지 않고 아이콘
          모양과 한국어 라벨을 함께 사용합니다.
        </p>
        <Card title="판정 상태" headingLevel={3}>
          <dl className={styles.legendList}>
            <div className={styles.legendRow}>
              <dt className={styles.legendTerm}>
                <StatusChip status="PASS" />
              </dt>
              <dd className={styles.legendDescription}>
                해당 기준을 충족했습니다.
              </dd>
            </div>
            <div className={styles.legendRow}>
              <dt className={styles.legendTerm}>
                <StatusChip status="WARNING" />
              </dt>
              <dd className={styles.legendDescription}>
                일부만 충족했거나 개선 여지가 있습니다.
              </dd>
            </div>
            <div className={styles.legendRow}>
              <dt className={styles.legendTerm}>
                <StatusChip status="FAIL" />
              </dt>
              <dd className={styles.legendDescription}>
                기준을 충족하지 못했습니다. 조치가 필요합니다.
              </dd>
            </div>
            <div className={styles.legendRow}>
              <dt className={styles.legendTerm}>
                <StatusChip status="NOT_APPLICABLE" />
              </dt>
              <dd className={styles.legendDescription}>
                이 페이지 유형에는 적용되지 않는 항목입니다. 감점이 아니며 채점 분모에서
                제외됩니다.
              </dd>
            </div>
            <div className={styles.legendRow}>
              <dt className={styles.legendTerm}>
                <StatusChip status="UNKNOWN" />
              </dt>
              <dd className={styles.legendDescription}>
                판정에 필요한 근거를 수집하지 못했습니다. 실패로 처리하지 않고 측정 범위에서
                제외한 뒤 그 사실을 함께 표시합니다.
              </dd>
            </div>
          </dl>
        </Card>
      </section>

      <section className={styles.section} aria-labelledby="veo-scope-heading">
        <h2 id="veo-scope-heading" className={styles.sectionTitle}>
          VEO가 하지 않는 것
        </h2>
        <ul className={styles.list}>
          <li>검색 순위를 예측하거나 보장하지 않습니다.</li>
          <li>실시간 지표라고 표기하지 않습니다. 모든 값에 수집 시각을 남깁니다.</li>
          <li>준비도 점수와 AI 가시성 관측 결과를 하나의 점수로 합치지 않습니다.</li>
          <li>근거 없이 추정한 숫자를 측정값처럼 보여주지 않습니다.</li>
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="veo-method-heading">
        <h2 id="veo-method-heading" className={styles.sectionTitle}>
          채점 방법론
        </h2>
        <p className={styles.prose}>
          채점 가중치, 심각도 계수, 상한 규칙은 버전이 붙은 공개 명세로 관리됩니다. 리포트에는
          어떤 명세 버전으로 계산했는지, 측정 범위와 신뢰도가 얼마인지 항상 함께 표시됩니다.
          방법론은 VEO-LAB이, 구현은 VENOM이 담당합니다.
        </p>
        <p>
          <Link href="/console/scoring-versions">적용 중인 채점 기준 버전 보기</Link>
        </p>
      </section>
    </div>
  );
}
