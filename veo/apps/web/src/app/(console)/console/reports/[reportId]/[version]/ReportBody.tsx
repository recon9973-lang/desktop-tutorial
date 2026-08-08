import Link from 'next/link';
import { Card } from '@veo/ui';

import type {
  ReportAudienceView,
  ReportValue,
  ReportVersionDetail,
} from '@/lib/reports';
import styles from '@/styles/page.module.css';

import own from '../../reports.module.css';

/** 읽을 수 있는 독자 셋. 주소에 없는 값이 오면 경영진으로 본다. */
export const AUDIENCES = ['executive', 'marketing', 'developer'] as const;
export type Audience = (typeof AUDIENCES)[number];

export const AUDIENCE_LABELS_KO: Record<Audience, string> = {
  executive: '경영진',
  marketing: '마케팅',
  developer: '개발자',
};

export function readAudience(value: string | undefined): Audience {
  return AUDIENCES.includes(value as Audience) ? (value as Audience) : 'executive';
}

/**
 * 발행된 리포트 한 판의 **본문**.
 *
 * 화면을 눈으로 못 여는 자리라(콘솔은 로그인이 필요하다) 페이지에서 떼어 두고 시험으로
 * 확인한다 — `VisibilityReport` 와 같은 모양이다.
 *
 * 이 화면이 지키는 것 둘.
 *
 * **하나 — 값을 직접 포맷하지 않는다.** 서버가 준 `display` 를 그대로 쓴다. 스키마가
 * 그렇게 못박아 두었다: *"모든 화면·내보내기가 동일하게 출력하는 표기입니다."* 화면이
 * 따로 포맷하면 같은 버전이 화면과 내려받은 파일에서 다르게 보인다.
 *
 * **둘 — 못 잰 값을 0 처럼 그리지 않는다.** `value === null` 은 "못 쟀다" 이고 `0` 은
 * "쟀는데 없었다" 다. 정반대의 사실이라 모양을 달리하고, 왜 못 쟀는지를 붙인다.
 */
export function ReportBody({
  detail,
  audience,
}: {
  readonly detail: ReportVersionDetail;
  readonly audience: Audience;
}) {
  const view = detail.views[audience];

  return (
    <>
      <AudienceTabs
        reportId={detail.report_id}
        version={detail.version_number}
        current={audience}
      />

      <p className={own.versionFacts}>
        발행 {formatWhen(detail.generated_at)}
        {detail.measurement_window_start !== null && detail.measurement_window_end !== null
          ? ` · 측정 구간 ${formatWhen(detail.measurement_window_start)} ~ ${formatWhen(
              detail.measurement_window_end,
            )}`
          : ''}
        <span className={own.hash}>{detail.content_hash}</span>
      </p>

      <section className={styles.section} aria-labelledby="report-summary-heading">
        <h2 id="report-summary-heading" className={styles.sectionTitle}>
          요약
        </h2>
        <p className={styles.prose}>{view.summary_ko}</p>
        {view.status_ko !== null && view.status_ko !== '' ? (
          <p className={styles.callout}>{view.status_ko}</p>
        ) : null}
      </section>

      <Metrics view={view} />
      <TopActions view={view} />
      <Unmeasured view={view} />
      <Changes view={view} />
      <Disclosure detail={detail} view={view} />
    </>
  );
}

/** 독자 셋. 링크라서 주소를 그대로 보낼 수 있고, 자바스크립트 없이도 넘어간다. */
function AudienceTabs({
  reportId,
  version,
  current,
}: {
  readonly reportId: string;
  readonly version: number;
  readonly current: Audience;
}) {
  return (
    <nav className={own.audienceTabs} aria-label="독자별 보기">
      {AUDIENCES.map((one) => (
        <Link
          key={one}
          href={`/console/reports/${reportId}/${version}?audience=${one}`}
          className={one === current ? own.audienceTabCurrent : own.audienceTab}
          aria-current={one === current ? 'page' : undefined}
        >
          {AUDIENCE_LABELS_KO[one]}
        </Link>
      ))}
    </nav>
  );
}

