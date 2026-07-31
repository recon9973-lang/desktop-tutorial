import { Card } from '@veo/ui';

import type { RiskFindings } from '@/lib/observations';

import styles from './geo.module.css';

/**
 * 답변 위험 — 이 화면이 지키는 것은 **0 의 뜻**이다.
 *
 * "위험 0건" 은 두 가지로 읽힐 수 있고, 둘은 정반대다.
 *
 *   (가) 다 재 봤는데 아무 문제가 없었다
 *   (나) 재는 항목이 아직 하나뿐이다
 *
 * 지금은 (나) 다. 방법론이 정의한 위험 8종 가운데 규칙으로 낼 수 있는 것은 동명 업체
 * 혼동 하나뿐이고, 나머지 7종은 언어모델 판정이나 고객 사이트 대조가 있어야 한다.
 * 그 사실을 0 옆에 적지 않으면 우리가 안 재는 것을 "없다" 로 보고하는 셈이 된다(0-A).
 *
 * 그리고 **종합 점수를 만들지 않는다.** 심각도별 건수만 센다. 위험을 한 숫자로 접으면
 * 치명 1건과 낮음 10건이 같은 값이 될 수 있고, 그 둘은 대응이 전혀 다르다.
 */
export function RiskReport({ findings }: { readonly findings: RiskFindings }) {
  const held = findings.internal.items;

  return (
    <Card title="답변 위험" headingLevel={3} tone="flat">
      {held.length === 0 ? (
        <p className={styles.stopped}>이번 실행에서 사람이 확인해야 할 건은 없습니다.</p>
      ) : (
        <ul className={styles.riskList}>
          {held.map((item) => (
            <li key={item.assessment_id} className={styles.riskItem}>
              <p className={styles.riskHead}>
                <span className={styles.riskBand}>{item.assessment.band_label_ko}</span>
                <span className={styles.riskStage}>{item.review.stage_label_ko}</span>
              </p>
              {/*
                검수자는 기계가 실제로 본 글자를 봐야 판단할 수 있다. 요약해서 보여주면
                "백세온담한의원" 과 "온담한의원" 의 차이가 사라진다.
              */}
              <p className={styles.riskQuote}>&ldquo;{item.assessment.claim_text}&rdquo;</p>
              <p className={styles.riskWhy}>{item.assessment.automated.rationale_ko}</p>
              <p className={styles.riskGate}>{item.explanation_ko}</p>
            </li>
          ))}
        </ul>
      )}

      <p className={styles.riskNoScore}>
        위험 영역에는 종합 점수가 없습니다. 심각도별 건수만 보고합니다 — 치명 1건과 낮음
        10건을 한 숫자로 접으면 대응이 전혀 다른 둘이 같은 값이 됩니다.
      </p>

      <section className={styles.riskGaps} aria-label="아직 재지 않는 위험 유형">
        <h4 className={styles.riskGapsTitle}>
          아직 재지 않는 항목 {findings.kinds_not_yet_produced.length}종
        </h4>
        <p className={styles.riskGapsLede}>
          위 목록이 비어 있다고 위험이 없는 것이 아닙니다. 지금 재는 위험 유형은 방법론
          8종 가운데 <strong>동명 업체 혼동 하나</strong>입니다.
        </p>
        <dl className={styles.riskGapList}>
          {findings.kinds_not_yet_produced.map((gap) => (
            <div key={gap.kind} className={styles.riskGapRow}>
              <dt>{gap.kind}</dt>
              <dd>{gap.reason_ko}</dd>
            </div>
          ))}
        </dl>
      </section>
    </Card>
  );
}
