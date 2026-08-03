'use client';

import { useMemo } from 'react';
import { StatusChip, type CheckStatus } from '@veo/ui';

import { describeObserved } from '@/components/ScanReport/CheckExplorer';
import type { GeoCheck, GeoIssue } from '@/lib/observations';

import styles from './geo.module.css';

/**
 * GEO 항목별 판정 — 무엇을 보고 그렇게 판정했고, 어떻게 고치나.
 *
 * 엔진은 처음부터 이 자료를 보내고 있었다. 화면이 읽지 않아서 GEO 는 영역 점수만 보이고
 * **왜 그 점수인지와 무엇을 고쳐야 하는지가 없었다** — 담당자가 그 화면을 보고 할 수 있는
 * 일이 없었다(사용자 지적: "SEO 처럼 측정값과 해결방법을").
 *
 * SEO 화면과 **같은 문법**을 쓴다: 영역이 카드, 머리줄에 상태 요약, 접힌 줄에 실측값,
 * 펼치면 근거와 고침 방법. 두 화면이 다른 문법을 쓰면 같은 사람이 두 번 배워야 한다.
 * 실측값을 사람 말로 옮기는 일은 SEO 쪽 함수를 그대로 부른다 — 두 벌로 만들면 한쪽만
 * 고쳐지는 날이 온다.
 */

const SEVERITY_LABELS: Record<string, string> = {
  BLOCKER: '치명',
  CRITICAL: '심각',
  MAJOR: '중요',
  MINOR: '경미',
  INFO: '참고',
};

/** 심각도 배지. 무게가 세 단계로만 보이게 묶는다 — 다섯 색은 색이 아니라 소음이다. */
const SEVERITY_BADGE: Record<string, string> = {
  BLOCKER: styles.sevBadgeHigh ?? '',
  CRITICAL: styles.sevBadgeHigh ?? '',
  MAJOR: styles.sevBadgeMid ?? '',
  MINOR: styles.sevBadgeLow ?? '',
  INFO: styles.sevBadgeLow ?? '',
};

const OWNERS: Record<string, string> = {
  DEVELOPER: '개발',
  CONTENT: '콘텐츠',
  MARKETER: '마케팅',
  OWNER: '사장님 확인',
};

/** 행에 얹을 실측값. 길면 접힌 줄을 밀어내므로 자른다. */
const GLANCE_MAX = 42;

function glance(causes: readonly { label: string; detail: string }[]): string | null {
  if (causes.length === 0) return null;
  if (causes.length > 1) return `${causes.length}건`;
  const only = causes[0];
  if (only === undefined) return null;
  const text = only.detail.trim();
  if (text === '') return null;
  return text.length > GLANCE_MAX ? `${text.slice(0, GLANCE_MAX)}…` : text;
}

export function ReadinessChecks({
  checks,
  issues,
  severities,
}: {
  readonly checks: readonly GeoCheck[];
  readonly issues: readonly GeoIssue[];
  /**
   * 검사별 심각도 — **발행 명세에서 읽어 온 것**만 온다.
   *
   * GEO 응답에는 심각도가 없다. 일부러 없다(엔진 경계). 없는 검사는 배지를 그리지
   * 않는다 — 지어낸 심각도는 없는 것보다 나쁘다.
   */
  readonly severities?: ReadonlyMap<string, string>;
}) {
  const issueOf = useMemo(
    () => new Map(issues.map((issue) => [issue.check_id, issue])),
    [issues],
  );
  const groups = useMemo(() => groupByCategory(checks), [checks]);

  if (checks.length === 0) return null;

  return (
    <section className={styles.checksSection} aria-labelledby="geo-checks">
      <h3 id="geo-checks" className={styles.checksTitle}>
        항목별 판정 ({checks.length}개)
      </h3>
      <p className={styles.checksNote}>
        각 항목을 펼치면 그렇게 판정한 근거와, 고칠 항목이라면 수정 방향과 붙여넣을 코드가
        나옵니다.
      </p>

      {groups.map(([name, items]) => (
        <CheckGroup
          key={name}
          name={name}
          items={items}
          issueOf={issueOf}
          severities={severities}
        />
      ))}
    </section>
  );
}

