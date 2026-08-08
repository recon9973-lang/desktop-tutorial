'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button, FormError } from '@veo/ui';

import own from '../issues.module.css';

/** 고를 수 있는 진단 실행 하나. 화면에 보일 말은 서버에서 온 값으로만 만든다. */
export interface SelectableScanRun {
  readonly id: string;
  readonly label: string;
}

interface Requested {
  readonly check_id: string;
  readonly target_urls: readonly string[];
  readonly note_ko: string;
}

interface Recorded {
  readonly state_label_ko: string;
  readonly outcome: string;
  readonly reason_ko: string;
}

/** 판정 코드를 사람 말로. 모르는 값은 지어내지 않고 그대로 보인다. */
const OUTCOME_LABELS_KO: Record<string, string> = {
  RESOLVED: '해결 확인',
  STILL_FAILING: '여전히 문제 있음',
  INCONCLUSIVE: '판정 불가',
};

function outcomeLabel(value: string): string {
  return OUTCOME_LABELS_KO[value] ?? value;
}

/**
 * 이슈를 닫는 자리 — 그리고 **여기가 유일한 자리다.**
 *
 * 서버 규칙상 해결(`VERIFIED_RESOLVED`)로 가는 간선은 하나뿐이고, 그 간선은 사람이
 * 밟을 수 없다. 재측정에서 그 검사가 통과했을 때만 열린다:
 *
 * > "해결(VERIFIED_RESOLVED)은 표적 재측정에서 해당 검사가 통과했을 때만 기록됩니다."
 * > (`apps/api/src/veo/issues/lifecycle.py:304`)
 *
 * 규칙은 처음부터 옳았는데 **그 규칙을 밟을 화면이 없었다.** 그래서 이슈가 열리고
 * 진행되지만 닫히지 않았다. 이 칸이 그 구멍이다.
 *
 * 두 단계로 나눈 것은 서버가 그렇게 나눠 두었기 때문이다.
 *
 * 1. **재검사 요청** — 이슈가 `VERIFYING` 으로 가고, 무엇을 다시 재야 하는지가 나온다.
 * 2. **진단으로 확인** — 다시 잰 진단을 고른다. 판정은 우리가 고르지 않는다.
 *
 * **판정을 고르는 칸이 없는 것이 요점이다.** 있으면 아무것도 안 고치고 대시보드만
 * 깨끗해진다. 여기서 할 수 있는 것은 "이 진단을 보라" 까지이고, 그 진단이 무엇을
 * 말하는지는 진단이 말한다.
 */
export function VerificationPanel({
  issueId,
  state,
  scanRuns,
}: {
  readonly issueId: string;
  readonly state: string;
  /** 이 이슈가 속한 프로젝트의 최근 진단들. 비어 있으면 고를 것이 없다는 뜻이다. */
  readonly scanRuns: readonly SelectableScanRun[];
}) {
  const router = useRouter();
  const [scanRunId, setScanRunId] = useState(scanRuns[0]?.id ?? '');
  const [requested, setRequested] = useState<Requested | null>(null);
  const [recorded, setRecorded] = useState<Recorded | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const awaitingMeasurement = state === 'VERIFYING';

  async function send(step: 'request' | 'result'): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/issue-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          issueId,
          step,
          ...(step === 'result' ? { scanRunId } : {}),
        }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

      if (!response.ok) {
        // 엔진의 거부 문장은 지금 갈 수 있는 상태를 이름으로 알려 준다. 그대로 보인다.
        setError(
          typeof record['message'] === 'string' ? record['message'] : '처리하지 못했습니다.',
        );
        return;
      }

      if (step === 'request') {
        const payload = record['requested'] as { request?: Requested } | undefined;
        setRequested(payload?.request ?? null);
        setRecorded(null);
      } else {
        setRecorded((record['recorded'] as Recorded | undefined) ?? null);
      }
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={own.verification}>
      <p className={own.verificationLede}>
        이 지적은 <strong>다시 재서 통과했을 때만</strong> 닫힙니다. 손으로 &lsquo;해결&rsquo;
        로 옮기는 길은 없습니다 — 있으면 고치지 않고도 목록이 깨끗해집니다.
      </p>

      <div className={own.verificationStep}>
        <p className={own.verificationStepHead}>1. 표적 재검사 요청</p>
        <p className={own.verificationHint}>
          사이트 전체를 다시 진단하지 않습니다. 이 지적이 걸린 <strong>검사 하나와 URL</strong>
          만 다시 봅니다.
        </p>
        <Button type="button" variant="secondary" busy={busy} onClick={() => send('request')}>
          재검사 요청
        </Button>

        {requested !== null ? (
          <div className={own.verificationTarget}>
            <p>
              다시 잴 것: <span className={own.check}>{requested.check_id}</span>
            </p>
            <ul className={own.verificationUrls}>
              {requested.target_urls.map((url) => (
                <li key={url}>{url}</li>
              ))}
            </ul>
            {requested.note_ko !== '' ? <p>{requested.note_ko}</p> : null}
          </div>
        ) : null}
      </div>

      <div className={own.verificationStep}>
        <p className={own.verificationStepHead}>2. 다시 잰 진단으로 확인</p>

        {!awaitingMeasurement ? (
          <p className={own.verificationHint}>
            먼저 재검사를 요청하십시오. <strong>재측정 대기</strong> 상태가 된 뒤에 고를 수
            있습니다.
          </p>
        ) : scanRuns.length === 0 ? (
          <p className={own.verificationHint}>
            고를 진단이 없습니다. 위에서 요청한 범위를 다시 진단한 뒤 이 화면으로 돌아오십시오.
          </p>
        ) : (
          <>
            <p className={own.verificationHint}>
              고른 진단이 <strong>무엇을 쟀는지</strong>로 판정합니다. 여기서 결과를 정하지
              않습니다 — 영향 URL 중 일부만 재졌거나 그 검사 결과가 없으면{' '}
              <strong>판정 불가</strong>이며 해결로 인정되지 않습니다.
            </p>
            <select
              className={own.verificationSelect}
              aria-label="확인에 쓸 진단"
              value={scanRunId}
              onChange={(event) => setScanRunId(event.target.value)}
            >
              {scanRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.label}
                </option>
              ))}
            </select>
            <Button type="button" busy={busy} onClick={() => send('result')}>
              이 진단으로 확인
            </Button>
          </>
        )}

        {recorded !== null ? (
          <p
            className={
              recorded.outcome === 'RESOLVED' ? own.verificationPassed : own.verificationFailed
            }
          >
            {outcomeLabel(recorded.outcome)} — {recorded.state_label_ko}
            {recorded.reason_ko !== '' ? ` · ${recorded.reason_ko}` : ''}
          </p>
        ) : null}
      </div>

      <FormError message={error} />
    </div>
  );
}
