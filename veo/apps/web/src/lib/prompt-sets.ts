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

export const INTENTS = [
  { id: 'DEFINITION', label: '정의', hint: '이게 뭔가요' },
  { id: 'HOW_TO', label: '방법', hint: '어떻게 하나요' },
  { id: 'BEST_OR_RECOMMENDED', label: '추천', hint: '어디가 잘하나요' },
  { id: 'COMPARISON', label: '비교', hint: 'A와 B 중 어느 쪽' },
  { id: 'PRICE', label: '가격', hint: '얼마인가요' },
  { id: 'LOCAL', label: '지역', hint: '○○에 있는 곳' },
  { id: 'TRUST', label: '신뢰·안전', hint: '부작용·후기·안전' },
] as const;

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

/** 이보다 적으면 의도를 고루 담을 수 없어 비율이 뜻을 잃는다. */
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
    notes.push({
      ok: intents.has(required),
      message: intents.has(required)
        ? `'${label}' 의도가 들어 있습니다`
        : `'${label}' 의도가 없습니다 — 브랜드에 불리해서 제일 먼저 빠지는 질문입니다. 빼고 재면 노출률이 실제보다 높게 나옵니다`,
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
