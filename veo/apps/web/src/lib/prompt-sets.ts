/**
 * 질문 집합을 만들 때 화면이 미리 보여주는 균형 — **판정은 서버가 한다.**
 *
 * 아래 값들은 서버(`observations/prompts.py`)가 쓰는 규칙을 화면에서 **미리** 보여주기
 * 위한 사본이다. 사본이 두 벌이면 언젠가 한쪽만 바뀐다(0-D). 그래서 이 파일은 판정을
 * 하지 않는다 — 저장은 언제나 서버가 받고, 서버가 거부하면 그 이유가 그대로 화면에
 * 뜬다. 여기 값이 낡아도 잘못된 집합이 저장되는 일은 없고, 화면 안내만 늦어진다.
 *
 * 왜 균형을 재는가. 브랜드에 **불리한 질문을 빼고** 만든 집합으로 재면 노출률이
 * 실제보다 높게 나온다. 그것은 고객에게 유리한 방향의 거짓이라 아무도 이의를 제기하지
 * 않고, 그래서 더 오래 살아남는다. 서버 주석의 표현이 정확하다 —
 * "이 둘을 빼는 것이 브랜드를 띄우는 가장 싼 방법이다."
 */

/**
 * 검색 의도 일곱 가지와 **그 의도의 질문이 실제로 어떻게 생겼는지.**
 *
 * 예시가 없으면 "'비교' 의도가 없습니다" 는 무슨 말인지 알 수 없는 지적이 된다.
 * 사장님 지적(2026-08-08): "비교 신뢰 안전 추천 이런게 없으니까 넣으라는거야?
 * 어려워 예시를 미리 보여 주면 좋겠어." 정확한 지적이다 — 분류 이름만 보여 주고
 * 채우라고 하면, 채우는 사람은 자기가 이미 쓴 질문을 아무 칸에나 넣게 된다.
 *
 * 예시는 병의원 현장 말투로 쓴다. `○○` 는 지역이나 시술 이름이 들어갈 자리다.
 */
export const INTENTS = [
  {
    id: 'DEFINITION',
    label: '정의',
    hint: '이게 뭔가요',
    examples: ['도수치료는 어떤 치료인가요?', '임플란트는 어떤 시술인가요?'],
  },
  {
    id: 'HOW_TO',
    label: '방법',
    hint: '어떻게 하나요',
    examples: ['교통사고 후 한방 치료는 어떻게 받나요?', '임플란트 후 관리는 어떻게 하나요?'],
  },
  {
    id: 'BEST_OR_RECOMMENDED',
    label: '추천',
    hint: '어디가 잘하나요',
    examples: ['○○ 교통사고 한의원 추천해줘', '○○에 임플란트 잘하는 치과 알려줘'],
  },
  {
    id: 'COMPARISON',
    label: '비교',
    hint: 'A와 B 중 어느 쪽',
    examples: [
      '교통사고 치료는 한의원과 정형외과 중 어디가 나은가요?',
      '다이어트 한약과 식욕억제제 중 뭐가 나은가요?',
    ],
  },
  {
    id: 'PRICE',
    label: '가격',
    hint: '얼마인가요',
    examples: ['○○ 다이어트 한약 가격이 얼마인가요?', '교통사고 한방 치료는 보험이 되나요?'],
  },
  {
    id: 'LOCAL',
    label: '지역',
    hint: '○○에 있는 곳',
    examples: ['○○역 근처에 일요일 진료하는 한의원 있나요?', '○○에서 야간 진료되는 곳 알려줘'],
  },
  {
    id: 'TRUST',
    label: '신뢰·안전',
    hint: '부작용·후기·안전',
    examples: [
      '다이어트 한약 부작용은 어떤 게 있나요?',
      '불면증 한약 오래 먹어도 괜찮나요?',
    ],
  },
] as const;

/** 의도 하나의 예시 질문 첫 줄. 없으면 빈 문자열. */
export function exampleFor(intent: string): string {
  return INTENTS.find((one) => one.id === intent)?.examples[0] ?? '';
}

export const FUNNELS = [
  { id: 'PROBLEM_AWARE', label: '문제 인식' },
  { id: 'RESEARCH', label: '알아보는 중' },
  { id: 'COMPARISON', label: '비교 중' },
  { id: 'RECOMMENDATION', label: '추천 요청' },
  { id: 'PURCHASE_OR_VISIT', label: '방문·예약 직전' },
  { id: 'AFTERCARE', label: '사후 관리' },
] as const;

export const SUBJECTS = [
  { id: 'NON_BRAND', label: '상호 없음', hint: '기본. 이것이 진짜 노출을 잰다' },
  { id: 'BRAND', label: '자사 상호', hint: '언급이 거의 보장된다 — 노출이 아니라 회상' },
  { id: 'COMPETITOR', label: '경쟁사 상호' },
  { id: 'CATEGORY', label: '업종·분류' },
] as const;

/**
 * 아래 넷은 전부 **[설계 판단]** 이다 — 통계나 외부 연구에서 나온 값이 아니라
 * 2026-07-28 에 우리가 정했다. 근거 문서는 `docs/adr/0015-prompt-sets-are-audited-artefacts.md`.
 *
 * ADR 이 대는 이유는 조작 방지다:
 *
 * > 경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. **질문만 고르면 된다.**
 * > 고객이 잘 나오는 "서초 임플란트 잘하는 곳"은 묻고, 잘 안 나오는 "임플란트 부작용"은
 * > 뺀다. 이후 모든 계산은 산술적으로 완벽하고 결론은 거짓이다.
 *
 * 그 논리는 타당하다. 다만 **왜 5개이고 왜 50%인지는 문서에 근거가 없다** — 4개나
 * 40%가 아니어야 할 이유가 적혀 있지 않다. 바꾸려면 ADR 을 고쳐야 하고, 고칠 때는
 * 그 숫자여야 하는 이유를 대야 한다. 화면 문구도 이 사실을 숨기지 않는다.
 */

