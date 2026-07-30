import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * 스타일에 대고 재는 몇 가지.
 *
 * jsdom 은 CSS 모듈을 적용하지 않으므로 컴포넌트 테스트로는 "얼마나 크게 그려지는가" 를
 * 잴 수 없다. 그런데 이 화면에서 크기는 장식이 아니라 **뜻**이다 — 건너뛴 실행을 작게
 * 그리면 부분 측정이 완전한 측정처럼 읽힌다. 그래서 선언 자체를 읽어서 고정한다.
 */

const CSS = readFileSync(join(__dirname, 'geo.module.css'), 'utf8');

/**
 * `@media` 는 중괄호가 한 겹 더 있어 단순한 규칙 훑기를 망가뜨린다 — 감싼 것을 벗겨
 * 평평하게 만든 뒤에 읽는다. (미디어 질의 자체는 원본 `CSS` 에 대고 따로 확인한다.)
 */
const FLAT = CSS.replace(/\/\*[\s\S]*?\*\//g, '').replace(
  /@media[^{]*\{([\s\S]*?)\n\}/g,
  '$1',
);

const RULES = [...FLAT.matchAll(/([^{}]+)\{([^{}]*)\}/g)];

/**
 * 이 선택자가 실제로 받는 선언 전부.
 *
 * 규칙을 하나만 찾으면 안 된다 — `.rateCard, .rateCardUnmeasured { ... }` 처럼 공유하는
 * 규칙과 각자의 규칙이 함께 있고, 요소는 그 둘을 다 받는다. 첫 번째만 보면 실제로
 * 적용되는 것과 다른 것을 재게 된다.
 */
function block(selector: string): string {
  const declarations = RULES
    .filter(([, selectors = '']) =>
      selectors
        .split(',')
        .map((one) => one.trim())
        .includes(selector),
    )
    .map(([, , body = '']) => body);

  if (declarations.length === 0) throw new Error(`${selector} 규칙을 찾지 못했습니다`);
  return declarations.join('\n');
}

/** 이 선택자 하나만 있는 규칙. 공유 규칙에서 받은 것 위에 무엇을 덮는지 본다. */
function soleRule(selector: string): string {
  const own = RULES.find(([, selectors = '']) => selectors.trim() === selector);
  if (own === undefined) throw new Error(`${selector} 단독 규칙을 찾지 못했습니다`);
  return own[2] ?? '';
}

describe('건너뛴 실행의 크기', () => {
  it('평범한 수치와 같은 규칙에서 크기를 받는다', () => {
    // 한 규칙에 함께 선언돼 있어야 한다. 따로 두면 언젠가 한쪽만 작아진다.
    expect(CSS).toMatch(/\.countValue,\s*\n?\.countValueAlarming\s*\{/);
  });

  it('경고용 변형이 스스로 크기를 다시 정하지 않는다', () => {
    // 공유 규칙에서 받은 크기를 자기 규칙에서 덮어쓰면 그 순간 작아질 수 있다.
    const own = soleRule('.countValueAlarming');
    expect(own).toMatch(/color:/);
    expect(own).not.toMatch(/font-size:/);
  });
});

describe('잴 수 없었던 값', () => {
  it('색 말고도 다른 신호를 준다', () => {
    // 색만으로 상태를 전달하지 않는다 — 색각 이상과 흑백 인쇄에서 사라진다.
    expect(block('.rateCardUnmeasured')).toMatch(/border:\s*1px dashed/);
  });

  it('값이 있는 카드보다 작은 글자를 쓴다 — 큰 자리에 앉으면 숫자로 읽힌다', () => {
    expect(block('.rateValue')).toMatch(/--veo-font-size-600/);
    expect(block('.rateValueUnmeasured')).toMatch(/--veo-font-size-300/);
  });
});

describe('움직임', () => {
  it('진행률 막대는 모션을 줄인 환경에서 움직이지 않는다', () => {
    expect(CSS).toMatch(/prefers-reduced-motion: reduce/);
  });
});