function CheckGroup({
  name,
  items,
  issueOf,
  severities,
}: {
  readonly name: string;
  readonly items: readonly GeoCheck[];
  readonly issueOf: ReadonlyMap<string, GeoIssue>;
  readonly severities?: ReadonlyMap<string, string>;
}) {
  const tally: Record<string, number> = {};
  for (const item of items) tally[item.status] = (tally[item.status] ?? 0) + 1;
  const needsWork = (tally.FAIL ?? 0) + (tally.WARNING ?? 0);

  return (
    <section className={styles.checkGroup} aria-label={name}>
      <h4 className={styles.checkGroupTitle}>
        <span className={styles.checkGroupName}>{name}</span>
        <span className={styles.checkGroupTally}>
          {/* 색만으로 알리지 않는다(기획서 §12.1) — 배지마다 글자가 함께 있다. */}
          {tally.FAIL ? <span className={styles.tallyFail}>실패 {tally.FAIL}</span> : null}
          {tally.WARNING ? (
            <span className={styles.tallyWarning}>주의 {tally.WARNING}</span>
          ) : null}
          {tally.UNKNOWN ? (
            <span className={styles.tallyUnknown}>측정 불가 {tally.UNKNOWN}</span>
          ) : null}
          {needsWork === 0 && tally.PASS ? (
            <span className={styles.tallyPass}>모두 통과 {tally.PASS}</span>
          ) : (
            <span className={styles.checkGroupCount}>{items.length}개</span>
          )}
        </span>
      </h4>
      <ul className={styles.checkList}>
        {items.map((check) => (
          <li key={check.check_id}>
            <CheckPanel
              check={check}
              issue={issueOf.get(check.check_id)}
              severity={severities?.get(check.check_id) ?? null}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

function CheckPanel({
  check,
  issue,
  severity,
}: {
  readonly check: GeoCheck;
  readonly issue: GeoIssue | undefined;
  readonly severity: string | null;
}) {
  const causes = describeObserved(check.observed);
  const shown = glance(causes);

  return (
    <details className={styles.check}>
      <summary className={styles.checkSummary}>
        <StatusChip status={check.status as CheckStatus} />
        <span className={styles.checkTitle}>{check.title_ko}</span>
        {/* 확정 시안 v2.2 §11 — "통과" 라는 판정보다 실제로 본 값이 신뢰를 만든다. */}
        {shown === null ? null : <span className={styles.checkObserved}>{shown}</span>}
        {/* 명세가 심각도를 정한 검사만 배지를 단다. 화면은 지어내지 않는다. */}
        {severity === null ? null : (
          <span className={SEVERITY_BADGE[severity] ?? styles.sevBadgeLow}>
            {SEVERITY_LABELS[severity] ?? severity}
          </span>
        )}
      </summary>

      <div className={styles.checkDetail}>
        <section className={styles.checkBlock}>
          <h5 className={styles.checkBlockTitle}>이렇게 판정한 근거</h5>
          {check.note_ko === null ? null : <p className={styles.checkNote}>{check.note_ko}</p>}
          {causes.length === 0 ? null : (
            <ul className={styles.causeList}>
              {causes.map((cause) => (
                <li key={cause.label}>
                  {cause.label === '' ? null : (
                    <code className={styles.causeWhere}>{cause.label}</code>
                  )}
                  <span>{cause.detail}</span>
                </li>
              ))}
            </ul>
          )}
          <p className={styles.checkMeta}>
            <code>{check.check_id}</code>
            {check.confidence_level === null ? null : ` · 근거 강도 ${check.confidence_level}`}
          </p>
        </section>

        {issue === undefined ? null : (
          <section className={styles.checkBlock}>
            <h5 className={styles.checkBlockTitle}>어떻게 고치나</h5>
            <p className={styles.checkNote}>{issue.remediation_ko}</p>
            {issue.fix_example === null ? null : (
              <>
                {/* 예시임을 라벨에 못 박는다 — 예시 코드가 측정된 실데이터로 읽히면
                    담당자가 남의 값을 그대로 올린다(v0.3.2 에서 고친 오해). */}
                <p className={styles.checkBlockTitle}>
                  예시 코드 — 업체명·내용은 우리 것으로 바꿔 쓰세요
                </p>
                <pre className={styles.code}>
                  <code>{issue.fix_example}</code>
                </pre>
              </>
            )}
            {issue.affected_urls.length === 0 ? null : (
              <div className={styles.urls}>
                <strong>대상 URL</strong>
                <ul>
                  {issue.affected_urls.slice(0, 10).map((url) => (
                    <li key={url}>
                      <code>{url}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {issue.business_impact_ko === '' ? null : (
              <p className={styles.checkNote}>
                <strong>이대로 두면</strong> {issue.business_impact_ko}
              </p>
            )}
            {issue.reverification_note_ko === '' ? null : (
              <p className={styles.checkNote}>
                <strong>확인 방법</strong> {issue.reverification_note_ko}
              </p>
            )}
            <p className={styles.checkMeta}>
              담당 {OWNERS[issue.remediation_owner] ?? issue.remediation_owner}
            </p>
          </section>
        )}
      </div>
    </details>
  );
}

/** 명세가 준 영역 이름으로 묶는다. 순서는 서버가 준 순서 그대로 — 명세의 순서다. */
function groupByCategory(checks: readonly GeoCheck[]): [string, GeoCheck[]][] {
  const groups = new Map<string, GeoCheck[]>();
  for (const check of checks) {
    // 명세에 없는 검사는 영역이 비어 온다. 지어낸 묶음에 끼워 넣지 않는다.
    const name = check.category_name_ko === '' ? '기타' : check.category_name_ko;
    const bucket = groups.get(name);
    if (bucket === undefined) groups.set(name, [check]);
    else bucket.push(check);
  }
  return [...groups.entries()];
}
