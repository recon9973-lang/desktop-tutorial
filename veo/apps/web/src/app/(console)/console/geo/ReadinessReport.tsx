import { Card } from '@veo/ui';

import type { GeoCategory, GeoReadiness } from '@/lib/observations';

import styles from './geo.module.css';

/**
 * GEO 준비도 결과.
 *
 * 이 화면이 반드시 지키는 것: **점수와 노출 차단은 나란히 있되 섞이지 않는다.**
 * 95점이면서 동시에 노출 차단일 수 있다 — 구조는 훌륭한데 robots 로 막아 둔 사이트가
 * 정확히 그 모습이다. 차단을 점수에 반영해 깎아 버리면 "무엇을 고쳐야 하는가" 가
 * 사라진다. 하나는 설정 한 줄이고 다른 하나는 몇 주짜리 작업이다.
 */
export function ReadinessReport({ report }: { readonly report: GeoReadiness }) {
  const { readiness, exposure } = report;
  const scored = readiness.score !== null;

  return (
    <div className={styles.report}>
      <p className={styles.scopeNotice}>{report.scope_notice_ko}</p>

      {exposure.blocked ? (
        <section className={styles.blocked} aria-label="노출 차단">
          <h3 className={styles.caveatTitle}>AI 엔진이 이 사이트에 접근할 수 없습니다</h3>
          <p className={styles.rateNote}>
            아래 점수와 <strong>별개의 사실</strong>입니다. 점수가 높아도 차단돼 있으면 AI
            답변에 나올 수 없습니다.
          </p>
          <ul className={styles.caveatList}>
            {exposure.gates.map((gate) => (
              <li key={gate.gate_id}>
                <strong>{gate.label_ko}</strong>
                {gate.description_ko === null ? null : ` — ${gate.description_ko}`}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className={scored ? styles.rateCard : styles.rateCardUnmeasured}>
        <p className={styles.rateLabel}>GEO 준비도 · {report.target_url}</p>
        <p className={scored ? styles.rateValue : styles.rateValueUnmeasured}>
          {scored ? `${readiness.score?.toFixed(1)}점` : '점수를 낼 수 없습니다'}
        </p>
        {readiness.band_label_ko === null ? null : (
          <p className={styles.rateDenominator}>{readiness.band_label_ko}</p>
        )}
        <p className={styles.interval}>
          측정 범위 {(readiness.coverage * 100).toFixed(0)}% · 신뢰도{' '}
          {(readiness.confidence * 100).toFixed(0)}% · 명세 {readiness.spec_version}
        </p>
        <p className={styles.rateMeaning}>{report.summary_ko}</p>
      </div>

      <Card title="영역별" headingLevel={3} tone="flat">
        <ul className={styles.categoryList}>
          {readiness.categories.map((category) => (
            <CategoryRow key={category.category_id} category={category} />
          ))}
        </ul>
      </Card>

      {report.notes_ko.length > 0 ? (
        <section className={styles.caveats} aria-label="함께 알아야 하는 것">
          <h3 className={styles.caveatTitle}>함께 알아야 하는 것</h3>
          <ul className={styles.caveatList}>
            {report.notes_ko.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className={styles.pending}>
        이 결과는 <strong>저장되지 않습니다.</strong> 화면을 새로 고치면 사라지며, 다시
        보시려면 다시 측정해야 합니다 — 관측 기록과 달리 준비도 진단은 아직 이력이 남지
        않습니다.
      </p>
    </div>
  );
}

/**
 * 한 영역.
 *
 * 못 잰 항목 수를 실패 항목 수와 **같은 자리에** 둔다. 측정 불가를 빼고 보여주면 그
 * 영역이 실제보다 잘 나온 것처럼 읽히는데, 그 배점은 분모에 그대로 남아 있다.
 */
function CategoryRow({ category }: { readonly category: GeoCategory }) {
  const scored = category.score !== null;
  return (
    <li className={styles.categoryRow}>
      <div className={styles.categoryHead}>
        <span className={styles.categoryName}>{category.name_ko}</span>
        <span className={scored ? styles.categoryScore : styles.categoryUnmeasured}>
          {scored ? `${category.score?.toFixed(1)}점` : '측정 불가'}
        </span>
      </div>
      <p className={styles.categoryMeta}>
        배점 {category.weight}점 · 실패 {category.failing_check_ids.length}개 · 측정 불가{' '}
        {category.unknown_check_ids.length}개 · 해당 없음{' '}
        {category.not_applicable_check_ids.length}개
      </p>
    </li>
  );
}
