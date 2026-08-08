'use client';

import { useRouter } from 'next/navigation';
import { useMemo, useState, type FormEvent } from 'react';
import { Button, FormError } from '@veo/ui';

import {
  FUNNELS,
  INTENTS,
  MIN_PROMPTS,
  SUBJECTS,
  exampleFor,
  previewBalance,
  splitPastedQuestions,
  type DraftPrompt,
} from '@/lib/prompt-sets';

import styles from './geo.module.css';

/**
 * 질문 집합을 만드는 칸 — 관측의 입구.
 *
 * 이 화면이 없어서 관측이 한 번도 돌지 못했다. 서버에는 만드는 길이 처음부터 있었고
 * (`POST /api/observations/prompt-sets`), 화면에서 부를 수가 없었을 뿐이다. 부를 수
 * 없는 기능은 없는 기능이다(0-E).
 *
 * 화면이 지키는 것 셋:
 *
 * **하나. 균형을 저장 전에 보여준다.** 서버는 균형이 안 맞으면 거부하는데, 거부를
 * 받고 나서야 알면 사람은 통과할 때까지 아무 값이나 바꿔 본다. 무엇이 모자란지 미리
 * 보이면 고칠 것을 고친다. 다만 **판정은 서버가 한다** — 여기 미리보기가 낡아도 잘못된
 * 집합이 저장되지는 않는다.
 *
 * **둘. 돈이 나가는 일이라고 적는다.** 질문 하나를 늘리면 매주·매달 반복해서 부른다.
 * 저장 버튼 옆에 월 금액이 없으면 아무도 그 사실을 떠올리지 않는다.
 *
 * **셋. 만든 근거를 같이 저장한다.** 질문을 어떻게 골랐는지(`generation_rule_ko`)가
 * 없으면, 6개월 뒤 이 집합이 왜 이 모양인지 아무도 설명할 수 없다.
 */

/** 한 질문을 한 번 재는 데 드는 값 — 반복 3회 · 검색 켬+끔 · 엔진 5개. */
const USD_PER_QUESTION_RUN = 0.61;

/** 화면에 원화를 적기 위한 환산. 정확한 환율이 아니라 자릿수 감을 주기 위한 값이다. */
const KRW_PER_USD = 1400;

const WEEKS_PER_MONTH = 4.345;

function newKey(): string {
  return crypto.randomUUID();
}

