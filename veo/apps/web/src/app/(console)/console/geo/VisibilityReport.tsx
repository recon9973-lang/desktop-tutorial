import { Card } from '@veo/ui';

import type { ObservationRun, Rate, VisibilityMetrics } from '@/lib/observations';

import styles from './geo.module.css';

/**
 * 관측 결과.
 *
 * 이 화면이 지키는 것은 전부 **구분**이다. 백엔드가 애써 나눠 둔 것을 화면에서 도로
 * 뭉개면 그 노력이 전부 사라진다.
 *
 * 1. **잴 수 없었던 것과 0%를 다르게 그린다.** 같은 회색 0%로 그리면 우리가 못 잰 것이
 *    고객 탓으로 보인다. `percent_text_ko` 를 그대로 쓰고 직접 포맷하지 않는다 —
 *    표본 3~4회 값에 소수점을 붙이면 감당 못 할 정밀도를 주장하게 된다.
 * 2. **못 한 일을 한 일과 같은 크기로 둔다.** 건너뛴 실행을 작게 그리면 절반만 실행된
 *    관측이 완전한 측정처럼 읽힌다.
 * 3. **주의사항을 접지 않는다.** 접힌 것은 읽히지 않고, 읽히지 않을 주의사항은 없는
 *    것과 같다.
 */
export function VisibilityReport({
  run,
  metrics,
}: {
  readonly run: ObservationRun;
  readonly metrics: VisibilityMetrics;
}) {
  return (
    <div className={styles.report}>
      {metrics.caveats_ko.length > 0 ? (
        <section className={styles.caveats} aria-label="이 숫자를 읽을 때 함께 알아야 하는 것">
          <h3 className={styles.caveatTitle}>먼저 읽어 주십시오</h3>
          <ul className={styles.caveatList}>
            {metrics.caveats_ko.map((caveat) => (
              <li key={caveat}>{caveat}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className={styles.rates}>
        <RateCard rate={metrics.mention_rate} meaning="AI 답변에 브랜드가 등장한 비율입니다." />
        <RateCard
          rate={metrics.citation_rate}
          meaning="출처를 확인할 수 있었던 답변 가운데 우리 사이트가 인용된 비율입니다."
        />
        <RateCard
          rate={metrics.prompt_coverage}
          meaning="던진 질문 가운데 한 번이라도 언급이 확인된 질문의 비율입니다."
        />
      </div>

      <Counts run={run} metrics={metrics} />
      <Cost run={run} />
    </div>
  );
}

/** 비율 하나. 값이 없을 때가 이 컴포넌트의 본체다. */
function RateCard({ rate, meaning }: { readonly rate: Rate; readonly meaning: string }) {
  const unmeasured = rate.value === null;

  return (
    <div className={unmeasured ? styles.rateCardUnmeasured : styles.rateCard}>
      <p className={styles.rateLabel}>{rate.label_ko}</p>
      {/* 엔진이 만든 문자열을 그대로 쓴다. 여기서 다시 포맷하면 규칙이 두 벌이 된다. */}
      <p className={unmeasured ? styles.rateValueUnmeasured : styles.rateValue}>
        {rate.percent_text_ko}
      </p>
      <p className={styles.rateDenominator}>
        {rate.denominator === 0
          ? '분모가 없습니다'
          : `${rate.denominator}회 중 ${rate.numerator}회`}
      </p>

      {rate.low !== null && rate.high !== null && !unmeasured ? (
        <p className={styles.interval}>
          95% 신뢰구간 {(rate.low * 100).toFixed(1)}% ~ {(rate.high * 100).toFixed(1)}%
        </p>
      ) : null}

      <p className={styles.rateMeaning}>{meaning}</p>

      {rate.note_ko !== '' ? <p className={styles.rateNote}>{rate.note_ko}</p> : null}

      {!unmeasured && !rate.is_comparison_grade ? (
        <p className={styles.rateNote}>
          표본이 비교 보고 기준(5회)에 못 미칩니다. <strong>경쟁사와 나란히 놓지
          마십시오.</strong>
        </p>
      ) : null}
    </div>
  );
}

/**
 * 한 일과 못 한 일.
 *
 * 넷을 같은 크기로 둔다. 건너뛴 실행을 작은 회색 글씨로 밀어 두면 부분 측정이 완전한
 * 측정처럼 읽히고, 그 위에서 계산한 비율은 분모가 틀렸다는 사실을 잃는다.
 */
function Counts({
  run,
  metrics,
}: {
  readonly run: ObservationRun;
  readonly metrics: VisibilityMetrics;
}) {
  return (
    <Card title="이 관측이 실제로 한 일" headingLevel={3} tone="flat">
      <dl className={styles.counts}>
        <Count label="계획한 실행" value={run.executions_planned} />
        <Count label="응답을 받은 실행" value={run.executions_valid} />
        <Count
          label="건너뛴 실행"
          value={run.executions_skipped}
          alarming={run.executions_skipped > 0}
        />
        <Count
          label="출처를 볼 수 있었던 응답"
          value={metrics.answers_with_visible_citations}
          alarming={metrics.answers_with_visible_citations === 0}
        />
      </dl>

      {run.stopped_reason !== null ? (
        <p className={styles.stopped}>
          <strong>중단됨</strong> — {run.stopped_reason}
        </p>
      ) : null}

      {!run.is_complete ? (
        <p className={styles.stopped}>
          <strong>부분 측정입니다.</strong> 계획한 실행을 다 하지 못했으므로, 위 비율은 실제로
          던진 질문에 대한 값이며 계획 전체에 대한 답이 아닙니다.
        </p>
      ) : null}

      <p className={styles.summary}>{run.summary_ko}</p>
    </Card>
  );
}

function Count({
  label,
  value,
  alarming = false,
}: {
  readonly label: string;
  readonly value: number;
  readonly alarming?: boolean;
}) {
  return (
    <div className={styles.count}>
      <dt className={styles.countLabel}>{label}</dt>
      <dd className={alarming ? styles.countValueAlarming : styles.countValue}>{value}</dd>
    </div>
  );
}

/** 비용. 모르는 것을 0원으로 적지 않는다. */
function Cost({ run }: { readonly run: ObservationRun }) {
  return (
    <Card title="비용" headingLevel={3} tone="flat">
      <p className={styles.cost}>
        확인된 비용 <strong>${run.total_cost_usd.toFixed(4)}</strong> (USD)
      </p>
      {run.unpriced_calls > 0 ? (
        <p className={styles.rateNote}>
          호출 {run.unpriced_calls}건은 가격표가 없어 비용을 계산하지 못했습니다.{' '}
          <strong>0원이라는 뜻이 아니라 모른다는 뜻입니다</strong> — 위 금액은 전체가 아니라
          일부입니다.
        </p>
      ) : null}
      <p className={styles.rateNote}>
        원화 환산은 하지 않습니다. 어느 시점의 환율로 바꿨는지가 남지 않으면 나중에 그
        숫자를 설명할 수 없습니다.
      </p>
    </Card>
  );
}
