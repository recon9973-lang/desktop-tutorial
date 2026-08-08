'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { FormError } from '@veo/ui';

import own from '../issues.module.css';

export interface AssignableMember {
  readonly id: string;
  readonly label: string;
}

/** 지정 해제를 뜻하는 값. 빈 문자열이라 `select` 의 기본 없음 항목과 그대로 맞는다. */
const UNASSIGNED = '';

/**
 * 이 건을 누가 맡았는가.
 *
 * 서버에는 처음부터 있었는데(`POST /api/issues/{id}/assignee`) 화면에서 부르는 곳이
 * 없었다. 그래서 이슈가 **아무도 맡지 않은 채로** 목록에 쌓였다.
 *
 * 고르면 바로 저장한다. "저장" 버튼을 따로 두지 않는 것은, 한 칸짜리 선택에서 버튼을
 * 안 눌러 안 바뀐 것을 바뀐 줄 아는 일이 흔하기 때문이다.
 *
 * **비활성 계정은 목록에 없다.** 떠난 사람에게 일을 맡길 수는 없다.
 */
export function AssigneePicker({
  issueId,
  assignedTo,
  members,
}: {
  readonly issueId: string;
  readonly assignedTo: string | null;
  readonly members: readonly AssignableMember[];
}) {
  const router = useRouter();
  const [current, setCurrent] = useState(assignedTo ?? UNASSIGNED);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pick(next: string): Promise<void> {
    if (busy) return;
    const previous = current;
    setCurrent(next);
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/issue-assignee', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issueId, userId: next === UNASSIGNED ? null : next }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

      if (!response.ok) {
        // 저장이 안 됐으면 화면도 되돌린다. 안 되돌리면 화면만 바뀐 채로 남는다.
        setCurrent(previous);
        setError(
          typeof record['message'] === 'string' ? record['message'] : '지정하지 못했습니다.',
        );
        return;
      }
      router.refresh();
    } catch {
      setCurrent(previous);
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  if (members.length === 0) {
    return (
      <p className={own.verificationHint}>
        지정할 수 있는 구성원이 없습니다. 구성원 화면에서 먼저 초대하십시오.
      </p>
    );
  }

  return (
    <div className={own.assignee}>
      <label className={own.verificationHint} htmlFor="issue-assignee">
        이 건을 맡을 사람
      </label>
      <select
        id="issue-assignee"
        className={own.verificationSelect}
        value={current}
        disabled={busy}
        onChange={(event) => void pick(event.target.value)}
      >
        <option value={UNASSIGNED}>맡은 사람 없음</option>
        {members.map((member) => (
          <option key={member.id} value={member.id}>
            {member.label}
          </option>
        ))}
      </select>
      <FormError message={error} />
    </div>
  );
}