/** 최소 질문 수. 이보다 적으면 그 몇 개가 곧 결론이 된다. */
export const MIN_PROMPTS = 5;

/** 한 의도가 집합의 절반을 넘으면 그 집합은 그 의도 하나를 잰 것이다. */
export const MAX_SINGLE_INTENT_SHARE = 0.5;

/** 상호를 넣은 질문은 언급이 거의 보장된다. 절반을 넘기면 노출률이 부풀려진다. */
export const MAX_BRAND_SUBJECT_SHARE = 0.5;

/** 빼면 안 되는 의도. 브랜드에 불리해서 제일 먼저 빠지는 둘이다. */
export const REQUIRED_INTENTS = ['TRUST', 'COMPARISON'] as const;

export interface DraftPrompt {
  readonly key: string;
  readonly text: string;
  readonly intent: string;
  readonly funnel: string;
  readonly subject: string;
}

export interface BalanceNote {
  readonly ok: boolean;
  readonly message: string;
  /**
   * 이 지적을 **한 번에 고칠 수 있는** 예시 질문. 없으면 사람이 판단해야 하는 지적이다.
   *
   * 지적만 하고 고칠 방법을 안 주면, 읽는 사람은 무엇을 넣어야 하는지 모르는 채로
   * 자기가 이미 쓴 질문의 분류만 바꾸게 된다 — 그러면 균형은 통과하는데 실제로 잰
   * 것은 그대로다. 숫자만 맞추고 뜻은 안 맞추는 것이 가장 나쁜 결과다.
   */
  readonly fix?: { readonly intent: string; readonly example: string };
}

/**
 * 지금 목록이 서버 관문을 통과할지 **미리** 보여준다.
 *
 * 통과 여부를 여기서 확정하지 않는다. 저장은 서버가 받고, 서버가 거부하면 그 문장이
 * 그대로 화면에 뜬다. 이 함수는 저장 버튼을 누르기 전에 무엇이 모자란지 알려 주는
 * 안내일 뿐이다.
 */
export function previewBalance(prompts: readonly DraftPrompt[]): BalanceNote[] {
  const notes: BalanceNote[] = [];
  const total = prompts.length;

  notes.push({
    ok: total >= MIN_PROMPTS,
    message:
      total >= MIN_PROMPTS
        ? `질문 ${total}개 — 최소 ${MIN_PROMPTS}개를 채웠습니다`
        : `질문이 ${total}개입니다. 최소 ${MIN_PROMPTS}개가 필요합니다`,
  });

  if (total === 0) return notes;

  const intents = new Set(prompts.map((one) => one.intent));
  for (const required of REQUIRED_INTENTS) {
    const label = INTENTS.find((one) => one.id === required)?.label ?? required;
    const has = intents.has(required);
    notes.push({
      ok: has,
      message: has
        ? `'${label}' 의도가 들어 있습니다`
        : `'${label}' 질문이 없습니다 — 브랜드에 불리해서 제일 먼저 빠지는 질문입니다. 빼고 재면 노출률이 실제보다 높게 나옵니다`,
      ...(has ? {} : { fix: { intent: required, example: exampleFor(required) } }),
    });
  }

  const counts = new Map<string, number>();
  for (const one of prompts) counts.set(one.intent, (counts.get(one.intent) ?? 0) + 1);
  let worst = '';
  let worstCount = 0;
  for (const [intent, count] of counts) {
    if (count > worstCount) {
      worst = intent;
      worstCount = count;
    }
  }
  const share = worstCount / total;
  const worstLabel = INTENTS.find((one) => one.id === worst)?.label ?? worst;
  notes.push({
    ok: share <= MAX_SINGLE_INTENT_SHARE,
    message:
      share <= MAX_SINGLE_INTENT_SHARE
        ? `가장 많은 의도가 '${worstLabel}' ${worstCount}개 (${Math.round(share * 100)}%)`
        : `'${worstLabel}' 이 ${Math.round(share * 100)}% 입니다. 절반을 넘으면 그 의도 하나를 잰 것이 됩니다`,
  });

  const branded = prompts.filter((one) => one.subject === 'BRAND').length;
  const brandShare = branded / total;
  notes.push({
    ok: brandShare <= MAX_BRAND_SUBJECT_SHARE,
    message:
      brandShare <= MAX_BRAND_SUBJECT_SHARE
        ? `상호를 넣은 질문 ${branded}개 (${Math.round(brandShare * 100)}%)`
        : `상호를 넣은 질문이 ${Math.round(brandShare * 100)}% 입니다. 그런 질문은 언급이 거의 보장되어 노출이 아니라 회상을 잽니다`,
  });

  return notes;
}

/**
 * 붙여넣은 여러 줄을 질문 목록으로.
 *
 * ERP 의 환자 질문 분석에서 그대로 복사해 오는 것을 전제로 한다. 번호(`1.`)나 글머리표
 * (`-`, `·`)가 앞에 붙어 오므로 떼어 낸다 — 그것까지 AI 에게 물으면 질문이 달라진다.
 */
export function splitPastedQuestions(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.replace(/^\s*(?:\d+[.)]|[-*·•])\s*/, '').trim())
    .filter((line) => line !== '');
}
