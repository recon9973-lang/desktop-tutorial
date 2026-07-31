'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, FormError } from '@veo/ui';

import type { ReviewQueueItem } from '@/lib/observations';

import styles from './review.module.css';

/**
 * 한 건을 판정하는 카드.
 *
 * 이 화면이 지키는 것 넷.
 *
 * 1. **기계가 실제로 본 글자를 보여준다.** 요약하면 "백세온담한의원" 과 "온담한의원" 의
 *    차이가 사라지고, 그 차이가 이 판정의 전부다.
 * 2. **착수하지 않으면 판정 버튼이 없다.** 원문을 열어 보지 않고 확정하는 길을 화면에서
 *    부터 막는다. 서버도 막지만, 서버가 막는 것을 화면이 권하면 안 된다.
 * 3. **기각에는 사유를 고르게 한다.** 자유 서술은 셀 수 없고, 기각을 기록하는 이유가
 *    자동 판정이 어디서 빗나가는지 세기 위해서다.
 * 4. **자동 판정이 뭐라고 했는지를 계속 보여준다.** 사람의 결론이 그것을 덮지 않는다는
 *    사실이 화면에서도 보여야 한다.
 */
export function ReviewCard({
  item,
  reasons,
}: {
  readonly item: ReviewQueueItem;
  readonly reasons: readonly { readonly value: string; readonly label_ko: string }[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decision, setDecision] = useState<'CONFIRMED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE'>(
    'CONFIRMED',
  );
  const [reason, setReason] = useState('');
  const [note, setNote] = useState('');

  async function send(payload: Record<string, unknown>): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/observation-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assessmentId: item.assessment_id, ...payload }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        setError(
          typeof record['message'] === 'string' ? record['message'] : '처리하지 못했습니다.',
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
    <li className={styles.card}>
      <p className={styles.head}>
        <span className={styles.band}>{item.band_label_ko}</span>
        <span className={styles.kind}>{item.kind}</span>
        <span className={styles.stage}>{item.stage_label_ko}</span>
      </p>

      <p className={styles.quote}>&ldquo;{item.claim_text}&rdquo;</p>

      {/* 사람의 결론이 이것을 덮지 않는다. 그 사실이 화면에서도 보여야 한다. */}
      <p className={styles.machine}>
        <span className={styles.machineLabel}>자동 판정 {item.automated_verdict}</span>
        {item.automated_rationale_ko}
      </p>

      {item.is_held_by_someone ? (
        <p className={styles.heldElsewhere}>
          다른 검수자가 맡고 있습니다. 같은 지적을 두 사람이 각각 판정하면 어느 쪽이 고객에게
          나가는지 알 수 없게 됩니다.
        </p>
      ) : item.is_mine ? (
        <div className={styles.decide}>
          <fieldset className={styles.choices}>
            <legend className={styles.legend}>검수 결론</legend>
            {(
              [
                ['CONFIRMED', '지적이 맞습니다'],
                ['REJECTED', '자동 판정이 틀렸습니다'],
                ['NEEDS_MORE_EVIDENCE', '지금 근거로는 판단할 수 없습니다'],
              ] as const
            ).map(([value, label]) => (
              <label key={value} className={styles.choice}>
                <input
                  type="radio"
                  name={`decision-${item.assessment_id}`}
                  value={value}
                  checked={decision === value}
                  onChange={() => setDecision(value)}
                />
                {label}
              </label>
            ))}
          </fieldset>

          {decision === 'REJECTED' ? (
            <label className={styles.field}>
              기각 사유
              <select
                className={styles.select}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              >
                <option value="">선택해 주십시오</option>
                {reasons.map((one) => (
                  <option key={one.value} value={one.value}>
                    {one.label_ko}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className={styles.field}>
            메모 (선택)
            <textarea
              className={styles.textarea}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={2}
            />
          </label>

          <div className={styles.actions}>
            <Button
              type="button"
              busy={busy}
              onClick={() =>
                send({ step: 'decide', decision, rejectionReason: reason, note })
              }
            >
              결론 기록
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => send({ step: 'release' })}
            >
              판단 없이 반납
            </Button>
          </div>
        </div>
      ) : (
        <div className={styles.actions}>
          <Button type="button" busy={busy} onClick={() => send({ step: 'claim' })}>
            착수하기
          </Button>
          <p className={styles.claimNote}>
            착수해야 판정할 수 있습니다. 원문을 열어 보지 않은 확정이 고객 문서에 실리지
            않게 하기 위해서입니다.
          </p>
        </div>
      )}

      <FormError message={error} />
    </li>
  );
}
