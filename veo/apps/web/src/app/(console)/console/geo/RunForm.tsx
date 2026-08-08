'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState, type FormEvent } from 'react';
import { Button, FormError } from '@veo/ui';

import { MIN_RUNS_FOR_COMPARISON, MIN_RUNS_FOR_EXPLORATION } from '@/lib/sampling';

import styles from './geo.module.css';

export interface RunnableEngine {
  readonly engine: string;
  readonly label: string;
  readonly models: readonly { readonly id: string; readonly citesSources: boolean }[];
  /** 검색을 끄고 물어볼 수 있는 엔진인가. 서버가 알려준다 — 화면이 알아맞히지 않는다. */
  readonly supportsSearchOff: boolean;
  /** 끌 수 없을 때 서버가 보내는 설명. 그대로 보여 준다. */
  readonly searchOffNote: string;
}

export interface SelectablePromptSet {
  readonly id: string;
  readonly label: string;
  readonly promptCount: number;
}

/**
 * 관측을 시작하는 칸.
 *
 * 두 가지를 화면에서 못 숨긴다.
 *
 * **인용을 돌려주지 않는 모델이 있다.** 실측으로 `gpt-5`·`gpt-4o` 는 출처를 돌려주고
 * `gpt-4.1`·`gpt-4o-mini` 는 돌려주지 않는다. 후자로 재면 인용률은 0%가 아니라
 * **측정 불가**가 되는데, 고른 뒤에 알면 이미 돈이 나간 뒤다. 그래서 고르는 자리에
 * 적는다.
 *
 * **반복 횟수는 표본 크기다.** 3회 미만이면 비율을 아예 내지 않고, 경쟁사 비교 보고에
 * 실으려면 5회가 필요하다. 이 숫자를 "성능 옵션"처럼 두면 사람은 늘 낮은 쪽을 고른다.
 *
 * **검색 켬과 끔은 서로 다른 질문이다.** 켬은 "지금 검색하면 우리가 나오는가", 끔은
 * "AI 가 학습한 것만으로 우리를 아는가" 다. 둘은 서로를 대신하지 못하므로 한쪽만 재고
 * "AI 답변에 나온다" 고 말할 수 없다. 그래서 둘 다 켜는 것이 기본값이고, 호출 수가
 * 두 배가 된다는 사실을 아래 비용 줄에 함께 적는다.
 */
