import type { Metadata } from 'next';
import { Card, EmptyState, ScoreCard } from '@veo/ui';

import { PUBLISHED_SCORING_SPECS, specLabel } from '@/lib/scoring';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

export const metadata: Metadata = {
  title: 'GEO 준비도 · AI 가시성 관측',
};

const GEO_SPEC = PUBLISHED_SCORING_SPECS[1];


export default async function ConsoleGeoPage() {
  const identity = await requireConsoleIdentity();

  return (
    <PermissionGate identity={identity} permission="observation:read">
      <ConsoleGeoContent />
    </PermissionGate>
  );
}

function ConsoleGeoContent() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>GEO</h1>
        <p className={styles.lede}>
          GEO 화면은 두 가지를 완전히 분리해서 보여줍니다. 하나는 우리가 통제할 수 있는 페이지
          구조의 준비도이고, 다른 하나는 외부 AI 서비스의 응답을 표본으로 관측한 기록입니다.
        </p>
      </div>

      <p className={styles.callout}>
        준비도와 가시성 관측은 측정 대상도 방법도 다르므로, VEO는 두 결과를 하나의 점수로
        합치지 않습니다. 어느 화면에서도 합산 지표를 만들지 않습니다.
      </p>

      <div className={styles.separatedSections}>
        <section className={styles.readinessSection} aria-labelledby="geo-readiness-heading">
          <div className={styles.header}>
            <p className={styles.eyebrow}>1 / 2 · 구조 평가</p>
            <h2 id="geo-readiness-heading" className={styles.sectionTitle}>
              GEO 준비도
            </h2>
            <p className={styles.sectionLede}>
              AI 답변 엔진이 페이지에 접근하고, 본문을 추출하고, 근거를 검증할 수 있는
              구조인지를 채점 명세에 따라 평가합니다. 우리가 고칠 수 있는 영역입니다.
            </p>
          </div>

          {GEO_SPEC === undefined ? null : (
            <ScoreCard
              title="GEO 준비도"
              score={null}
              specVersion={specLabel(GEO_SPEC)}
              coverage={0}
              confidence={0}
              note="평가된 항목이 없어 점수를 계산하지 않았습니다."
            />
          )}

          <Card title="평가하는 것" headingLevel={3} tone="flat">
            <ul className={styles.list}>
              <li>AI 크롤러 접근 허용 및 색인 가능 여부</li>
              <li>본문 추출 가능성과 의미 구조</li>
              <li>작성자·출처·갱신 시각 등 검증 가능한 근거 표기</li>
              <li>구조화 데이터와 화면에 보이는 내용의 일치</li>
            </ul>
          </Card>

          <EmptyState description="점검을 실행하면 항목별 준비도 판정이 이곳에 표시됩니다." />
        </section>

        <hr className={styles.divider} />

        <section className={styles.observationSection} aria-labelledby="geo-observation-heading">
          <div className={styles.header}>
            <p className={styles.eyebrow}>2 / 2 · 외부 관측</p>
            <h2 id="geo-observation-heading" className={styles.sectionTitle}>
              AI 가시성 관측
            </h2>
            <p className={styles.sectionLede}>
              지정한 질의에 대해 외부 AI 서비스가 우리 사이트를 언급하거나 인용했는지를 표본
              관측한 기록입니다. 점수가 아니라 관측 결과이며, 같은 질의라도 응답은 달라질 수
              있습니다.
            </p>
          </div>

          <Card title="관측 기록에 반드시 함께 남기는 것" headingLevel={3} tone="flat">
            <ul className={styles.list}>
              <li>관측을 수행한 시각</li>
              <li>사용한 질의와 표본 수</li>
              <li>관측 대상 서비스</li>
              <li>언급·인용이 확인되지 않았다는 사실 자체도 기록</li>
            </ul>
          </Card>

          <EmptyState description="관측을 실행하면 질의별 관측 기록이 수집 시각과 함께 이곳에 표시됩니다." />

          <p className={styles.prose}>
            관측되지 않았다는 것은 그 시점의 표본에서 확인되지 않았다는 뜻이며, 앞으로도 노출되지
            않는다는 뜻이 아닙니다. VEO는 이 결과를 준비도 점수에 반영하지 않습니다.
          </p>
        </section>
      </div>
    </div>
  );
}