export function PromptSetForm({ projectId }: { readonly projectId: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState('핵심 질문');
  const [version, setVersion] = useState('1');
  const [rule, setRule] = useState('');
  const [pasted, setPasted] = useState('');
  const [rows, setRows] = useState<DraftPrompt[]>([]);
  /** 이 집합을 몇 주에 한 번 돌릴 계획인지. 저장되는 값이 아니라 금액 셈에만 쓴다. */
  const [perMonth, setPerMonth] = useState(WEEKS_PER_MONTH);

  const notes = useMemo(() => previewBalance(rows), [rows]);
  const blocking = notes.filter((one) => !one.ok);

  const monthlyUsd = rows.length * perMonth * USD_PER_QUESTION_RUN;

  function addPasted(): void {
    const lines = splitPastedQuestions(pasted);
    if (lines.length === 0) return;
    setRows((current) => [
      ...current,
      ...lines.map((text) => ({
        key: newKey(),
        text,
        // 기본값을 '추천·상호 없음' 으로 두는 이유: 병의원 질문의 대다수가 그것이고,
        // 무엇보다 **상호 없음**이 진짜 노출을 재는 쪽이다. 사람이 손대지 않아도
        // 부풀려지지 않는 방향이 기본값이어야 한다.
        intent: 'BEST_OR_RECOMMENDED',
        funnel: 'RECOMMENDATION',
        subject: 'NON_BRAND',
      })),
    ]);
    setPasted('');
  }

  /**
   * 모자란 의도의 예시 질문을 그대로 목록에 넣는다.
   *
   * 예시를 **그대로 쓰라는 뜻이 아니다.** `○○` 자리에 지역·시술을 넣어 고쳐 쓰라는
   * 것이고, 넣자마자 편집칸이 생기므로 고치는 것이 자연스러운 다음 동작이 된다.
   * 예시를 보여주기만 하면 사람은 그것을 손으로 옮겨 적다가 그만둔다.
   */
  function addExample(intent: string): void {
    setRows((current) => [
      ...current,
      {
        key: newKey(),
        text: exampleFor(intent),
        intent,
        funnel: intent === 'TRUST' ? 'RESEARCH' : 'COMPARISON',
        subject: 'NON_BRAND',
      },
    ]);
  }

  function update(key: string, field: 'text' | 'intent' | 'funnel' | 'subject', value: string) {
    setRows((current) =>
      current.map((one) => (one.key === key ? { ...one, [field]: value } : one)),
    );
  }

  function remove(key: string): void {
    setRows((current) => current.filter((one) => one.key !== key));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/prompt-set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId,
          name,
          version,
          generationRuleKo: rule,
          prompts: rows.map((one) => ({
            text: one.text,
            intent: one.intent,
            funnel: one.funnel,
            subject: one.subject,
          })),
        }),
      });
      const body: unknown = await response.json().catch(() => null);
      const record =
        typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
      if (!response.ok) {
        // 서버가 준 문장을 그대로 보인다. 균형 거부는 고칠 수 있는 안내다.
        setError(
          typeof record['message'] === 'string' ? record['message'] : '저장하지 못했습니다.',
        );
        return;
      }
      setRows([]);
      setRule('');
      setOpen(false);
      router.refresh();
    } catch {
      setError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주십시오.');
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button type="button" onClick={() => setOpen(true)}>
        질문 집합 만들기
      </Button>
    );
  }

  return (
    <form className={styles.runForm} onSubmit={submit} noValidate>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="set-name">
          집합 이름
        </label>
        <input
          id="set-name"
          className={styles.select}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <p className={styles.hint}>
          핵심 질문은 자주(주 1회) <strong>5~8개</strong>, 확장 질문은 드물게(월 1회){' '}
          <strong>20개 안팎</strong>을 권합니다. 집합을 나눠 두면 주기를 따로 줄 수 있습니다.
        </p>
        <p className={styles.hint}>
          <strong>한 집합에 최소 {MIN_PROMPTS}개가 필요합니다.</strong> 질문을 몇 개만 골라
          두면 그 몇 개가 곧 결론이 되기 때문입니다 — 잘 나오는 질문만 남기는 것이 숫자를
          위조하지 않고 결과를 바꾸는 가장 쉬운 방법입니다. 이 <strong>{MIN_PROMPTS}이라는
          숫자는 통계에서 나온 값이 아니라 2026-07-28에 우리가 정한 바닥값</strong>입니다
          (설계 기록 ADR 0015). 바꾸려면 그 문서를 고쳐야 합니다.
        </p>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="set-version">
          판
        </label>
        <input
          id="set-version"
          className={styles.number}
          value={version}
          onChange={(event) => setVersion(event.target.value)}
        />
        <p className={styles.hint}>
          질문을 바꾸면 판을 올립니다. <strong>같은 판끼리만 추이를 이을 수 있습니다</strong> —
          질문이 달라지면 그 뒤 숫자는 앞과 같은 것을 잰 값이 아닙니다.
        </p>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="set-paste">
          질문 붙여넣기 — 한 줄에 하나
        </label>
        <textarea
          id="set-paste"
          className={styles.select}
          rows={5}
          value={pasted}
          placeholder={'안산에 임플란트 잘하는 치과 알려줘\n임플란트 수술 후 붓기는 며칠 가나요?'}
          onChange={(event) => setPasted(event.target.value)}
        />
        <p className={styles.hint}>
          ERP 의 <strong>환자 질문 분석</strong>에서 그대로 복사해 오시면 됩니다. 번호나
          글머리표는 자동으로 떼어냅니다. <strong>상호를 넣지 않은 질문</strong>이 진짜
          노출을 잽니다 — &ldquo;○○의원 어때?&rdquo;는 언급이 거의 보장됩니다.
        </p>
        <Button type="button" onClick={addPasted}>
          목록에 추가
        </Button>
      </div>

      {/*
        분류 이름만 보여 주고 채우라고 하면, 채우는 사람은 자기가 이미 쓴 질문을 아무
        칸에나 넣는다. 그러면 균형은 통과하는데 실제로 잰 것은 한 종류뿐이다.
        일곱 가지가 각각 어떻게 생긴 질문인지 먼저 보인다(사장님 지적 2026-08-08).
      */}
      <section className={styles.balance} aria-label="의도별 질문 예시">
        <h3 className={styles.balanceTitle}>어떤 질문을 넣나 — 일곱 가지</h3>
        <ul className={styles.exampleList}>
          {INTENTS.map((item) => (
            <li key={item.id}>
              <b>{item.label}</b> <span className={styles.hint}>{item.hint}</span>
              <br />
              {item.examples[0]}
              <Button type="button" onClick={() => addExample(item.id)}>
                넣기
              </Button>
            </li>
          ))}
        </ul>
        <p className={styles.hint}>
          <code>○○</code> 자리에 지역이나 시술 이름을 넣어 고쳐 쓰십시오. 넣으면 바로
          편집할 수 있습니다. <strong>&lsquo;신뢰·안전&rsquo;과 &lsquo;비교&rsquo;는 반드시
          있어야 합니다</strong> — 브랜드에 불리해서 제일 먼저 빠지는 질문이고, 빼고 재면
          노출률이 실제보다 높게 나옵니다.
        </p>
      </section>

      {rows.length > 0 ? (
        <ul className={styles.promptRows}>
          {rows.map((one) => (
            <li key={one.key} className={styles.promptRow}>
              <input
                aria-label="질문"
                className={styles.select}
                value={one.text}
                onChange={(event) => update(one.key, 'text', event.target.value)}
              />
              <select
                aria-label="검색 의도"
                className={styles.select}
                value={one.intent}
                onChange={(event) => update(one.key, 'intent', event.target.value)}
              >
                {INTENTS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label} — {item.hint}
                  </option>
                ))}
              </select>
              <select
                aria-label="퍼널 단계"
                className={styles.select}
                value={one.funnel}
                onChange={(event) => update(one.key, 'funnel', event.target.value)}
              >
                {FUNNELS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="질문 대상"
                className={styles.select}
                value={one.subject}
                onChange={(event) => update(one.key, 'subject', event.target.value)}
              >
                {SUBJECTS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
              <Button type="button" onClick={() => remove(one.key)}>
                빼기
              </Button>
            </li>
          ))}
        </ul>
      ) : null}

      <section className={styles.balance} aria-label="집합 균형 미리보기">
        <h3 className={styles.balanceTitle}>저장 전 확인</h3>
        <ul>
          {notes.map((note) => (
            <li key={note.message} className={note.ok ? styles.balanceOk : styles.balanceBad}>
              <span>
                {note.ok ? '확인' : '보완'} · {note.message}
              </span>
              {/* 지적만 하고 고칠 방법을 안 주면, 읽는 사람은 자기가 이미 쓴 질문의
                  분류만 바꾼다 — 균형은 통과하는데 잰 것은 그대로다. */}
              {note.fix === undefined ? null : (
                <span className={styles.balanceFix}>
                  예: <strong>{note.fix.example}</strong>
                  <Button type="button" onClick={() => addExample(note.fix!.intent)}>
                    이런 질문 넣기
                  </Button>
                </span>
              )}
            </li>
          ))}
        </ul>
        <p className={styles.hint}>
          최종 판정은 저장할 때 서버가 합니다. 여기 목록은 미리 보여주는 것입니다.
        </p>
      </section>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="set-cadence">
          측정 주기 — 한 달에 몇 번
        </label>
        <input
          id="set-cadence"
          className={styles.number}
          type="number"
          min={1}
          max={31}
          step={1}
          value={Math.round(perMonth)}
          onChange={(event) => setPerMonth(Math.max(1, Number(event.target.value)))}
        />
        <p className={styles.hint}>
          주 1회면 약 4번, 월 1회면 1번입니다. <strong>이 값은 저장되지 않습니다</strong> —
          아래 금액을 셈하는 데만 씁니다.
        </p>
      </div>

      <p className={styles.cost}>
        질문 <strong>{rows.length}개</strong>를 한 달에 <strong>{Math.round(perMonth)}번</strong>{' '}
        재면 약 <strong>${monthlyUsd.toFixed(2)}</strong> (
        {Math.round(monthlyUsd * KRW_PER_USD).toLocaleString('ko-KR')}원) 입니다. 반복 3회 ·
        검색 켬/끔 · 엔진 5개 기준이며, 제공자 공식 단가와 실측 토큰으로 셈한{' '}
        <strong>추정</strong>입니다.
      </p>

      <Button type="submit" busy={busy} disabled={rows.length === 0}>
        {busy ? '저장하는 중…' : '질문 집합 저장'}
      </Button>
      {blocking.length > 0 ? (
        <p className={styles.warning}>
          보완할 것이 {blocking.length}건 남아 있습니다. 그대로 저장하면 서버가 거부할 수
          있습니다.
        </p>
      ) : null}
      <FormError message={error} />

      <div className={styles.field}>
        <label className={styles.label} htmlFor="set-rule">
          이 질문들을 어떻게 골랐는지
        </label>
        <textarea
          id="set-rule"
          className={styles.select}
          rows={3}
          value={rule}
          onChange={(event) => setRule(event.target.value)}
          placeholder="예: ERP 환자질문분석 2026-08 스냅샷에서 지역 의존 질문 상위 20개를 뽑고, 진료과가 겹치는 것을 하나로 합쳤습니다."
        />
        <p className={styles.hint}>
          6개월 뒤 이 집합이 왜 이 모양인지 설명할 수 있는 유일한 기록입니다. 무엇을 왜
          뺐는지도 여기 적어 주십시오.
        </p>
      </div>
    </form>
  );
}
