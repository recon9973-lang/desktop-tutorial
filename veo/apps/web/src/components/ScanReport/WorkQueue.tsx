'use client';

/**
 * 작업 큐 (콘솔 재설계 ③) — 담당자가 위에서부터 하나씩 처리하는 목록.
 *
 * 시안 v2.2 그대로: 카드 더미가 아니라 **대시보드 표** — 한 컨테이너, 실선 구분,
 * 상태는 점+라벨, 이득은 +N점 알약, 담당은 칩. 행을 열면 진단 결과·조치·붙여넣을
 * 코드가 나오고, 긴 본문 아래에도 접기 버튼이 있다(위로 되돌아가지 않아도 닫힌다).
 *
 * 화면이 지키는 것:
 * - **순서를 다시 계산하지 않는다.** 엔진(rank_improvements)이 실제 채점 산식으로
 *   매긴 순서를 그대로 그린다 — 위에서부터 처리하면 점수가 가장 빨리 오른다.
 * - 상한에 막힌 항목은 "+0점"이 아니라 "상한 해제 후"로 — 숫자를 지어내지 않는다.
 * - 담당 칩 필터는 세는 것만 한다. 숨긴 건수는 칩에 그대로 보인다.
 */

import { useState } from 'react';

import type { ConsoleScanResult, Improvement, Issue, Outcome } from '@/lib/console-scan';

import styles from './WorkQueue.module.css';

const OWNERS: Record<string, string> = {
  DEVELOPER: '개발',
  MARKETER: '마케팅',
  BUSINESS_OWNER: '사업 담당',
  OPERATIONS: '운영',
};

function ownerLabel(owner: string): string {
  return OWNERS[owner] ?? owner;
}

const STATUS_LABELS: Record<string, { readonly label: string; readonly className: string }> = {
  FAIL: { label: '실패', className: styles.stFail! },
  WARNING: { label: '주의', className: styles.stWarn! },
  UNKNOWN: { label: '측정 불가', className: styles.stUnknown! },
};

interface QueueRow {
  readonly improvement: Improvement;
  readonly issue: Issue | null;
  readonly outcome: Outcome | null;
}

