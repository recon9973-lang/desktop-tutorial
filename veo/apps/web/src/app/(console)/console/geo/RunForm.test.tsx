/**
 * 실행 폼의 검색 모드 칸.
 *
 * 화면을 눈으로 못 여는 자리라(콘솔은 로그인이 필요하다) 여기서 실제로 그려 보고
 * 확인한다. 지키는 것 셋 —
 *
 * 1. 켬·끔이 **둘 다 기본으로 켜져 있다.** 한쪽만 재고 "AI 답변에 나온다" 고 말할 수 없다.
 * 2. 호출 횟수가 **모드 수만큼** 곱해진다. 두 모드를 골랐는데 절반으로 보이면 안 된다.
 * 3. 검색을 끌 수 없는 엔진에서는 끔 칸이 잠기고 **이유가 함께 보인다.**
 *    목록에서 빼면 "이 엔진은 아예 못 쓴다" 로 읽힌다.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { RunForm, type RunnableEngine, type SelectablePromptSet } from './RunForm';

const PROMPT_SETS: SelectablePromptSet[] = [
  { id: 'set-1', label: '핵심 질문', promptCount: 5 },
];

const OPENAI: RunnableEngine = {
  engine: 'OPENAI',
  label: 'ChatGPT (OpenAI)',
  models: [{ id: 'gpt-5', citesSources: true }],
  supportsSearchOff: true,
  searchOffNote: '',
};

const PERPLEXITY: RunnableEngine = {
  engine: 'PERPLEXITY',
  label: 'Perplexity',
  models: [{ id: 'sonar', citesSources: true }],
  supportsSearchOff: false,
  searchOffNote: '이 엔진은 검색을 끌 수 없습니다. 켬 모드로만 측정합니다.',
};

function on(): HTMLInputElement {
  return screen.getByLabelText(/검색 켬/) as HTMLInputElement;
}
function off(): HTMLInputElement {
  return screen.getByLabelText(/검색 끔/) as HTMLInputElement;
}

describe('검색 모드 칸', () => {
  it('켬과 끔이 둘 다 기본으로 켜져 있다', () => {
    render(<RunForm promptSets={PROMPT_SETS} engines={[OPENAI]} />);

    expect(on().checked).toBe(true);
    expect(off().checked).toBe(true);
  });

  it('호출 횟수가 모드 수만큼 곱해진다', async () => {
    const user = userEvent.setup();
    render(<RunForm promptSets={PROMPT_SETS} engines={[OPENAI]} />);

    // 질문 5개 × 반복 5회 × 모드 2개
    expect(screen.getByText('50번')).toBeTruthy();
    expect(screen.getByText(/검색 켬·끔 각각/)).toBeTruthy();

    await user.click(off());
    // 모드 하나로 줄면 절반이다
    expect(screen.getByText('25번')).toBeTruthy();
  });

  it('한 모드만 남기면 다른 모드의 숫자가 없다고 말한다', async () => {
    const user = userEvent.setup();
    render(<RunForm promptSets={PROMPT_SETS} engines={[OPENAI]} />);

    expect(screen.queryByText(/다른 모드의 숫자는 없습니다/)).toBeNull();
    await user.click(off());
    expect(screen.getByText(/다른 모드의 숫자는 없습니다/)).toBeTruthy();
  });

  it('검색을 끌 수 없는 엔진은 끔 칸이 잠기고 이유가 보인다', () => {
    render(<RunForm promptSets={PROMPT_SETS} engines={[PERPLEXITY]} />);

    expect(off().disabled).toBe(true);
    expect(off().checked).toBe(false);
    expect(screen.getByText(PERPLEXITY.searchOffNote)).toBeTruthy();
    // 엔진 자체는 목록에 남는다 — 빼면 "못 쓰는 엔진" 으로 읽힌다.
    expect(screen.getByRole('option', { name: 'Perplexity' })).toBeTruthy();
  });

  it('둘 다 끄면 실행하지 않고 이유를 말한다', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    render(<RunForm promptSets={PROMPT_SETS} engines={[OPENAI]} />);

    await user.click(on());
    await user.click(off());
    await user.click(screen.getByRole('button', { name: '관측 시작' }));

    expect(screen.getByText(/적어도 하나는 재야 합니다/)).toBeTruthy();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
