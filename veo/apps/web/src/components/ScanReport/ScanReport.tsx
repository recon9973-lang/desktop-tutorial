import { Card, StatusChip, type CheckStatus } from '@veo/ui';

import type { Band } from '@/lib/scan-report';
import type { ConsoleScanResult, Issue, Outcome } from '@/lib/console-scan';

import styles from './ScanReport.module.css';

/**
 * 하나의 진단 결과를 두 가지로 보여준다.
 *
 * 기획서 §12.3 — **한 원시 결과에서 보기만 다르게** 만들며 별도 계산을 중복하지 않는다.
 * 여기서는 무엇을 보여줄지만 고르고, 숫자는 서버가 준 것을 그대로 쓴다.
 *
 * `간소화` 는 업체에 그대로 전달할 수 있는 것 — 점수, 등급, 무엇을 먼저 고칠지, 그것이
 * 사업에 어떤 영향인지. `상세` 는 직원용으로 항목 전체, 판정 근거, 수정 예시, 재검증
 * 방법, 그리고 왜 못 잰 항목이 있는지까지 보여준다.
 */

export type ReportView = 'simple' | 'detailed';

interface ScanReportProps {
  readonly result: ConsoleScanResult;
  readonly bands: readonly Band[];
  readonly view: ReportView;
}

/** 0~1 비율을 백분율 문자열로. 반올림은 한 자리까지 — 그 이상은 정밀해 보이기만 한다. */
function percent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

export function ScanReport({ result, bands, view }: ScanReportProps) {
  const detailed = view === 'detailed';

  return (
    <div className={styles.report}>
      <Headline result={result} bands={bands} />
      <Improvements result={result} />
      <Categories result={result} />
      {/* 상세 보기에서는 항목별 판정 안에 조치 안내가 들어가므로 목록을 두 번 그리지
          않는다. 간소화 보기는 그 반대로, 고칠 것만 골라 보여준다. */}
      {detailed ? <Checks result={result} /> : <Issues result={result} detailed={false} />}
      {detailed ? <Unmeasured result={result} /> : null}
      {detailed ? <OutOfScope result={result} /> : null}
      {detailed ? <Provenance result={result} /> : null}
    </div>
  );
}