function whereOf(row: QueueRow): string {
  const urls = row.issue?.affectedUrls ?? [];
  if (urls.length === 0) return '';
  const first = urls[0]!.replace(/^https?:\/\//, '');
  return urls.length === 1 ? first : `${first} 외 ${urls.length - 1}장`;
}

export function WorkQueue({
  result,
  issuesHrefBase = null,
}: {
  readonly result: ConsoleScanResult;
  /**
   * "이슈로 추적" 링크의 앞부분(끝에 check_id 가 붙는다). 이슈는 진단 저장이 이미
   * 만들어 두므로 여기서 새로 만들지 않는다 — 같은 검사의 이슈 화면으로 건너갈 뿐이다.
   */
  readonly issuesHrefBase?: string | null;
}) {
  const [owner, setOwner] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  if (result.improvements.length === 0) return null;

  const issueById = new Map(result.issues.map((issue) => [issue.checkId, issue]));
  const outcomeById = new Map(result.outcomes.map((item) => [item.checkId, item]));
  const rows: readonly QueueRow[] = result.improvements.map((improvement) => ({
    improvement,
    issue: issueById.get(improvement.checkId) ?? null,
    outcome: outcomeById.get(improvement.checkId) ?? null,
  }));

  const counts = new Map<string, number>();
  for (const row of rows) {
    const key = row.improvement.remediationOwner;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const visible = owner === null
    ? rows
    : rows.filter((row) => row.improvement.remediationOwner === owner);
  const allBlocked = rows.every((row) => row.improvement.blockedByCap);

  return (
    <section className={styles.queue} aria-labelledby="work-queue">
      <div className={styles.head}>
        <h2 id="work-queue" className={styles.title}>
          작업 큐
        </h2>
        <p className={styles.sub}>
          {allBlocked
            ? '상한이 걸려 있어, 아래를 고쳐도 상한이 풀리기 전까지는 점수가 오르지 않습니다.'
            : '위에서부터 처리하면 점수가 가장 빨리 오릅니다 — 상승폭은 실제 채점 산식 값입니다.'}
        </p>
      </div>

      <div className={styles.chips} role="group" aria-label="담당 필터">
        <button
          type="button"
          className={owner === null ? `${styles.chip} ${styles.chipOn}` : styles.chip}
          onClick={() => setOwner(null)}
        >
          전체 {rows.length}
        </button>
        {[...counts.entries()].map(([key, count]) => (
          <button
            key={key}
            type="button"
            className={owner === key ? `${styles.chip} ${styles.chipOn}` : styles.chip}
            onClick={() => setOwner(owner === key ? null : key)}
          >
            {ownerLabel(key)} {count}
          </button>
        ))}
      </div>

      <div className={styles.table}>
        {visible.map((row) => (
          <QueueItem
            key={row.improvement.checkId}
            row={row}
            issuesHrefBase={issuesHrefBase}
            open={openId === row.improvement.checkId}
            onToggle={() =>
              setOpenId(openId === row.improvement.checkId ? null : row.improvement.checkId)
            }
          />
        ))}
      </div>
    </section>
  );
}

function QueueItem({
  row,
  issuesHrefBase,
  open,
  onToggle,
}: {
  readonly row: QueueRow;
  readonly issuesHrefBase: string | null;
  readonly open: boolean;
  readonly onToggle: () => void;
}) {
  const { improvement, issue, outcome } = row;
  const status = STATUS_LABELS[outcome?.status ?? 'UNKNOWN'] ?? STATUS_LABELS.UNKNOWN!;
  const where = whereOf(row);
  const expandable = issue !== null;

  return (
    <article className={styles.task}>
      <button
        type="button"
        className={styles.taskHead}
        onClick={expandable ? onToggle : undefined}
        aria-expanded={expandable ? open : undefined}
        disabled={!expandable}
      >
        <span className={`${styles.status} ${status.className}`}>{status.label}</span>
        <span className={styles.taskTitle}>{improvement.title}</span>
        {where === '' ? null : <span className={styles.where}>{where}</span>}
        <span className={styles.owner}>{ownerLabel(improvement.remediationOwner)}</span>
        <span className={styles.gain}>
          {improvement.blockedByCap ? '상한 해제 후' : `+${improvement.gainPoints.toFixed(1)}점`}
        </span>
      </button>

      {open && issue !== null ? (
        <div className={styles.taskBody}>
          <p className={styles.label}>진단 결과</p>
          <p>{issue.summary}</p>

          {issue.businessImpact === '' ? null : (
            <>
              <p className={styles.label}>사업 영향</p>
              <p>{issue.businessImpact}</p>
            </>
          )}

          <p className={styles.label}>이렇게 고치세요</p>
          <p>{issue.remediation}</p>

          {issue.fixExample !== null ? <FixCode code={issue.fixExample} /> : null}

          {issue.affectedUrls.length > 0 ? (
            <>
              <p className={styles.label}>걸린 페이지</p>
              <ul className={styles.urls}>
                {issue.affectedUrls.slice(0, 10).map((url) => (
                  <li key={url}>
                    <code>{url}</code>
                  </li>
                ))}
                {issue.affectedUrls.length > 10 ? (
                  <li>… 외 {issue.affectedUrls.length - 10}장</li>
                ) : null}
              </ul>
            </>
          ) : null}

          {issue.reverificationNote === '' ? null : (
            <>
              <p className={styles.label}>고친 뒤 확인</p>
              <p>{issue.reverificationNote}</p>
            </>
          )}

          <div className={styles.taskFoot}>
            <span className={styles.meta}>
              심각도 {improvement.severity}
              {issue.affectedUrls.length > 0 ? ` · 걸린 페이지 ${issue.affectedUrls.length}장` : ''}
              {issuesHrefBase === null ? null : (
                <>
                  {' '}
                  <a
                    className={styles.issueLink}
                    href={`${issuesHrefBase}${encodeURIComponent(improvement.checkId)}`}
                  >
                    → 이슈로 추적
                  </a>
                </>
              )}
            </span>
            {/* 긴 본문을 다 읽고 나서 위로 되돌아가지 않아도 닫힌다. */}
            <button type="button" className={styles.fold} onClick={onToggle}>
              접기 ▴
            </button>
          </div>
        </div>
      ) : null}
    </article>
  );
}

function FixCode({ code }: { readonly code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <>
      {/* 예시임을 라벨에 못 박는다 — 예시 속 브랜드(온담의원 등)는 가상의 것인데,
          "붙여넣을 코드" 라고만 적으면 측정한 사이트의 실데이터로 읽힌다(사용자 보고). */}
      <p className={styles.label}>예시 코드 — 업체명·내용은 우리 것으로 바꿔 쓰세요</p>
      <div className={styles.codeWrap}>
        <button
          type="button"
          className={styles.copy}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(code);
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1600);
            } catch {
              // 클립보드 권한이 없으면 조용히 둔다 — 코드는 화면에 있으니 직접 긁으면 된다.
            }
          }}
        >
          {copied ? '복사됨 ✓' : '코드 복사'}
        </button>
        <pre className={styles.code}>{code}</pre>
      </div>
    </>
  );
}
