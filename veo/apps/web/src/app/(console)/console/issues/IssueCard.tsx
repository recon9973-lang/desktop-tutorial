'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button, FormError } from '@veo/ui';

import { ownerLabel, type Issue } from '@/lib/issues';

import styles from './issues.module.css';

/**
 * 문제 한 건 — 그리고 **지금 무엇을 할 수 있는가.**
 *
 * 버튼 목록을 이 파일이 가지고 있지 않다. `issue.human_transitions` 는 엔진이 상태
 * 표에서 뽑아 준 것이고, 화면은 그것을 그대로 그린다. 그래서 여기에 `해결` 버튼이
 * 생길 수 없다 — 사람이 걸을 수 있는 어떤 간선도 그 상태로 가지 않기 때문이다.
 *
 * `수정했다고 보고됨` 은 **열린 상태**다. 카드에서 이 상태를 해결된 것처럼 그리지
 * 않는다. 그렇게 그리는 순간 만들어지는 것이 바뀐 것 없는 사이트 위의 깨끗한
 * 대시보드다.
 */
export function IssueCard({
  issue,
  linkToDetail = true,
}: {
  readonly issue: Issue;
  /** 상세 화면 자신은 자기 자신으로 가는 링크를 그리지 않는다. */
  readonly linkToDetail?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const awaitingMeasurement = issue.state === 'FIX_CLAIMED' || issue.state === 'VERIFYING';

  async function move(toState: string): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/issue-state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issueId: issue.id, toState }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        // 엔진의 거부 문장은 지금 갈 수 있는 상태를 이름으로 알려 준다. 그대로 보인다.
        setError(
          typeof record['message'] === 'string' ? record['message'] : '변경하지 못했습니다.',
        );
        return;
      }
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className={issue.recurrence_count > 0 ? styles.issueRecurred : styles.issue}>
      <p className={styles.issueHead}>
        <span className={styles.severity}>{issue.severity}</span>
        {linkToDetail ? (
          <Link href={`/console/issues/${issue.id}`} className={styles.issueTitle}>
            {issue.title_ko}
          </Link>
        ) : (
          <span className={styles.issueTitle}>{issue.title_ko}</span>
        )}
      </p>

      <p className={styles.state}>
        <span className={issue.is_open ? styles.openState : styles.closedState}>
          {issue.state_label_ko}
        </span>
        <span className={styles.owner}>조치 담당 {ownerLabel(issue.remediation_owner)}</span>
        <span className={styles.urls}>영향 URL {issue.affected_url_count}개</span>
        <span className={styles.check}>{issue.check_id}</span>
      </p>

      {/* 재측정 없이는 닫히지 않는다는 사실을, 그 상태에 놓인 건에서 직접 말한다. */}
      {awaitingMeasurement ? (
        <p className={styles.unverified}>
          재측정으로 확인되지 않았습니다. 이 건은 아직 <strong>열린 문제</strong>입니다.
        </p>
      ) : null}

      {issue.recurrence_count > 0 ? (
        <p className={styles.recurrence}>
          해결 확인 후 {issue.recurrence_count}회 재발했습니다. 고쳤다고 믿고 넘어간 자리가
          열려 있었다는 뜻입니다.
        </p>
      ) : null}

      {issue.business_impact_ko !== null ? (
        <p className={styles.impact}>{issue.business_impact_ko}</p>
      ) : null}

      {issue.human_transitions.length > 0 ? (
        <div className={styles.actions}>
          {issue.human_transitions.map((move_) => (
            <Button
              key={move_.to_state}
              type="button"
              variant="secondary"
              busy={busy}
              title={move_.reason_ko}
              onClick={() => move(move_.to_state)}
            >
              {move_.label_ko}
            </Button>
          ))}
        </div>
      ) : (
        <p className={styles.noMoves}>
          담당자가 손으로 바꿀 수 있는 상태가 없습니다. 다음 변화는 재측정이 정합니다.
        </p>
      )}

      <FormError message={error} />
    </li>
  );
}
