'use client';

import { useState } from 'react';
import { Button, FormError } from '@veo/ui';

import own from './usage.module.css';

/**
 * 경보가 실제로 닿는지 한 번 보내 본다.
 *
 * ## 왜 필요한가
 *
 * 경보는 **사고가 났을 때만** 울린다. 그래서 주소를 넣은 사람이 맞는지 확인할 방법이
 * 없었다 — 잘못 넣어 두면 정작 필요한 날 조용하고, 그날까지 아무도 모른다.
 *
 * 실제 경보와 **같은 통로**로 보낸다. 시험용 우회로를 따로 두면 그 우회로만 동작하는
 * 상태를 못 잡는다.
 *
 * ## 화면에 주소를 그리지 않는다
 *
 * 결과는 셋뿐이다 — 닿았다 · 주소가 없다 · 보냈으나 실패. 주소 자체를 보여 주면 이
 * 화면을 열 수 있는 사람 모두가 그것을 갖는다.
 */
export function AlertTestButton() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send(): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch('/api/alert-test', { method: 'POST' });
      const payload: unknown = await response.json().catch(() => null);
      const body =
        typeof payload === 'object' && payload !== null
          ? (payload as Record<string, unknown>)
          : {};

      if (!response.ok || body['ok'] !== true) {
        setError(
          typeof body['message'] === 'string'
            ? body['message']
            : '시험 발송에 실패했습니다.',
        );
        return;
      }
      setResult(typeof body['messageKo'] === 'string' ? body['messageKo'] : '보냈습니다.');
    } catch {
      setError('서버에 연결하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={own.alertTest}>
      <p className={own.alertTestNote}>
        경보는 사고가 났을 때만 울립니다. 주소를 제대로 넣었는지는 한 번 보내 봐야
        알 수 있습니다.
      </p>
      <Button type="button" onClick={() => void send()} busy={busy}>
        경보 시험 발송
      </Button>
      {/* `null` 일 때도 켜 둔다 — 라이브 영역을 붙였다 떼면 낭독기가 못 읽는다. */}
      <FormError message={error} />
      {result === null ? null : <p className={own.alertTestResult}>{result}</p>}
    </div>
  );
}