function Headline({
  result,
  bands,
}: {
  readonly result: ConsoleScanResult;
  readonly bands: readonly Band[];
}) {
  const band = bands.find((item) => item.id === result.bandId);

  return (
    <section className={styles.headline} aria-labelledby="report-score">
      <div className={styles.scoreBlock}>
        <h2 id="report-score" className={styles.scoreLabel}>
          SEO 기술 준비도
        </h2>
        <p className={styles.score}>
          {result.score === null ? '측정 불가' : result.score.toFixed(1)}
          {result.score === null ? null : <span className={styles.scoreUnit}>점</span>}
        </p>
        {band === undefined ? null : (
          <p className={styles.band}>
            {band.label}
            {band.description === null ? null : (
              <span className={styles.bandNote}> — {band.description}</span>
            )}
          </p>
        )}
        <p className={styles.meaning}>
          검색 순위 예측이 아니라, 검색엔진과 AI 답변 엔진이 사이트를 발견하고 해석할 수
          있는 상태인지에 대한 값입니다.
        </p>
      </div>

      <dl className={styles.figures}>
        <div>
          <dt>측정 범위</dt>
          <dd>{percent(result.coverage)}</dd>
        </div>
        <div>
          <dt>신뢰도</dt>
          <dd>{percent(result.confidence)}</dd>
        </div>
        <div>
          <dt>채점 기준</dt>
          <dd>{result.specVersion}</dd>
        </div>
      </dl>

      {bands.length === 0 ? null : (
        <table className={styles.bandTable}>
          <caption className={styles.bandCaption}>점수 구간</caption>
          <tbody>
            {bands.map((item) => {
              const current = item.id === result.bandId;
              return (
                <tr key={item.id} className={current ? styles.bandCurrent : undefined}>
                  <th scope="row">
                    {item.label}
                    {/* 현재 등급을 색으로만 표시하지 않는다. 기획서 §12.1 */}
                    {current ? <span className={styles.bandMark}> · 현재</span> : null}
                  </th>
                  <td>
                    {item.min}~{Math.round(item.max)}점
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {result.appliedCaps.map((cap) => (
        <p key={cap.capId} className={styles.cap}>
          <strong>{cap.maxOverallScore}점 상한이 걸려 있습니다.</strong> {cap.reason}{' '}
          {cap.releaseCondition}
        </p>
      ))}
    </section>
  );
}

function Improvements({ result }: { readonly result: ConsoleScanResult }) {
  if (result.improvements.length === 0) return null;

  const blocked = result.improvements.every((item) => item.blockedByCap);

  return (
    <section className={styles.section} aria-labelledby="report-todo">
      <h2 id="report-todo" className={styles.sectionTitle}>
        100점까지 — 개선 할 일
      </h2>
      <p className={styles.sectionNote}>
        {blocked
          ? '지금은 상한이 걸려 있어, 아래를 고쳐도 상한이 풀리기 전까지는 점수가 오르지 않습니다.'
          : '위에서부터 처리하면 점수가 가장 빨리 오릅니다. 점수 상승폭은 실제 채점 산식으로 계산한 값입니다.'}
      </p>
      <ol className={styles.todoList}>
        {result.improvements.map((item) => (
          <li key={item.checkId} className={styles.todo}>
            <span className={styles.todoTitle}>{item.title}</span>
            <span className={styles.todoMeta}>
              {item.blockedByCap ? '상한 해제 후 반영' : `+${item.gainPoints.toFixed(1)}점`}
              <span className={styles.todoOwner}> · {ownerLabel(item.remediationOwner)}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Categories({ result }: { readonly result: ConsoleScanResult }) {
  return (
    <section className={styles.section} aria-labelledby="report-categories">
      <h2 id="report-categories" className={styles.sectionTitle}>
        영역별 점수
      </h2>
      <ul className={styles.categoryList}>
        {result.categories.map((category) => (
          <li key={category.categoryId} className={styles.category}>
            <div className={styles.categoryHead}>
              <span className={styles.categoryName}>{category.name}</span>
              <span className={styles.categoryScore}>
                {category.score === null
                  ? '측정 불가'
                  : /* 배점 대비로 보여준다. 백분율만 쓰면 어느 영역이 무거운지 알 수 없다. */
                    `${((category.score * category.weight) / 100).toFixed(1)} / ${category.weight}`}
              </span>
            </div>
            <p className={styles.categoryMeta}>
              측정 범위 {percent(category.coverage)}
              {category.failingCheckIds.length > 0
                ? ` · 실패 ${category.failingCheckIds.length}건`
                : ''}
              {category.unknownCheckIds.length > 0
                ? ` · 측정 불가 ${category.unknownCheckIds.length}건`
                : ''}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * 항목별 판정 — 접혀 있다가, 열면 원인과 수정 방향이 나온다.
 *
 * 54개 항목의 근거를 한꺼번에 펼쳐 두면 화면이 읽히지 않고, 상태만 늘어놓으면 그 줄을
 * 본 직원이 할 수 있는 일이 없다. 그래서 한 줄은 판정과 이름만, 열었을 때 두 가지 —
 * 무엇을 보고 그렇게 판정했는지와, 무엇을 어떻게 바꾸는지.
 *
 * `details`/`summary` 를 쓰는 이유: 자바스크립트 없이 열리고, 키보드로 다룰 수 있으며,
 * 브라우저의 페이지 내 검색이 닫힌 내용까지 찾아 준다. 직접 만든 토글은 셋 다 잃는다.
 */
function Checks({ result }: { readonly result: ConsoleScanResult }) {
  const scored = result.outcomes.filter((item) => item.availability === 'SELF_SERVICE');
  const issues = new Map(result.issues.map((issue) => [issue.checkId, issue]));
  const groups = groupByCategory(scored);

  return (
    <section className={styles.section} aria-labelledby="report-checks">
      <h2 id="report-checks" className={styles.sectionTitle}>
        항목별 판정 ({scored.length}개)
      </h2>
      <p className={styles.sectionNote}>
        각 항목을 펼치면 그렇게 판정한 근거와, 고칠 항목이라면 수정 방향이 나옵니다.
      </p>

      {groups.map(([categoryName, items]) => (
        <div key={categoryName} className={styles.checkGroup}>
          <h3 className={styles.checkGroupTitle}>
            {categoryName}
            <span className={styles.checkGroupCount}>{items.length}개</span>
          </h3>
          <ul className={styles.checkList}>
            {items.map((outcome) => (
              <li key={outcome.checkId}>
                <CheckPanel outcome={outcome} issue={issues.get(outcome.checkId)} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

function CheckPanel({
  outcome,
  issue,
}: {
  readonly outcome: Outcome;
  readonly issue: Issue | undefined;
}) {
  const causes = describeObserved(outcome.observed);

  return (
    <details className={styles.check}>
      <summary className={styles.checkSummary}>
        <StatusChip status={outcome.status as CheckStatus} />
        <span className={styles.checkTitle}>{outcome.title}</span>
        <span className={styles.checkSeverity}>{severityLabel(outcome.severity)}</span>
      </summary>

      <div className={styles.checkDetail}>
        <section className={styles.checkBlock}>
          <h4 className={styles.checkBlockTitle}>이렇게 판정한 근거</h4>
          {outcome.note === null ? null : <p className={styles.checkNote}>{outcome.note}</p>}
          {causes.length === 0 ? null : (
            <ul className={styles.causeList}>
              {causes.map((cause) => (
                <li key={cause.label}>
                  {cause.label === '' ? null : (
                    <code className={styles.causeWhere}>{cause.label}</code>
                  )}
                  <span className={styles.causeWhat}>{cause.detail}</span>
                </li>
              ))}
            </ul>
          )}
          {outcome.reference === null ? null : (
            <p className={styles.checkWhy}>
              <strong>왜 보는가</strong> {outcome.reference}
            </p>
          )}
          <p className={styles.checkMeta}>
            <code>{outcome.checkId}</code>
            {outcome.confidenceLevel === null ? null : ` · 근거 강도 ${outcome.confidenceLevel}`}
          </p>
        </section>

        {issue === undefined ? null : (
          <section className={styles.checkBlock}>
            <h4 className={styles.checkBlockTitle}>어떻게 고치나</h4>
            <p className={styles.issueFix}>{issue.remediation}</p>
            {issue.fixExample === null ? null : (
              <pre className={styles.code}>
                <code>{issue.fixExample}</code>
              </pre>
            )}
            {issue.affectedUrls.length === 0 ? null : (
              <div className={styles.urls}>
                <strong>대상 URL</strong>
                <ul>
                  {issue.affectedUrls.slice(0, 10).map((url) => (
                    <li key={url}>
                      <code>{url}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {issue.businessImpact === '' ? null : (
              <p className={styles.issueImpact}>
                <strong>이대로 두면</strong> {issue.businessImpact}
              </p>
            )}
            {issue.reverificationNote === '' ? null : (
              <p className={styles.issueRetest}>
                <strong>확인 방법</strong> {issue.reverificationNote}
              </p>
            )}
            <p className={styles.issueOwner}>담당 {ownerLabel(issue.remediationOwner)}</p>
          </section>
        )}
      </div>
    </details>
  );
}

/**
 * 연동이 있어야 재는 항목들. 배점에서 빠지지만 숨기지는 않는다.
 *
 * 사용자의 지시가 정확히 이것이었다 — 배점에서 빼되, 측정하지 않더라도 아래에 언급해
 * 알려 주는 방식으로만 쓴다.
 */
function OutOfScope({ result }: { readonly result: ConsoleScanResult }) {
  const gated = result.outcomes.filter((item) => item.availability !== 'SELF_SERVICE');
  if (gated.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-out-of-scope">
      <h2 id="report-out-of-scope" className={styles.sectionTitle}>
        이 진단의 배점 밖 ({gated.length}개)
      </h2>
      <p className={styles.sectionNote}>
        연동이 있어야 잴 수 있는 항목입니다. 점수를 깎지 않았고 분모에도 넣지 않았습니다 —
        아직 요청하지 않은 권한 때문에 점수가 낮아지면 안 되기 때문입니다. 연결하면 다음
        진단부터 함께 측정됩니다.
      </p>
      <ul className={styles.reasonList}>
        {gated.map((item) => (
          <li key={item.checkId}>
            <span className={styles.reasonTitle}>
              {item.title}
              <span className={styles.gateTag}>{availabilityLabel(item.availability)}</span>
            </span>
            <span className={styles.reasonWhy}>{item.note ?? item.categoryName}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** 명세가 준 영역 이름으로 묶는다. 순서는 서버가 준 순서 그대로 — 명세의 순서다. */
function groupByCategory(outcomes: readonly Outcome[]): [string, Outcome[]][] {
  const groups = new Map<string, Outcome[]>();
  for (const outcome of outcomes) {
    const bucket = groups.get(outcome.categoryName);
    if (bucket === undefined) {
      groups.set(outcome.categoryName, [outcome]);
    } else {
      bucket.push(outcome);
    }
  }
  return [...groups.entries()];
}

/**
 * 수집기가 담아 둔 관측값을 화면에 쓸 줄로 편다.
 *
 * 값의 모양은 검사마다 다르다 — URL별 문제 설명(dict), 문제 URL 목록(list), 개수 하나.
 * 여기서 하는 일은 **모양을 읽는 것뿐** 이고, 값을 계산하거나 요약하지 않는다.
 */
function describeObserved(observed: unknown): { label: string; detail: string }[] {
  if (observed === null || observed === undefined) return [];

  if (Array.isArray(observed)) {
    return observed.map((item, index) => ({
      label: String(index + 1),
      detail: plain(item),
    }));
  }

  if (typeof observed === 'object') {
    return Object.entries(observed as Record<string, unknown>).map(([key, value]) => ({
      label: key,
      detail: plain(value),
    }));
  }

  return [{ label: '', detail: plain(observed) }];
}

function plain(value: unknown): string {
  if (value === null || value === undefined) return '없음';
  if (typeof value === 'boolean') return value ? '예' : '아니오';
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(plain).join(', ');
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, entry]) => `${key}: ${plain(entry)}`)
      .join(' · ');
  }
  return String(value);
}

const SEVERITIES: Record<string, string> = {
  BLOCKER: '치명',
  CRITICAL: '심각',
  MAJOR: '중요',
  MINOR: '경미',
  INFO: '참고',
};

function severityLabel(severity: string): string {
  return SEVERITIES[severity] ?? severity;
}

const AVAILABILITIES: Record<string, string> = {
  CUSTOMER_GRANTED: '고객 권한 필요',
  PAID_PROVIDER: '유료 연동 필요',
};

function availabilityLabel(availability: string): string {
  return AVAILABILITIES[availability] ?? availability;
}

function Unmeasured({ result }: { readonly result: ConsoleScanResult }) {
  if (result.unknownChecks.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-unknown">
      <h2 id="report-unknown" className={styles.sectionTitle}>
        측정하지 못한 항목 ({result.unknownChecks.length}개)
      </h2>
      <p className={styles.sectionNote}>
        감점되지 않았습니다. 측정 범위에만 반영됩니다 — 사이트가 나쁜 것이 아니라 판정에
        필요한 근거를 얻지 못한 것입니다.
      </p>
      <ul className={styles.reasonList}>
        {result.unknownChecks.map((item) => (
          <li key={item.checkId}>
            <span className={styles.reasonTitle}>{item.title}</span>
            <span className={styles.reasonWhy}>{item.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Issues({
  result,
  detailed,
}: {
  readonly result: ConsoleScanResult;
  readonly detailed: boolean;
}) {
  if (result.issues.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby="report-issues">
      <h2 id="report-issues" className={styles.sectionTitle}>
        조치가 필요한 항목 ({result.issues.length}건)
      </h2>
      <ul className={styles.issueList}>
        {result.issues.map((issue) => (
          <li key={issue.checkId}>
            <Card title={issue.title} headingLevel={3}>
              <p className={styles.issueSummary}>{issue.summary}</p>

              {issue.businessImpact === '' ? null : (
                <p className={styles.issueImpact}>
                  <strong>사업 영향</strong> {issue.businessImpact}
                </p>
              )}

              <p className={styles.issueFix}>
                <strong>조치</strong> {issue.remediation}
              </p>

              {detailed && issue.fixExample !== null ? (
                <pre className={styles.code}>
                  <code>{issue.fixExample}</code>
                </pre>
              ) : null}

              {detailed && issue.affectedUrls.length > 0 ? (
                <div className={styles.urls}>
                  <strong>영향 URL</strong>
                  <ul>
                    {issue.affectedUrls.slice(0, 10).map((url) => (
                      <li key={url}>
                        <code>{url}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {detailed && issue.reverificationNote !== '' ? (
                <p className={styles.issueRetest}>
                  <strong>재검증</strong> {issue.reverificationNote}
                </p>
              ) : null}

              <p className={styles.issueOwner}>담당 {ownerLabel(issue.remediationOwner)}</p>
            </Card>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Provenance({ result }: { readonly result: ConsoleScanResult }) {
  return (
    <section className={styles.section} aria-labelledby="report-provenance">
      <h2 id="report-provenance" className={styles.sectionTitle}>
        근거와 출처
      </h2>
      <p className={styles.sectionNote}>
        판정마다 그때 수집한 내용의 해시가 남아 있습니다. 몇 달 뒤에도 무엇을 보고 그렇게
        판정했는지 확인할 수 있습니다.
      </p>
      <dl className={styles.figures}>
        <div>
          <dt>채점 기준</dt>
          <dd>
            {result.specId} {result.specVersion}
          </dd>
        </div>
        <div>
          <dt>기준 체크섬</dt>
          <dd>
            <code>{result.specChecksum.slice(0, 12)}…</code>
          </dd>
        </div>
        <div>
          <dt>수집 근거</dt>
          <dd>{result.evidence.length}건</dd>
        </div>
      </dl>
    </section>
  );
}

const OWNERS: Record<string, string> = {
  DEVELOPER: '개발',
  MARKETER: '마케팅',
  BUSINESS_OWNER: '사업 담당',
  OPERATIONS: '운영',
};

function ownerLabel(owner: string): string {
  return OWNERS[owner] ?? owner;
}
