/**
 * 수동 측정 칸.
 *
 * 화면을 눈으로 못 여는 자리라(콘솔은 로그인이 필요하다) 여기서 실제로 그려 보고
 * 확인한다. 지키는 것 넷 —
 *
 * 1. **"추이에 안 올라간다" 가 눈에 보인다.** 숨기면 이걸 재고 그래프가 왜 안 움직이는지
 *    묻게 된다. 서버도 섞는 것을 거부하지만 거부는 화면에 안 보인다.
 * 2. 검색어를 **줄 단위로** 읽고 빈 줄·중복을 뺀다. 세는 숫자가 실제로 보낼 개수와
 *    다르면 예상 호출 수가 거짓이 된다.
 * 3. 호출 수가 **검색어 × 반복 × 모드 수**로 곱해진다.
 * 4. 금액을 모를 때 **0원이 아니라 "모른다"** 라고 적는다.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { ManualRunForm, readQuestions, type SelectableProject } from './ManualRunForm';
import type { RunnableEngine } from './RunForm';

const PROJECTS: SelectableProject[] = [{ id: 'p-1', label: '베놈 · 기본' }];

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

function questionBox(): HTMLTextAreaElement {
  // `검색어당 반복 횟수` 라벨과 겹치므로 앞머리를 고정한다.
  return screen.getByLabelText(/^검색어 —/) as HTMLTextAreaElement;
}

describe('검색어 읽기', () => {
  it('빈 줄을 버린다', () => {
    expect(readQuestions('가\n\n  \n나')).toEqual(['가', '나']);
  });

  it('같은 검색어를 두 번 세지 않는다 — 두 번 세면 예상 호출 수가 거짓이 된다', () => {
    expect(readQuestions('강남 임플란트\n강남 임플란트')).toEqual(['강남 임플란트']);
  });

  it('앞뒤 공백을 떼고 비교한다', () => {
    expect(readQuestions('  강남 임플란트  \n강남 임플란트')).toEqual(['강남 임플란트']);
  });

  it('아무것도 없으면 빈 목록이다', () => {
    expect(readQuestions('   \n\n')).toEqual([]);
  });
});

describe('수동 측정 칸', () => {
  it('추이에 올라가지 않는다는 것을 먼저 말한다', () => {
    render(<ManualRunForm projects={PROJECTS} engines={[OPENAI]} />);
    expect(screen.getByText(/추이에 올라가지 않습니다/)).toBeInTheDocument();
  });

  it('검색어 개수를 실제로 보낼 개수로 센다', async () => {
    const user = userEvent.setup();
    render(<ManualRunForm projects={PROJECTS} engines={[OPENAI]} />);

    await user.type(questionBox(), '가\n나\n가');

    expect(screen.getByText(/지금 2개입니다/)).toBeInTheDocument();
  });

  it('호출 수는 검색어 × 반복 × 모드 수다', async () => {
    const user = userEvent.setup();
    render(<ManualRunForm projects={PROJECTS} engines={[OPENAI]} />);

    await user.type(questionBox(), '가\n나');
    // 기본은 검색 켬 하나 · 반복 3회 → 2 × 3 × 1 = 6
    expect(screen.getByText(/6번/)).toBeInTheDocument();

    await user.click(screen.getByLabelText(/검색 끔/));
    // 모드가 둘이 되면 2 × 3 × 2 = 12
    expect(screen.getByText(/12번/)).toBeInTheDocument();
  });

  it('금액을 모를 때 0원이 아니라 모른다고 적는다', async () => {
    const user = userEvent.setup();
    render(<ManualRunForm projects={PROJECTS} engines={[OPENAI]} />);

    await user.type(questionBox(), '가');

    expect(screen.getByText(/금액은 아직 낼 수 없습니다/)).toBeInTheDocument();
    expect(screen.getByText(/0원이라는 뜻이 아니라/)).toBeInTheDocument();
  });

  it('검색을 끌 수 없는 엔진에서는 끔 칸이 잠기고 이유가 보인다', () => {
    render(<ManualRunForm projects={PROJECTS} engines={[PERPLEXITY]} />);

    expect(screen.getByLabelText(/검색 끔/)).toBeDisabled();
    expect(screen.getByText(/검색을 끌 수 없습니다/)).toBeInTheDocument();
  });

  it('고를 프로젝트가 없으면 아예 그리지 않는다', () => {
    const { container } = render(<ManualRunForm projects={[]} engines={[OPENAI]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
