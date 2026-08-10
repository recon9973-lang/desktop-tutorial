import type { Metadata } from 'next';
import { Card, EmptyState, ErrorState, formatCount, formatPercent, formatScore } from '@veo/ui';

import { measurementLabel, readSpend } from '@/lib/observations';
import { readPageSpeedQuota, type PageSpeedQuota } from '@/lib/usage';
import styles from '@/styles/page.module.css';
import { PermissionGate } from '@/components/PermissionGate';
import { requireConsoleIdentity } from '@/lib/session';

import { AlertTestButton } from './AlertTestButton';
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
  // 둘은 서로 다른 질문이다 — 하나가 실패해도 나머지는 보여야 한다. 한도는 특히
  // 그렇다: 이 화면이 통째로 사라지면 한도에 다가가는 것을 아무도 모른다.
  const [quotaFound, spendFound] = await Promise.all([readPageSpeedQuota(), readSpend(month)]);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>콘솔</p>
        <h1 className={styles.title}>사용량·비용</h1>
        <p className={styles.lede}>
          외부 API 를 실제로 부른 만큼입니다. 위쪽은 <strong>오늘의 한도</strong>(넘기면 그날
          진단에서 성능이 빠집니다), 아래쪽은 <strong>이 달의 AI 호출과 비용</strong>입니다.
        </p>
      </div>

      <PageSpeedQuotaSection found={quotaFound} />
      <SpendSection found={spendFound} />
      <AlertSection />
    </div>
  );
}

/* ── 오늘의 한도 ─────────────────────────────────────────────────────── */

/**
 * 한도는 **넘기 전에** 보여야 의미가 있다.
 *
 * 넘고 나면 "성능 측정 불가" 로만 드러나고, 그것도 화면에서는 사이트의 문제처럼
 * 보이는 형태다. 그때는 이미 그날 하루가 지나갔다.
 */
