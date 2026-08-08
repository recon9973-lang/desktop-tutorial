'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button, FormError } from '@veo/ui';

import { MIN_RUNS_FOR_EXPLORATION } from '@/lib/sampling';

import styles from './geo.module.css';
import type { RunnableEngine } from './RunForm';

export interface SelectableProject {
  readonly id: string;
  readonly label: string;
}

/** 서버가 돌려주는 예상 규모. 화면은 이 값을 그대로 옮겨 적는다. */
interface Estimate {
  readonly total_calls: number;
  readonly amount_usd: number | null;
  readonly measurement: string;
  readonly remedies_ko: readonly string[];
  readonly summary_ko: string;
}

/** 서버와 같은 상한. */
const MAX_QUESTIONS = 20;

/** 입력칸의 줄을 검색어 목록으로. 빈 줄과 중복은 버린다. */
export function readQuestions(raw: string): string[] {
  return [...new Set(raw.split('\n').map((line) => line.trim()).filter((line) => line !== ''))];
}

/**
 * 수동 측정 — 관리자가 그 자리에서 검색어를 넣고 잰다.
 *
 * 정기 관측과 나란히 두면서도 **같은 것으로 보이지 않게** 해야 한다. 둘은 다른 측정이다.
 * 정기 관측은 발행된 질문 집합을 정해진 주기로 돌리고, 이쪽은 사람이 그 순간 검색어를
 * 고른다. 조건(엔진·모델·검색모드)이 똑같아도 **고른 사람이 다르게 만든다.**
 *
 * 그래서 이 화면이 두 가지를 반드시 말한다.
 *
 * **하나 — 이 값은 추이에 안 올라간다.** 숨기면 사장님은 이걸 재고 그래프가 왜 안
 * 움직이는지 묻게 된다. 서버도 섞는 것을 거부하지만, 거부는 화면에 안 보인다.
 *
 * **둘 — 누르면 돈이 나간다.** 그래서 누르기 전에 서버에 규모를 물어 보여준다.
 * 호출 수는 정확하고, 금액은 같은 조건으로 이미 잰 토큰이 있을 때만 나온다. 없으면
 * 금액 자리를 비우고 **왜 못 내는지**를 적는다 — 지어낸 금액은 실측과 구별되지 않는다.
 */
