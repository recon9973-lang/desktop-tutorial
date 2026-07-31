'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button, FormError } from '@veo/ui';

import styles from './reports.module.css';

/**
 * 고를 수 있는 진단 하나 — **이미 사람이 읽을 수 있게 다듬어진 채로** 온다.
 *
 * 시각을 여기서 만들지 않는다. 서버 컴포넌트가 만들어 글자로 넘긴다. 함수를 이 경계
 * 너머로 넘기면 렌더가 깨지는데, 그 깨짐은 **로그인한 화면에서만** 보인다 — 빌드도
 * 타입체크도 잡아주지 않는다.
 */
export interface RunChoice {
  readonly scanRunId: string;
  readonly label: string;
}

/**
 * 리포트를 발행하는 칸.
 *
 * 입력이 **제목과 진단 실행 두 개뿐**인 것이 요점이다. 점수를 손으로 넣는 칸이 없다.
 * 있으면 언젠가 채워지고, 그 순간 문서의 숫자는 아무도 재지 않은 값이 된다.
 *
 * 고를 수 있는 실행은 엔진이 준 것만 그린다. 측정 조건이 기록되지 않은 실행은 목록에
 * 아예 오지 않는다 — 골랐다가 거절당하는 것보다 낫다.
 */
export function PublishForm({ runs }: { readonly runs: readonly RunChoice[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [scanRunId, setScanRunId] = useState(runs[0]?.scanRunId ?? '');

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scanRunId, title }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        // 엔진의 거부 문장은 왜 이 실행으로 문서를 만들 수 없는지를 말한다. 그대로 보인다.
        setError(
          typeof record['message'] === 'string' ? record['message'] : '발행하지 못했습니다.',
        );
        return;
      }
      setTitle('');
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  if (runs.length === 0) {
    return (
      <p className={styles.blocked}>
        <strong>리포트로 만들 수 있는 진단이 없습니다.</strong> 진단을 먼저 실행해 주십시오.
        문서의 숫자는 실제 측정에서만 옵니다 — 손으로 채워 넣는 길은 이 화면에 없습니다.
      </p>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <label className={styles.label}>
        리포트 제목 <span className={styles.required}>필수</span>
        <input
          className={styles.input}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="온담한의원 7월 진단"
          required
        />
      </label>

      <label className={styles.label}>
        어느 진단으로 만들까요
        <select
          className={styles.input}
          value={scanRunId}
          onChange={(event) => setScanRunId(event.target.value)}
        >
          {runs.map((run) => (
            <option key={run.scanRunId} value={run.scanRunId}>
              {run.label}
            </option>
          ))}
        </select>
        <span className={styles.hint}>
          그 실행이 남긴 점수·항목별 판정·근거·측정 조건이 그대로 문서가 됩니다. 발행한
          버전은 고칠 수 없습니다.
        </span>
      </label>

      <div className={styles.actions}>
        <Button type="submit" busy={busy}>
          발행
        </Button>
      </div>
      <FormError message={error} />
    </form>
  );
}