function Metrics({ view }: { readonly view: ReportAudienceView }) {
  if (view.metrics.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-metrics-heading">
      <h2 id="report-metrics-heading" className={styles.sectionTitle}>
        지표 {view.metrics.length}개
      </h2>
      <ul className={own.metricList}>
        {view.metrics.map((metric) => (
          <li key={metric.metric_key} className={own.metric}>
            <span className={own.metricLabel}>{metric.label_ko}</span>
            <MetricValue value={metric.value} />
            {metric.note_ko !== '' ? (
              <span className={own.metricNote}>{metric.note_ko}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function MetricValue({ value }: { readonly value: ReportValue }) {
  const measured = value.value !== null;
  return (
    <span
      className={measured ? own.metricValue : own.metricValueUnknown}
      data-measured={measured ? 'yes' : 'no'}
    >
      {value.display}
      {!measured ? (
        <span className={own.metricWhy}>
          {value.reason_ko !== null && value.reason_ko !== ''
            ? value.reason_ko
            : value.status_ko}
        </span>
      ) : null}
    </span>
  );
}

function TopActions({ view }: { readonly view: ReportAudienceView }) {
  if (view.top_actions.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-actions-heading">
      <h2 id="report-actions-heading" className={styles.sectionTitle}>
        먼저 할 것 {view.top_actions.length}개
      </h2>
      <ol className={own.actionList}>
        {view.top_actions.map((action) => (
          <li key={`${action.rank}-${action.title_ko}`} className={own.action}>
            <p className={own.actionHead}>
              <span className={own.severity}>{action.severity}</span>
              <span className={own.actionTitle}>{action.title_ko}</span>
            </p>
            <p className={own.actionWhy}>{action.why_ko}</p>
            <p className={own.actionOwner}>담당 {action.owner_ko}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** 판정하지 못한 검사. **접지 않는다** — 빼면 문서가 실제보다 튼튼해 보인다. */
function Unmeasured({ view }: { readonly view: ReportAudienceView }) {
  if (view.unmeasured_checks.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-unmeasured-heading">
      <h2 id="report-unmeasured-heading" className={styles.sectionTitle}>
        판정하지 못한 것 {view.unmeasured_checks.length}개
      </h2>
      <p className={styles.callout}>
        아래는 <strong>문제가 없다는 뜻이 아니라</strong> 이번 측정으로는 판정할 수 없었다는
        뜻입니다. 0점과 다릅니다.
      </p>
      <ul className={own.unmeasuredList}>
        {view.unmeasured_checks.map((check) => (
          <li key={check.check_id} className={own.unmeasured}>
            <span className={own.unmeasuredTitle}>{check.title_ko}</span>
            <span className={own.unmeasuredStatus}>{check.status_ko}</span>
            {check.reason_ko !== null && check.reason_ko !== '' ? (
              <span className={own.unmeasuredWhy}>{check.reason_ko}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Changes({ view }: { readonly view: ReportAudienceView }) {
  if (view.changes_ko.length === 0 && view.reverification_ko.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-changes-heading">
      <h2 id="report-changes-heading" className={styles.sectionTitle}>
        지난 판과 달라진 것
      </h2>
      {view.changes_ko.length > 0 ? (
        <ul className={styles.list}>
          {view.changes_ko.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : (
        <p className={own.noMoves}>달라진 것이 기록되지 않았습니다.</p>
      )}
      {view.reverification_ko.length > 0 ? (
        <>
          <p className={styles.callout}>재측정으로 확인해야 하는 것</p>
          <ul className={styles.list}>
            {view.reverification_ko.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

/**
 * 측정 조건 — 숫자 옆에 **늘 함께** 나가야 하는 것.
 *
 * 몇 장을 봤는지, 확신도가 얼마인지, 순위 예측이 아니라는 것. 이것을 접으면 숫자만
 * 남고, 숫자만 남은 문서는 실제보다 세게 읽힌다.
 */
function Disclosure({
  detail,
  view,
}: {
  readonly detail: ReportVersionDetail;
  readonly view: ReportAudienceView;
}) {
  const disclosure = view.disclosure;
  const rows: readonly (readonly [string, string])[] = [
    ['측정 범위', disclosure.scope_ko],
    ['도달 범위', disclosure.coverage_ko],
    ['확신도', disclosure.confidence_ko],
    ['측정 시각', disclosure.measured_at_ko],
    ['방법론', disclosure.methodology_ko],
  ];

  return (
    <section className={styles.section} aria-labelledby="report-disclosure-heading">
      <h2 id="report-disclosure-heading" className={styles.sectionTitle}>
        이 숫자를 읽는 법
      </h2>

      {disclosure.rank_prediction_notice_ko !== '' ? (
        <p className={styles.callout}>{disclosure.rank_prediction_notice_ko}</p>
      ) : null}

      <Card title="측정 조건" headingLevel={3} tone="flat">
        <dl className={own.disclosureList}>
          {rows
            .filter(([, value]) => value !== '')
            .map(([label, value]) => (
              <div key={label} className={own.disclosureRow}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
        </dl>
      </Card>

      {disclosure.lines_ko.length > 0 ? (
        <ul className={styles.list}>
          {disclosure.lines_ko.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}

      {/* 버전 전체에 붙는 고지. 독자별 고지와 별개라 따로 그린다. */}
      {detail.disclosures_ko.length > 0 ? (
        <ul className={styles.list}>
          {detail.disclosures_ko.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

/** 서버에서 그린다. 시간대를 한국 기준으로 고정해 두 곳에서 다른 시각이 보이지 않게 한다. */
export function formatWhen(value: string | null): string {
  if (value === null) return '시각 기록 없음';
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return value;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Seoul',
  }).format(at);
}
