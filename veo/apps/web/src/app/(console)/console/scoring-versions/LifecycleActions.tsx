'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button, FormError } from '@veo/ui';

import styles from './lab.module.css';

/**
 * 이 버전에 지금 할 수 있는 일 — **서버가 허락한 것만**.
 *
 * 화면은 상태 기계를 갖지 않는다. 어떤 상태에서 무엇이 가능한지는 엔진이 정하고
 * (`allowed_transitions`), 여기서는 받은 목록을 버튼으로 그릴 뿐이다. 두 벌로 두면
 * 화면이 "발행" 을 보여주는데 엔진이 거절하는 날이 오고, 그때 누른 사람은 자기가 뭘
 * 잘못했는지 알 수 없다.
 *
 * 되돌릴 수 없는 동작(발행·폐기)은 **한 번 더 묻는다.** 발행된 명세의 숫자는 불변이라
 * 잘못 누르면 되돌리는 길이 새 버전을 내는 것뿐이다.
 */

const LABELS: Record<string, string> = {
  submit: '검토 요청',
  approve: '승인',
  'send-back': '초안으로 되돌리기',
  publish: '발행',
  retire: '폐기',
  'golden-run': '골든 검증 실행',
};

/** 되돌릴 수 없어서 한 번 더 묻는 동작. */
const CONFIRM: Record<string, string> = {
  publish:
    '발행하면 이 명세의 숫자는 바뀌지 않습니다. 되돌리려면 새 버전을 내야 합니다. 발행할까요?',
  retire: '폐기하면 이 명세로는 더 이상 채점하지 않습니다. 폐기할까요?',
};

export function LifecycleActions({
  versionId,
  allowed,
}: {
  readonly versionId: string;
  /** 엔진이 준 목록. 비어 있으면 지금 할 수 있는 일이 없다는 뜻이다. */
  readonly allowed: readonly string[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: string): Promise<void> {
    if (busy !== null) return;
    const question = CONFIRM[action];
    if (question !== undefined && !window.confirm(question)) return;

    setBusy(action);
    setError(null);
    try {
      const response = await fetch('/api/scoring-lab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ versionId, action }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        setError(
          typeof payload === 'object' && payload !== null && 'message' in payload
            ? String((payload as { message: unknown }).message)
            : '처리하지 못했습니다.',
        );
        return;
      }
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다.');
    } finally {
      setBusy(null);
    }
  }

  // 골든 검증은 상태를 바꾸지 않으므로 전이 목록에 없다. 언제든 다시 돌릴 수 있어야
  // 하므로 따로 붙인다 — 검증하지 않고 발행하는 것을 막는 유일한 수단이다.
  const actions = [...allowed, 'golden-run'];

  return (
    <div className={styles.actions}>
      {actions.length === 0 ? (
        <p className={styles.actionsNote}>지금 이 버전에 할 수 있는 일이 없습니다.</p>
      ) : (
        <div className={styles.actionRow}>
          {actions.map((action) => (
            <Button
              key={action}
              type="button"
              variant={action === 'publish' ? 'primary' : 'secondary'}
              disabled={busy !== null}
              onClick={() => void run(action)}
            >
              {busy === action ? '처리 중…' : (LABELS[action] ?? action)}
            </Button>
          ))}
        </div>
      )}
      <FormError message={error} />
    </div>
  );
}