export function ManualRunForm({
  projects,
  engines,
}: {
  readonly projects: readonly SelectableProject[];
  readonly engines: readonly RunnableEngine[];
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState(projects[0]?.id ?? '');
  const [raw, setRaw] = useState('');
  const [engine, setEngine] = useState(engines[0]?.engine ?? '');
  const [model, setModel] = useState(engines[0]?.models[0]?.id ?? '');
  const [repetitions, setRepetitions] = useState(MIN_RUNS_FOR_EXPLORATION);
  const [browsing, setBrowsing] = useState(true);
  const [searchOff, setSearchOff] = useState(false);
  // 예상치는 **어떤 조건의 답인지**와 함께 들고 다닌다. 조건이 바뀌면 지우는 대신 안
  // 쓴다 — 지우려면 조건이 바뀔 때마다 상태를 건드려야 하고, 그 사이 한 번 더 그려지는
  // 동안 옛 숫자가 화면에 남는다. 그 숫자를 보고 누르면 실제와 다른 규모를 승인한 것이다.
  const [answered, setAnswered] = useState<{ key: string; value: Estimate } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 같은 화면에서 두 번 눌러도 두 번 실행되지 않게 한다. 측정은 돈이 나가는 일이다.
  const attemptKey = useRef<string>(crypto.randomUUID());

  const chosen = engines.find((one) => one.engine === engine);
  const models = chosen?.models ?? [];
  const canTurnSearchOff = chosen?.supportsSearchOff ?? true;
  const modes = [
    ...(browsing ? ['BROWSING'] : []),
    ...(searchOff && canTurnSearchOff ? ['NO_BROWSING'] : []),
  ];
  const questions = readQuestions(raw);
  const tooMany = questions.length > MAX_QUESTIONS;

  /** 지금 화면에 걸린 조건. 서버에 물을 값이자, 돌아온 답이 아직 유효한지 가르는 열쇠. */
  const askable = questions.length > 0 && !tooMany && modes.length > 0 && model !== '';
  const key = askable
    ? [engine, model, questions.length, repetitions, modes.join('+')].join('|')
    : '';

  // 조건이 바뀌면 서버에 다시 묻는다.
  useEffect(() => {
    if (key === '') return;

    const query = new URLSearchParams({
      engine,
      model,
      questions: String(questions.length),
      repetitions: String(repetitions),
    });
    for (const mode of modes) query.append('mode', mode);

    const abort = new AbortController();
    void fetch(`/api/observation-manual?${query.toString()}`, { signal: abort.signal })
      .then(async (response) => (response.ok ? await response.json() : null))
      .then((body: unknown) => {
        const record =
          typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
        const value = record['estimate'] as Estimate | undefined;
        if (value !== undefined) setAnswered({ key, value });
      })
      .catch(() => {
        // 예상치를 못 받은 것은 실행을 막을 일이 아니다. 호출 수는 아래 곱셈으로 나온다.
      });
    return () => abort.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // 지금 조건의 답만 쓴다. 조건이 바뀌었는데 답이 아직 안 온 동안에는 서버 값이 없는
  // 것으로 친다 — 옛 조건의 금액을 지금 조건 옆에 두면 그것이 지금 값으로 읽힌다.
  const estimate = answered !== null && answered.key === key ? answered.value : null;

  function pickEngine(next: string): void {
    setEngine(next);
    setModel(engines.find((one) => one.engine === next)?.models[0]?.id ?? '');
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    if (questions.length === 0) {
      setError('잴 검색어를 한 줄에 하나씩 넣어 주십시오.');
      return;
    }
    if (tooMany) {
      setError(`검색어는 최대 ${MAX_QUESTIONS}개까지입니다.`);
      return;
    }
    if (modes.length === 0) {
      setError('검색 켬·끔 중 적어도 하나는 재야 합니다.');
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/observation-manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId,
          questions,
          engine,
          model,
          searchModes: modes,
          repetitions,
          idempotencyKey: attemptKey.current,
        }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

      if (!response.ok) {
        setError(
          typeof record['message'] === 'string'
            ? record['message']
            : '수동 측정을 시작하지 못했습니다.',
        );
        return;
      }

      const job =
        typeof record['job'] === 'object' && record['job'] !== null
          ? (record['job'] as { id?: unknown })
          : {};
      if (typeof job.id === 'string') {
        // 다음 측정은 새 열쇠로. 같은 열쇠를 남겨 두면 검색어를 바꿔 다시 눌러도
        // 첫 실행이 그대로 돌아온다.
        attemptKey.current = crypto.randomUUID();
        router.push(`/console/geo?job=${job.id}`);
        return;
      }
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  if (projects.length === 0 || engines.length === 0) return null;

  // 서버 예상치를 못 받았을 때 쓰는 값. 곱셈이라 화면에서도 정확하다.
  const calls = questions.length * repetitions * modes.length;

  return (
    <form className={styles.runForm} onSubmit={submit} noValidate>
      <p className={styles.warning}>
        수동 측정은 <strong>추이에 올라가지 않습니다.</strong> 지금 이 검색어로 우리가
        나오는지를 보는 것이고, 정기 관측과 하나의 비율로 합쳐지지 않습니다 — 잘 나오는
        검색어를 골라 재면 그것만으로 그래프가 올라가기 때문입니다.
      </p>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="manual-project">
          프로젝트
        </label>
        <select
          id="manual-project"
          className={styles.select}
          value={projectId}
          onChange={(event) => setProjectId(event.target.value)}
        >
          {projects.map((one) => (
            <option key={one.id} value={one.id}>
              {one.label}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="manual-questions">
          검색어 — 한 줄에 하나씩
        </label>
        <textarea
          id="manual-questions"
          className={styles.questions}
          value={raw}
          onChange={(event) => setRaw(event.target.value)}
          placeholder={'강남 임플란트 잘하는 곳\n임플란트 부작용'}
        />
        <p className={styles.hint}>
          지금 {questions.length}개입니다 (빈 줄과 중복은 뺐습니다). 최대 {MAX_QUESTIONS}개.
        </p>
        {tooMany ? (
          <p className={styles.warning}>
            검색어가 {questions.length}개입니다. {MAX_QUESTIONS}개까지만 한 번에 잽니다.
          </p>
        ) : null}
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="manual-engine">
          AI 엔진
        </label>
        <select
          id="manual-engine"
          className={styles.select}
          value={engine}
          onChange={(event) => pickEngine(event.target.value)}
        >
          {engines.map((one) => (
            <option key={one.engine} value={one.engine}>
              {one.label}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="manual-model">
          모델
        </label>
        <select
          id="manual-model"
          className={styles.select}
          value={model}
          onChange={(event) => setModel(event.target.value)}
        >
          {models.map((one) => (
            <option key={one.id} value={one.id}>
              {one.id}
              {one.citesSources ? ' — 출처를 돌려줍니다' : ' — 출처를 돌려주지 않습니다'}
            </option>
          ))}
        </select>
      </div>

      <fieldset className={styles.field}>
        <legend className={styles.label}>검색 모드</legend>
        <label className={styles.modeChoice}>
          <input
            type="checkbox"
            checked={browsing}
            onChange={(event) => setBrowsing(event.target.checked)}
          />
          검색 켬 — 지금 검색하면 우리가 나오는가
        </label>
        <label className={styles.modeChoice}>
          <input
            type="checkbox"
            checked={searchOff && canTurnSearchOff}
            disabled={!canTurnSearchOff}
            onChange={(event) => setSearchOff(event.target.checked)}
          />
          검색 끔 — AI 가 학습한 것만으로 우리를 아는가
        </label>
        {!canTurnSearchOff && chosen !== undefined ? (
          <p className={styles.warning}>{chosen.searchOffNote}</p>
        ) : null}
      </fieldset>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="manual-repetitions">
          검색어당 반복 횟수
        </label>
        <input
          id="manual-repetitions"
          className={styles.number}
          type="number"
          min={1}
          max={20}
          value={repetitions}
          onChange={(event) => setRepetitions(Number(event.target.value))}
        />
        <p className={styles.hint}>
          AI 답변은 같은 질문에도 매번 달라집니다. {MIN_RUNS_FOR_EXPLORATION}회 미만이면
          비율을 내지 않습니다.
        </p>
      </div>

      <div className={styles.estimate}>
        <p style={{ margin: 0 }}>
          외부 AI 를 <strong>{estimate?.total_calls ?? calls}번</strong> 부릅니다.
        </p>
        {estimate !== null && estimate.amount_usd !== null ? (
          <p style={{ margin: 'var(--veo-space-2) 0 0' }}>
            예상 비용 <strong>약 ${estimate.amount_usd.toFixed(2)}</strong> — 같은 조건에서
            이미 잰 토큰으로 계산했습니다.
          </p>
        ) : (
          <div className={styles.estimateUnknown}>
            <p style={{ margin: 0 }}>
              <strong>금액은 아직 낼 수 없습니다.</strong> 0원이라는 뜻이 아니라 모른다는
              뜻입니다 — 금액은 단가 × 토큰인데, 이 조건으로 얼마나 긴 답이 오는지는 한 번
              재 봐야 압니다.
            </p>
            {(estimate?.remedies_ko ?? []).map((line) => (
              <p key={line} style={{ margin: 'var(--veo-space-2) 0 0' }}>
                {line}
              </p>
            ))}
          </div>
        )}
      </div>

      <Button type="submit" busy={busy}>
        {busy ? '시작하는 중…' : '이 검색어 재기'}
      </Button>
      <FormError message={error} />
    </form>
  );
}