function PageSpeedQuotaSection({
  found,
}: {
  readonly found: Awaited<ReturnType<typeof readPageSpeedQuota>>;
}) {
  if (!found.ok) {
    return (
      <section className={styles.section} aria-labelledby="quota-heading">
        <h2 id="quota-heading" className={styles.sectionTitle}>
          오늘 PageSpeed 한도
        </h2>
        {/*
          여기서 "0회 썼습니다" 로 넘어가면 안 된다. 못 읽은 것과 안 쓴 것은 정반대이고,
          하필 이 화면에서 그 둘을 섞으면 한도가 끝난 날에 여유가 있다고 말하게 된다.
        */}
        <ErrorState
          title="한도를 확인하지 못했습니다"
          description={
            (found.message ?? '서버에 연결하지 못했습니다.') +
            ' 이 숫자를 못 읽은 것이지, 한도가 남아 있다는 뜻이 아닙니다.'
          }
        />
      </section>
    );
  }

  const quota = found.data;

  return (
    <section className={styles.section} aria-labelledby="quota-heading">
      <h2 id="quota-heading" className={styles.sectionTitle}>
        오늘 PageSpeed 한도
      </h2>

      {/* 한 줄 판정을 먼저. 숫자를 읽기 전에 결론이 보여야 한다. */}
      <p className={statusClass(quota)} role={quota.is_warning ? 'status' : undefined}>
        {quota.summary_ko}
      </p>

      <dl className={own.totals}>
        {/*
          남은 양이 제일 크게 온다. '쓴 만큼' 을 앞에 두면 판단에 한 번 더 뺄셈이 든다.
        */}
        <Figure
          label="남은 호출"
          value={`${formatCount(quota.remaining)}회`}
          note={`진단 한 번에 최대 ${quota.calls_per_scan}회 · 약 ${formatCount(quota.scans_remaining)}번 더 진단 가능`}
          warn={quota.is_warning}
        />
        <Figure
          label="오늘 쓴 호출 (전체)"
          value={`${formatCount(quota.calls_today)}회`}
          note={`한도 ${formatCount(quota.daily_quota)}회 중 ${percent(quota.used_ratio)}`}
        />
        <Figure
          label="이 조직이 쓴 몫"
          value={`${formatCount(quota.calls_by_this_organization)}회`}
          note="참고용입니다. 남은 양은 이 숫자로 알 수 없습니다."
        />
      </dl>

      {quota.remedies_ko.length > 0 ? (
        <ul className={own.remedies}>
          {quota.remedies_ko.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}

      {/*
        주의 문구는 접어 두지 않는다. 조직 몫과 남은 양을 같은 뜻으로 읽는 순간
        이 화면은 확신 있게 틀린 말을 하게 된다.
      */}
      <p className={own.caveat}>{quota.caveat_ko}</p>
    </section>
  );
}

/** 여유·경고·소진을 색만으로 구분하지 않는다. 문장 자체가 이미 다르다. */
function statusClass(quota: PageSpeedQuota): string | undefined {
  if (quota.is_exhausted) return own.quotaExhausted;
  if (quota.is_warning) return own.quotaWarning;
  return own.quotaCalm;
}

function percent(ratio: number): string {
  return formatPercent(ratio);
}

/* ── 이 달의 AI 호출 ─────────────────────────────────────────────────── */

function SpendSection({ found }: { readonly found: Awaited<ReturnType<typeof readSpend>> }) {
  if (!found.ok) {
    return (
      <section className={styles.section} aria-labelledby="spend-heading">
        <h2 id="spend-heading" className={styles.sectionTitle}>
          이 달의 AI 호출
        </h2>
        <ErrorState
          title="사용량을 불러오지 못했습니다"
          description={found.message ?? '서버에 연결하지 못했습니다.'}
        />
      </section>
    );
  }

  const spend = found.data;
  const priced = spend.measurement === 'COMPLETE';

  return (
    <>
      <section className={styles.section} aria-labelledby="spend-heading">
        <h2 id="spend-heading" className={styles.sectionTitle}>
          이 달의 AI 호출 · {spend.month}
        </h2>
        <p className={own.sectionLede}>
          AI 답변 엔진에 실제로 보낸 호출입니다. <strong>금액을 내지 못한 호출은 0원으로
          더하지 않습니다</strong> — 더하면 합계가 &lsquo;예산 안&rsquo;처럼 보이는데, 그
          결론은 자료가 뒷받침하지 않습니다.
        </p>

        {spend.total_calls === 0 ? (
          <EmptyState description="이 달에 실행한 AI 호출이 없습니다." />
        ) : (
          <>
            <dl className={own.totals}>
              <Figure label="호출" value={`${formatCount(spend.total_calls)}회`} />
              <Figure
                label="입력 토큰"
                value={formatCount(spend.input_tokens)}
              />
              <Figure
                label="출력 토큰"
                value={formatCount(spend.output_tokens)}
              />
              {/*
                금액과 '얼마나 실측인지' 를 떼어 놓지 않는다. $0.00 만 크게 보이면
                그것이 이 달의 전부라는 뜻으로 읽힌다.
              */}
              <Figure
                label="측정된 금액"
                value={`$${formatScore(spend.measured_cost_usd)}`}
                note={measurementLabel(spend.measurement)}
                warn={!priced}
              />
            </dl>

            {spend.unmeasurable_calls > 0 ? (
              <p className={own.unmeasured}>
                이 중 <strong>{formatCount(spend.unmeasurable_calls)}회</strong>는
                금액을 낼 수 없어 위 합계에 들어 있지 않습니다.{' '}
                <strong>실제 지출은 위 금액보다 큽니다.</strong>
              </p>
            ) : null}
          </>
        )}
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

      {spend.total_calls > 0 ? (
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
                    {formatCount(engine.calls)}회
                  </span>
                </p>
                <p className={own.engineMeta}>
                  입력 {formatCount(engine.input_tokens)} · 출력{' '}
                  {formatCount(engine.output_tokens)} 토큰 · 측정된 금액 $
                  {formatScore(engine.measured_cost_usd)}
                </p>
                {engine.unmeasurable_calls > 0 ? (
                  <p className={own.engineWarn}>
                    금액 미측정 {formatCount(engine.unmeasurable_calls)}회
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

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
            <li>
              PageSpeed 는 하루 한도 안에서 무료입니다. 위 &lsquo;오늘 PageSpeed 한도&rsquo;
              가 0원이 아니라 <strong>횟수</strong>를 세는 이유입니다.
            </li>
          </ul>
        </Card>
      </section>
    </>
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

/* ── 경보 ────────────────────────────────────────────────────────────── */

/**
 * 경보가 실제로 닿는가.
 *
 * 이 자리가 사용량 화면에 있는 이유는, 여기가 **한도가 보이는 곳**이기 때문이다.
 * 한도를 넘으면 경보가 울려야 하는데 그 경보가 닿지 않으면 이 화면도 소용이 없다 —
 * 아무도 안 보고 있을 때를 위한 것이 경보다.
 */
function AlertSection() {
  return (
    <section className={styles.section} aria-labelledby="alert-heading">
      <h2 id="alert-heading" className={styles.sectionTitle}>
        경보
      </h2>
      <Card title="알림이 닿는지 확인" headingLevel={3} tone="flat">
        <AlertTestButton />
      </Card>
    </section>
  );
}
