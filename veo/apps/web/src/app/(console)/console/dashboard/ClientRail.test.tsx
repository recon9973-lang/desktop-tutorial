/**
 * 거래처 레일 — **화면에 실제로 무엇이 찍히는가.**
 *
 * 자료 층 시험(`lib/dashboard.test.ts`)은 값이 맞는지를 본다. 이 파일은 그 값이
 * **글자로 어떻게 나가는지**를 본다. 둘은 다른 자리에서 깨진다 — 값이 `null` 인데
 * 화면이 `0.00` 을 찍는 일은 자료 시험을 다 통과하고도 일어난다.
 *
 * 지키는 것 셋 —
 *
 * 1. 못 잰 곳은 `—`. `0.00` 으로 그리면 "쟀는데 0 점" 과 구별되지 않는다.
 * 2. 점수는 **자른다.** `71.039` 는 `71.04` 가 아니라 `71.03`.
 * 3. 밀린 줄에는 **왜 밀렸는지**가 글자로 함께 나간다. 색만으로 말하지 않는다.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import type { ClientRow } from '@/lib/dashboard';

import { ClientRail, clientNote, clientTone } from './ClientRail';

function row(overrides: Partial<ClientRow> = {}): ClientRow {
  return {
    customerId: 'c1',
    name: '참사랑한의원',
    siteCount: 1,
    score: 71.03,
    measuredAt: '2026-08-08T00:00:00Z',
    ageDays: 1,
    unmeasuredSites: 0,
    ...overrides,
  };
}

describe('화면에 찍히는 값', () => {
  it('업체 이름과 점수를 낸다', () => {
    render(<ClientRail rows={[row()]} />);

    expect(screen.getByText('참사랑한의원')).toBeTruthy();
    expect(screen.getByText('71.03')).toBeTruthy();
  });

  it('점수를 자른다 — 반올림하지 않는다', () => {
    render(<ClientRail rows={[row({ score: 71.039 })]} />);

    expect(screen.getByText('71.03')).toBeTruthy();
    expect(screen.queryByText('71.04')).toBeNull();
  });

  it('못 잰 곳은 — 로 낸다. 0.00 이 아니다', () => {
    render(<ClientRail rows={[row({ score: null, ageDays: null })]} />);

    expect(screen.getByText('—')).toBeTruthy();
    expect(screen.queryByText('0.00')).toBeNull();
    // 단위까지 붙이면 "— 점" 이 되어 잰 값처럼 읽힌다.
    expect(screen.queryByText('점')).toBeNull();
  });

  it('누르면 그 거래처의 현황 화면으로 간다', () => {
    render(<ClientRail rows={[row({ customerId: 'abc-123' })]} />);

    const link = screen.getByRole('link', { name: /참사랑한의원/ });
    expect(link.getAttribute('href')).toBe('/console/customers/abc-123');
  });

  it('받은 순서대로 그린다 — 화면이 다시 정렬하지 않는다', () => {
    render(
      <ClientRail
        rows={[
          row({ customerId: 'a', name: '나중', score: 95 }),
          row({ customerId: 'b', name: '먼저', score: 10 }),
        ]}
      />,
    );

    const names = screen.getAllByRole('link').map((link) => link.textContent ?? '');
    expect(names[0]).toContain('나중');
    // 두 곳에서 정렬하면 반드시 어긋난다. 순서는 자료 층이 정한다.
    expect(names[1]).toContain('먼저');
  });

  it('거래처가 없으면 빈 구역을 그리지 않는다', () => {
    const { container } = render(<ClientRail rows={[]} />);
    expect(container.textContent).toBe('');
  });
});

describe('밀린 이유를 글자로 말한다', () => {
  it('안 잰 주소가 있으면 그것부터', () => {
    expect(clientNote(row({ unmeasuredSites: 2, siteCount: 3 }))).toBe(
      '아직 안 잰 주소 2곳',
    );
  });

  it('한 번도 안 쟀으면 그렇게 적는다', () => {
    expect(clientNote(row({ ageDays: null, score: null }))).toBe(
      '한 번도 진단하지 않았습니다',
    );
  });

  it('14일을 넘기면 며칠 지났는지 적는다', () => {
    expect(clientNote(row({ ageDays: 30 }))).toBe('30일 지났습니다');
  });

  it('오늘 잰 것을 "0일 전" 이라 하지 않는다', () => {
    expect(clientNote(row({ ageDays: 0 }))).toBe('오늘 진단했습니다');
  });
});

describe('색은 글자를 대신하지 않는다 — 등급은 자료로 정한다', () => {
  it('안 잰 주소가 있으면 가장 무겁다', () => {
    expect(clientTone(row({ unmeasuredSites: 1 }))).toBe('fail');
  });

  it('한 번도 안 쟀으면 "오래됨" 보다 무겁다 — 시작조차 안 했다', () => {
    expect(clientTone(row({ ageDays: null }))).toBe('fail');
    expect(clientTone(row({ ageDays: 30 }))).toBe('warn');
  });

  it('최근에 쟀으면 아무 표시도 하지 않는다', () => {
    expect(clientTone(row({ ageDays: 3 }))).toBe('plain');
  });

  it('경계값 14일은 오래된 쪽이다', () => {
    expect(clientTone(row({ ageDays: 13 }))).toBe('plain');
    expect(clientTone(row({ ageDays: 14 }))).toBe('warn');
  });
});