export function RunForm({
  promptSets,
  engines,
}: {
  readonly promptSets: readonly SelectablePromptSet[];
  readonly engines: readonly RunnableEngine[];
}) {
  const router = useRouter();
  const [promptSetId, setPromptSetId] = useState(promptSets[0]?.id ?? '');
  const [engine, setEngine] = useState(engines[0]?.engine ?? '');
  const [model, setModel] = useState(engines[0]?.models[0]?.id ?? '');
  const [repetitions, setRepetitions] = useState(MIN_RUNS_FOR_COMPARISON);
  const [browsing, setBrowsing] = useState(true);
  const [searchOff, setSearchOff] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 같은 화면에서 두 번 눌러도 두 번 실행되지 않게 한다. 관측은 돈이 나가는 일이다.
  const attemptKey = useRef<string>(crypto.randomUUID());

  const chosen = engines.find((one) => one.engine === engine);
  const chosenModel = chosen?.models.find((one) => one.id === model);
  const models = chosen?.models ?? [];
  const promptCount = promptSets.find((one) => one.id === promptSetId)?.promptCount ?? 0;

  // 끌 수 없는 엔진에서는 끔이 고른 것으로 남아 있어도 보내지 않는다. 보내면 서버가
  // 거절하고, 그 전에 화면이 "끔도 잰다" 고 말한 셈이 된다.
  const canTurnSearchOff = chosen?.supportsSearchOff ?? true;
  const modes = [
    ...(browsing ? ['BROWSING'] : []),
    ...(searchOff && canTurnSearchOff ? ['NO_BROWSING'] : []),
  ];

  function pickEngine(next: string): void {
    setEngine(next);
    const first = engines.find((one) => one.engine === next)?.models[0]?.id ?? '';
    setModel(first);
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    if (modes.length === 0) {
      setError('검색 켬·끔 중 적어도 하나는 재야 합니다.');
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/observation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          promptSetId,
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
          typeof record['message'] === 'string' ? record['message'] : '관측을 시작하지 못했습니다.',
        );
        return;
      }

      const job =
        typeof record['job'] === 'object' && record['job'] !== null
          ? (record['job'] as { id?: unknown })
          : {};
      if (typeof job.id === 'string') {
        // 다음 실행은 새 열쇠로. 같은 열쇠를 남겨 두면 조건을 바꿔 다시 눌러도
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

  if (promptSets.length === 0 || engines.length === 0) return null;

  // 모드마다 따로 부른다. 모드 수를 빼고 세면 두 모드를 골라도 절반으로 보인다.
  const calls = promptCount * repetitions * modes.length;

  return (
    <form className={styles.runForm} onSubmit={submit} noValidate>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="prompt-set">
          질문 집합
        </label>
        <select
          id="prompt-set"
          className={styles.select}
          value={promptSetId}
          onChange={(event) => setPromptSetId(event.target.value)}
        >
          {promptSets.map((set) => (
            <option key={set.id} value={set.id}>
              {set.label} · 질문 {set.promptCount}개
            </option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="engine">
          AI 엔진
        </label>
        <select
          id="engine"
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
        <label className={styles.label} htmlFor="model">
          모델
        </label>
        <select
          id="model"
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
        {chosenModel !== undefined && !chosenModel.citesSources ? (
          <p className={styles.warning}>
            이 모델은 어느 출처를 썼는지 알려주지 않습니다. 그래서 <strong>인용률이 0%가
            아니라 &lsquo;측정 불가&rsquo;</strong>로 남습니다. 인용을 재려면 출처를 돌려주는
            모델을 고르십시오. 언급률은 이 모델로도 잴 수 있습니다.
          </p>
        ) : null}
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
        {modes.length === 1 ? (
          <p className={styles.hint}>
            한 모드만 재면 <strong>다른 모드의 숫자는 없습니다.</strong> 검색을 켰을 때
            나오는 것과 학습만으로 아는 것은 서로 다른 사실이라, 한쪽으로 다른 쪽을 말할
            수 없습니다.
          </p>
        ) : null}
      </fieldset>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="repetitions">
          질문당 반복 횟수
        </label>
        <input
          id="repetitions"
          className={styles.number}
          type="number"
          min={1}
          max={20}
          value={repetitions}
          onChange={(event) => setRepetitions(Number(event.target.value))}
        />
        <p className={styles.hint}>
          AI 답변은 같은 질문에도 매번 달라집니다. <strong>{MIN_RUNS_FOR_EXPLORATION}회
          미만이면 비율을 내지 않고</strong>, 경쟁사 비교 보고에 실으려면{' '}
          {MIN_RUNS_FOR_COMPARISON}회 이상이 필요합니다.
        </p>
        {repetitions < MIN_RUNS_FOR_EXPLORATION ? (
          <p className={styles.warning}>
            {repetitions}회로는 노출률을 계산하지 않습니다. 실행은 되지만 결과에 퍼센트가
            나오지 않습니다.
          </p>
        ) : repetitions < MIN_RUNS_FOR_COMPARISON ? (
          <p className={styles.warning}>
            {repetitions}회는 방향만 볼 수 있는 표본입니다. 경쟁사와 나란히 놓을 수는
            없습니다.
          </p>
        ) : null}
      </div>

      <p className={styles.cost}>
        이 조건이면 AI 를 <strong>{calls}번</strong> 부릅니다
        {modes.length === 2 ? ' (검색 켬·끔 각각)' : ''}. 실행은 몇 분 걸릴 수 있고,
        시작하면 이 화면을 닫아도 계속 돕니다.
      </p>

      <Button type="submit" busy={busy}>
        {busy ? '시작하는 중…' : '관측 시작'}
      </Button>
      <FormError message={error} />
    </form>
  );
}
