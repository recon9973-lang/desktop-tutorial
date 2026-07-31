import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { Brand } from '@/lib/brands';

import { BrandCard } from './BrandCard';

/**
 * 이 카드의 목적은 등록된 값을 나열하는 것이 아니라 **비어 있는 칸을 눈에 띄게 하는
 * 것**이다.
 *
 * 비어 있으면 그 브랜드의 언급이 전부 검수 대기로 넘어가는데, 사용자는 관측을 돌려
 * 돈을 쓴 뒤에야 그 사실을 알게 된다. 그때는 이미 늦다.
 */

function brand(over: Partial<Brand> = {}): Brand {
  return {
    id: 'b-1',
    entity_key: 'ondam',
    display_name: '온담한의원',
    is_own_brand: true,
    aliases: [],
    own_domains: ['ondam.example'],
    address_terms: [],
    phone_numbers: [],
    distinguishing_terms: [],
    identity_strength: 'SUFFICIENT',
    name_is_generic: false,
    gaps_ko: [],
    ...over,
  };
}

describe('측정이 되는지', () => {
  it('측정 가능 여부를 글자로 말한다', () => {
    render(<BrandCard brand={brand()} />);

    expect(screen.getByText('측정 가능')).toBeInTheDocument();
  });

  it('측정 불가는 그렇게 적는다', () => {
    render(<BrandCard brand={brand({ identity_strength: 'INSUFFICIENT' })} />);

    expect(screen.getByText('측정 불가')).toBeInTheDocument();
  });

  it('여러 업체가 함께 쓰는 이름이면 그 사실을 붙인다', () => {
    render(<BrandCard brand={brand({ name_is_generic: true })} />);

    expect(screen.getByText('여러 업체가 함께 쓰는 이름')).toBeInTheDocument();
  });
});

describe('빈 칸', () => {
  it('비어 있는 항목을 감추지 않는다', () => {
    // 감추면 "다 채웠다" 로 보인다. 비어 있다는 것이 여기서 가장 중요한 정보다.
    render(<BrandCard brand={brand()} />);

    expect(screen.getByText('대표번호')).toBeInTheDocument();
    expect(screen.getAllByText('없음').length).toBeGreaterThan(0);
  });

  it('무엇을 넣어야 하는지 그대로 보여준다', () => {
    render(
      <BrandCard
        brand={brand({
          identity_strength: 'INSUFFICIENT',
          gaps_ko: ['전화번호를 등록하세요. 가장 효과가 큰 한 가지입니다.'],
        })}
      />,
    );

    expect(screen.getByText(/가장 효과가 큰 한 가지/)).toBeInTheDocument();
  });
});
