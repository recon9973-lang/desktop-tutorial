'use client';

import { useMemo, useState } from 'react';
import { StatusChip, type CheckStatus } from '@veo/ui';

import type { Issue, Outcome } from '@/lib/console-scan';

import styles from './ScanReport.module.css';

/**
 * 항목별 판정 — 좁혀 보고, 펼쳐 읽는다.
 *
 * 이 화면을 실제로 렌더해 재 봤더니 상세 보기가 **6,476px, 화면 7.2개** 였고 항목이
 * 44개인데 좁힐 수단이 하나도 없었다. 그중 실패는 5개인데 그 5개를 찾으려면 눈으로
 * 훑는 수밖에 없었다.
 *
 * 그래서 두 가지를 더한다. **상태 칩으로 좁히기** — 숫자가 붙어 있어 누르기 전에
 * 몇 개인지 안다. 그리고 **심각도를 행 왼쪽 색 띠로** — 가장 중요한 신호가 오른쪽 끝
 * 흐린 회색 글씨였는데, 통과한 경미 항목과 실패한 치명 항목이 같은 무게로 보였다.
 *
 * 색만으로 알리지 않는다(기획서 §12.1). 띠 옆에 상태 칩과 심각도 글자가 함께 있다.
 */

interface CheckExplorerProps {
  readonly outcomes: readonly Outcome[];
  readonly issues: readonly Issue[];
}

/** 좁히기 기준. `전체` 는 아무것도 빼지 않는다. */
const FILTERS = [
  { id: 'ALL', label: '전체' },
  { id: 'FAIL', label: '실패' },
  { id: 'WARNING', label: '주의' },
  { id: 'UNKNOWN', label: '측정 불가' },
  { id: 'PASS', label: '통과' },
] as const;

type FilterId = (typeof FILTERS)[number]['id'];

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

/** 심각도별 색 띠의 클래스. 이름이 아니라 무게 순서로 읽히게 한다. */
const SEVERITY_CLASS: Record<string, string> = {
  BLOCKER: styles.sevBlocker ?? '',
  CRITICAL: styles.sevCritical ?? '',
  MAJOR: styles.sevMajor ?? '',
  MINOR: styles.sevMinor ?? '',
  INFO: styles.sevInfo ?? '',
};

export function CheckExplorer({ outcomes, issues }: CheckExplorerProps) {
  const [filter, setFilter] = useState<FilterId>('ALL');

  // 배점에 들어가는 항목만 여기서 다룬다. 연동이 필요한 항목은 아래 전용 구역에서
  // 무엇을 연결하면 되는지와 함께 말한다.
  const scored = useMemo(
    () => outcomes.filter((item) => item.availability === 'SELF_SERVICE'),
    [outcomes],
  );

  const counts = useMemo(() => {
    const tally: Record<string, number> = { ALL: scored.length };
    for (const item of scored) {
      tally[item.status] = (tally[item.status] ?? 0) + 1;
    }
    return tally;
  }, [scored]);

  const shown = filter === 'ALL' ? scored : scored.filter((item) => item.status === filter);
  const issueOf = useMemo(() => new Map(issues.map((i) => [i.checkId, i])), [issues]);
  const groups = useMemo(() => groupByCategory(shown), [shown]);

  return (
    <section className={styles.section} aria-labelledby="report-checks">
      <h2 id="report-checks" className={styles.sectionTitle}>
        항목별 판정 ({scored.length}개)
      </h2>
      <p className={styles.sectionNote}>
        각 항목을 펼치면 그렇게 판정한 근거와, 고칠 항목이라면 수정 방향이 나옵니다.
      </p>

      <div className={styles.filters} role="group" aria-label="판정으로 좁히기">
        {FILTERS.map((option) => {
          const count = counts[option.id] ?? 0;
          const active = filter === option.id;
          return (
            <button
              key={option.id}
              type="button"
              className={active ? styles.filterOn : styles.filter}
              aria-pressed={active}
              // 0건인 기준은 눌러도 빈 화면이 된다. 누를 수 없게 두고 이유는 숫자가 말한다.
              disabled={count === 0}
              onClick={() => setFilter(option.id)}
            >
              {option.label}
              <span className={styles.filterCount}>{count}</span>
            </button>
          );
        })}
      </div>

      {shown.length === 0 ? (
        <p className={styles.sectionNote}>이 기준에 해당하는 항목이 없습니다.</p>
      ) : (
        groups.map(([categoryName, items]) => (
          <CheckGroup
            key={categoryName}
            name={categoryName}
            items={items}
            issueOf={issueOf}
          />
        ))
      )}
    </section>
  );
}

