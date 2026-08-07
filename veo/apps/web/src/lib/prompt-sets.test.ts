import { describe, expect, it } from 'vitest';

import {
  MIN_PROMPTS,
  previewBalance,
  splitPastedQuestions,
  type DraftPrompt,
} from './prompt-sets';

/**
 * 질문 집합의 균형 미리보기.
 *
 * 여기서 재는 것은 **화면이 저장 전에 무엇을 말해 주는가** 다. 판정 자체는 서버가 하고,
 * 서버가 거부하면 그 문장이 그대로 뜬다. 그래도 이 안내가 틀리면 사람은 통과할 줄 알고
 * 눌렀다가 거부당하고, 그다음부터는 안내를 안 읽는다.
 */

function prompt(overrides: Partial<DraftPrompt> = {}): DraftPrompt {
  return {
    key: Math.random().toString(36),
    text: '합성 질문',
    intent: 'BEST_OR_RECOMMENDED',
    funnel: 'RECOMMENDATION',
    subject: 'NON_BRAND',
    ...overrides,
  };
}

function balanced(): DraftPrompt[] {
  return [
    prompt({ intent: 'BEST_OR_RECOMMENDED' }),
    prompt({ intent: 'TRUST' }),
    prompt({ intent: 'COMPARISON' }),
    prompt({ intent: 'PRICE' }),
    prompt({ intent: 'LOCAL' }),
  ];
}

function messages(prompts: readonly DraftPrompt[]): string[] {
  return previewBalance(prompts)
    .filter((one) => !one.ok)
    .map((one) => one.message);
}

describe('저장 전 균형 미리보기', () => {
  it('고루 담긴 집합에는 보완할 것이 없다', () => {
    expect(messages(balanced())).toEqual([]);
  });

  it('질문이 적으면 몇 개가 필요한지 말한다', () => {
    const notes = messages([prompt()]);

    expect(notes.some((one) => one.includes(String(MIN_PROMPTS)))).toBe(true);
  });

  it("'신뢰·안전' 이 빠지면 짚는다", () => {
    // 부작용·후기 질문은 브랜드에 불리해서 제일 먼저 빠진다. 빼고 재면 노출률이
    // 실제보다 높게 나오고, 그것은 아무도 이의를 제기하지 않는 방향의 거짓이다.
    const without = balanced().map((one) =>
      one.intent === 'TRUST' ? { ...one, intent: 'PRICE' } : one,
    );

    expect(messages(without).some((one) => one.includes('신뢰·안전'))).toBe(true);
  });

  it("'비교' 가 빠지면 짚는다", () => {
    const without = balanced().map((one) =>
      one.intent === 'COMPARISON' ? { ...one, intent: 'PRICE' } : one,
    );

    expect(messages(without).some((one) => one.includes('비교'))).toBe(true);
  });

  it('한 의도가 절반을 넘으면 짚는다', () => {
    const lopsided = [
      ...balanced(),
      prompt({ intent: 'BEST_OR_RECOMMENDED' }),
      prompt({ intent: 'BEST_OR_RECOMMENDED' }),
      prompt({ intent: 'BEST_OR_RECOMMENDED' }),
      prompt({ intent: 'BEST_OR_RECOMMENDED' }),
      prompt({ intent: 'BEST_OR_RECOMMENDED' }),
    ];

    expect(messages(lopsided).some((one) => one.includes('%'))).toBe(true);
  });

  it('상호를 넣은 질문이 절반을 넘으면 짚는다', () => {
    // 상호가 든 질문은 언급이 거의 보장된다. 그것으로 채운 집합의 노출률은 노출이
    // 아니라 회상을 잰 값이다.
    const branded = balanced().map((one, index) =>
      index < 3 ? { ...one, subject: 'BRAND' } : one,
    );

    expect(messages(branded).some((one) => one.includes('회상'))).toBe(true);
  });

  it('빈 목록에도 답을 준다', () => {
    expect(() => previewBalance([])).not.toThrow();
    expect(messages([]).length).toBeGreaterThan(0);
  });
});

describe('붙여넣은 질문 나누기', () => {
  it('한 줄에 하나씩 나눈다', () => {
    expect(splitPastedQuestions('첫 질문\n둘째 질문')).toEqual(['첫 질문', '둘째 질문']);
  });

  it('번호와 글머리표를 떼어낸다', () => {
    // ERP 환자질문분석에서 복사해 오면 번호가 붙어 온다. 그것까지 AI 에게 물으면
    // 질문이 달라진다 — "1. 임플란트…" 와 "임플란트…" 는 다른 질문이다.
    expect(
      splitPastedQuestions('1. 첫 질문\n2) 둘째 질문\n- 셋째 질문\n· 넷째 질문'),
    ).toEqual(['첫 질문', '둘째 질문', '셋째 질문', '넷째 질문']);
  });

  it('빈 줄은 버린다', () => {
    expect(splitPastedQuestions('첫 질문\n\n   \n둘째 질문')).toEqual(['첫 질문', '둘째 질문']);
  });

  it('질문 안의 숫자는 건드리지 않는다', () => {
    expect(splitPastedQuestions('임플란트 2개 하면 얼마인가요?')).toEqual([
      '임플란트 2개 하면 얼마인가요?',
    ]);
  });
});
