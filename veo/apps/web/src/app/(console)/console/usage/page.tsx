import type { Metadata } from 'next';
import { Card, EmptyState, ErrorState } from '@veo/ui';

import { measurementLabel, readSpend } from '@/lib/observations';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import own from './usage.module.css';

export const metadata: Metadata = {
  title: '사용량·비용',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

export default async function ConsoleUsagePage({
  searchParams,
}: {
  readonly searchParams: Promise<{ readonly month?: string }>;
}) {
  const identity = await requireConsoleIdentity();
  const { month } = await searchParams;

  return (
    <PermissionGate identity={identity} permission="usage:read">
      <ConsoleUsageContent month={month ?? null} />
    </PermissionGate>
  );
}

async function ConsoleUsageContent({ month }: { readonly month: string | null }) {
  const found = await readSpend(month);

  if (!found.ok) {
    return (
      <div className={styles.page}>
        <ErrorState
          title="사용량을 불러오지 못했습니다"
          description={found.message ?? '서버에 연결하지 못했습니다.'}
        />
      </div>
    );
  }

  const spend = found.data;
  const priced = spend.measurement === 'COMPLETE';

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔 · {spend.month}</p>
        <h1 className={styles.title}>사용량·비용</h1>
        <p className={styles.lede}>
          AI 답변 엔진에 실제로 보낸 호출입니다. <strong>금액을 내지 못한 호출은 0원으로
          더하지 않습니다</strong> — 더하면 합계가 &lsquo;예산 안&rsquo;처럼 보이는데, 그
          결론은 자료가 뒷받침하지 않습니다.
        </p>
      </div>

      {spend.total_calls === 0 ? (
        <EmptyState description="이 달에 실행한 AI 호출이 없습니다." />
      ) : (
        <>
          <section className={styles.section} aria-labelledby="usage-total-heading">
            <h2 id="usage-total-heading" className={styles.sectionTitle}>
              이 달에 쓴 만큼
            </h2>
            <dl className={own.totals}>
              <Figure label="호출" value={`${spend.total_calls.toLocaleString('ko-KR')}회`} />
              <Figure
                label="입력 토큰"
                value={spend.input_tokens.toLocaleString('ko-KR')}
              />
              <Figure
                label="출력 토큰"
                value={spend.output_tokens.toLocaleString('ko-KR')}
              />
              {/*
                금액과 '얼마나 실측인지' 를 떼어 놓지 않는다. $0.00 만 크게 보이면
                그것이 이 달의 전부라는 뜻으로 읽힌다.
              */}
              <Figure
                label="측정된 금액"
                value={`$${spend.measured_cost_usd.toFixed(2)}`}
                note={measurementLabel(spend.measurement)}
                warn={!priced}
              />
            </dl>

            {spend.unmeasurable_calls > 0 ? (
              <p className={own.unmeasured}>
                이 중 <strong>{spend.unmeasurable_calls.toLocaleString('ko-KR')}회</strong>는
                금액을 낼 수 없어 위 합계에 들어 있지 않습니다.{' '}
                <strong>실제 지출은 위 금액보다 큽니다.</strong>
              </p>
            ) : null}
          </section>

          {spend.remedies_ko.length > 0 ? (
            <section className={styles.section} aria-labelledby="usage-remedy-heading">
              <h2 id="usage-remedy-heading" className={styles.sectionTitle}>
                금액을 알려면
              </h2>
              <ul className={own.remedies}>
                {spend.remedies_ko.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className={styles.section} aria-labelledby="usage-engine-heading">
            <h2 id="usage-engine-heading" className={styles.sectionTitle}>
              엔진별
            </h2>
            <ul className={own.engineList}>
              {spend.engines.map((engine) => (
                <li key={engine.engine} className={own.engine}>
                  <p className={own.engineHead}>
                    <span className={own.engineName}>{engine.engine}</span>
                    <span className={own.engineCalls}>
                      {engine.calls.toLocaleString('ko-KR')}회
                    </span>
                  </p>
                  <p className={own.engineMeta}>
                    입력 {engine.input_tokens.toLocaleString('ko-KR')} · 출력{' '}
                    {engine.output_tokens.toLocaleString('ko-KR')} 토큰 · 측정된 금액 $
                    {engine.measured_cost_usd.toFixed(2)}
                  </p>
                  {engine.unmeasurable_calls > 0 ? (
                    <p className={own.engineWarn}>
                      금액 미측정 {engine.unmeasurable_calls.toLocaleString('ko-KR')}회
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      <section className={styles.section} aria-labelledby="usage-policy-heading">
        <h2 id="usage-policy-heading" className={styles.sectionTitle}>
          이 숫자를 읽는 법
        </h2>
        <Card title="0원과 '모른다'는 다릅니다" headingLevel={3}>
          <ul className={styles.list}>
            <li>호출 수와 토큰 수는 언제나 실측입니다. 가격표가 비어 있어도 잽니다.</li>
            <li>
              금액은 가격이 등록된 모델에서만 계산합니다. 없으면 &lsquo;측정 불가&rsquo;로
              남고 0원이 되지 않습니다.
            </li>
            <li>실패한 호출도 과금될 수 있어 빼지 않고 셉니다.</li>
          </ul>
        </Card>
      </section>
    </div>
  );
}

function Figure({
  label,
  value,
  note,
  warn = false,
}: {
  readonly label: string;
  readonly value: string;
  readonly note?: string;
  readonly warn?: boolean;
}) {
  return (
    <div className={warn ? own.figureWarn : own.figure}>
      <dt>{label}</dt>
      <dd className={own.figureValue}>{value}</dd>
      {note !== undefined ? <dd className={own.figureNote}>{note}</dd> : null}
    </div>
  );
}