/**
 * 한 영역(카테고리) — 카드 하나.
 *
 * 예전에는 영역 이름이 **밑줄 하나**였고 그 아래 항목들이 각자 흰 카드로 떠 있었다.
 * 44개가 같은 무게로 늘어서니 어디서 어디까지가 한 영역인지 눈으로 잡히지 않았고,
 * 멀쩡한 영역을 통째로 건너뛸 방법도 없어 전부 훑어야 했다.
 *
 * 그래서 두 가지를 바꾼다. **영역을 진짜 카드로** 묶어 경계를 만들고, **머리줄에 이 영역의
 * 상태를 요약**한다 — "실패 2 · 주의 1" 이 보이면 볼지 말지 그 자리에서 정할 수 있고,
 * "모두 통과" 면 접힌 채로 지나가면 된다. 항목은 카드 안에서 실선으로만 나뉜다:
 * 카드 안의 카드는 테두리가 두 겹이 되어 오히려 읽기 어려웠다.
 */
function CheckGroup({
  name,
  items,
  issueOf,
}: {
  readonly name: string;
  readonly items: readonly Outcome[];
  readonly issueOf: ReadonlyMap<string, Issue>;
}) {
  const tally = { FAIL: 0, WARNING: 0, UNKNOWN: 0, PASS: 0 } as Record<string, number>;
  for (const item of items) tally[item.status] = (tally[item.status] ?? 0) + 1;
  const needsWork = (tally.FAIL ?? 0) + (tally.WARNING ?? 0);

  return (
    <section className={styles.checkGroup} aria-label={name}>
      <h3 className={styles.checkGroupTitle}>
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
      </h3>
      <ul className={styles.checkList}>
        {items.map((outcome) => (
          <li key={outcome.checkId}>
            <CheckPanel outcome={outcome} issue={issueOf.get(outcome.checkId)} />
          </li>
        ))}
      </ul>
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
  const band = SEVERITY_CLASS[outcome.severity] ?? '';

  return (
    <details className={`${styles.check} ${band}`}>
      <summary className={styles.checkSummary}>
        <StatusChip status={outcome.status as CheckStatus} />
        <span className={styles.checkTitle}>{outcome.title}</span>
        {/* 심각도는 이 줄에서 가장 중요한 신호인데 오른쪽 끝 흐린 회색 글씨였다 —
            통과한 경미 항목과 실패한 치명 항목이 같은 무게로 보였다. 무게에 따라
            배지로 세운다. */}
        <span className={SEVERITY_BADGE[outcome.severity] ?? styles.sevBadgeLow}>
          {SEVERITY_LABELS[outcome.severity] ?? outcome.severity}
        </span>
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
export function describeObserved(observed: unknown): { label: string; detail: string }[] {
  if (observed === null || observed === undefined) return [];

  if (Array.isArray(observed)) {
    return observed.map((item, index) => ({ label: String(index + 1), detail: plain(item) }));
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
  if (typeof value === 'number') return String(value);
  // 빈 문자열·빈 목록·빈 객체는 "없음" 이다. 그대로 두면 이름만 있고 값은 비어 있는
  // 줄이 남아, 화면이 무엇을 말하려는지 알 수 없게 된다.
  if (typeof value === 'string') return value.trim() === '' ? '없음' : value;
  if (Array.isArray(value)) return value.length === 0 ? '없음' : value.map(plain).join(', ');
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    return entries.length === 0
      ? '없음'
      : entries.map(([key, entry]) => `${key}: ${plain(entry)}`).join(' · ');
  }
  return String(value);
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
