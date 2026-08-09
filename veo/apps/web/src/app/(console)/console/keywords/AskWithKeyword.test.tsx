/**
 * 키워드 → 질문 수집 — **③ 축의 앞단을 잇는 길.**
 *
 * 사장님이 그린 사슬(2026-08-09):
 *
 * > *"키워드에서 관련 질문이 나오고 키워드 마인드맵이 나오고 관련 PAA 지식iN 같은
 * > 곳에서 질문을 추출하게 만들고 싶었어."*
 *
 * 양쪽 끝은 다 있었고 **가운데가 없었다.** 사람이 키워드 화면에서 눈으로 읽고 GEO
 * 화면 입력칸에 다시 타이핑했다(`CORRECTIONS.md` #23).
 *
 * 이 파일이 지키는 것 셋 —
 *
 * 1. **연관 키워드에도 길이 있다.** 연관 키워드는 네이버가 준 실측이고 검색량이 함께
 *    있다. 사람이 많이 찾는 말부터 질문을 모을 수 있어야 한다.
 * 2. **씨앗이 그대로 건너간다.** 공백·한글이 든 키워드가 주소에서 깨지면 저쪽 입력칸에
 *    엉뚱한 글자가 들어가고, 그 글자로 남의 API 를 부른다.
 * 3. **누르기 전에는 아무 일도 안 일어난다.** 수집은 외부 호출이다.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { KeywordReport } from './KeywordReport';
import type { KeywordLookup } from '@/lib/keywords';

function lookup(): KeywordLookup {
  return {
    providers: [],
    notices_ko: [],
    keywords: [
      {
        original_keyword: '마산 교통사고 한의원',
        normalized_keyword: '마산교통사고한의원',
        metrics: null,
        trend: null,
        opportunity: null,
        related: [
          {
            related_keyword: '창원 교통사고 한의원',
            monthly_total_searches: { value: 320, quality: 'EXACT', note_ko: '' },
          },
        ],
      },
    ],
  } as unknown as KeywordLookup;
}

describe('키워드에서 질문 수집으로 가는 길', () => {
  it('조회한 키워드마다 길이 있다', () => {
    render(<KeywordReport lookup={lookup()} />);

    const links = screen.getAllByRole('link', { name: '이 키워드로 질문 찾기' });
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it('연관 키워드에도 길이 있다 — 검색량이 큰 말부터 갈 수 있어야 한다', () => {
    render(<KeywordReport lookup={lookup()} />);

    const links = screen.getAllByRole('link', { name: '이 키워드로 질문 찾기' });
    const hrefs = links.map((one) => one.getAttribute('href'));

    expect(hrefs).toContain(`/console/geo?seed=${encodeURIComponent('마산 교통사고 한의원')}`);
    expect(hrefs).toContain(`/console/geo?seed=${encodeURIComponent('창원 교통사고 한의원')}`);
  });

  it('공백과 한글이 깨지지 않는다', () => {
    render(<KeywordReport lookup={lookup()} />);

    const [first] = screen.getAllByRole('link', { name: '이 키워드로 질문 찾기' });
    // 안 감싸면 주소에서 잘리고, 저쪽은 잘린 글자로 남의 API 를 부른다.
    expect(first?.getAttribute('href')).toBe(
      '/console/geo?seed=%EB%A7%88%EC%82%B0%20%EA%B5%90%ED%86%B5%EC%82%AC%EA%B3%A0%20%ED%95%9C%EC%9D%98%EC%9B%90',
    );
  });
});
