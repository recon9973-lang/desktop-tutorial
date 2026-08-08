/**
 * 홈페이지에서 읽어 온 값은 **고르는 것**이지 채워지는 것이 아니다.
 *
 * 이 시험이 지키는 것 넷 —
 *
 * 1. 사이트가 스스로 선언한 값만 미리 체크된다. 본문에서 찾은 값은 사람이 누른다.
 * 2. 고르지 않은 값은 폼에 들어가지 않는다.
 * 3. 사업자등록번호는 고르는 값이 아니다 — 대조에 안 걸리는 값으로 칸을 채우지 않는다.
 * 4. 못 읽었으면 **왜 못 읽었는지** 보인다. 빈 목록만 보이면 "정보가 없는 사이트"로 읽힌다.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  SiteIdentityPicker,
  collectPicked,
  initialPicks,
  type IdentityCandidate,
  type SiteIdentityDraft,
} from './SiteIdentityPicker';

function candidate(over: Partial<IdentityCandidate> = {}): IdentityCandidate {
  return {
    field: 'PHONE',
    value: '053-355-0000',
    source: 'FOUND_IN_TEXT',
    preselected: false,
    note_ko: '본문에서 찾은 값입니다. 맞는지 확인하십시오.',
    ...over,
  };
}

function draft(over: Partial<SiteIdentityDraft> = {}): SiteIdentityDraft {
  return {
    url: 'https://ondam.kr',
    candidates: [
      candidate({ field: 'DISPLAY_NAME', value: '더바른한의원', source: 'DECLARED', preselected: true }),
      candidate({ field: 'PHONE', value: '053-355-0000', source: 'DECLARED', preselected: true }),
      candidate({ field: 'PHONE', value: '010-1234-5678' }),
      candidate({ field: 'ADDRESS', value: '대구광역시 북구 옥산로 95' }),
      candidate({ field: 'REPRESENTATIVE', value: '권영재' }),
    ],
    notes_ko: [],
    ...over,
  };
}

describe('처음 체크되는 것', () => {
  it('사이트가 선언한 값만 미리 체크된다', () => {
    const picked = initialPicks(draft());

    expect(picked.has('DISPLAY_NAME:더바른한의원')).toBe(true);
    expect(picked.has('PHONE:053-355-0000')).toBe(true);
  });

  it('본문에서 찾은 값은 미리 체크되지 않는다', () => {
    const picked = initialPicks(draft());

    expect(picked.has('PHONE:010-1234-5678')).toBe(false);
    expect(picked.has('REPRESENTATIVE:권영재')).toBe(false);
  });
});

describe('고른 값 모으기', () => {
  it('고른 것만 칸으로 간다', () => {
    const values = collectPicked(draft(), initialPicks(draft()));

    expect(values.displayName).toBe('더바른한의원');
    expect(values.phoneNumbers).toBe('053-355-0000');
    // 체크 안 한 것은 없다.
    expect(values.addressTerms).toBeUndefined();
    expect(values.doctorNames).toBeUndefined();
  });

  it('여러 개를 고르면 쉼표로 잇는다', () => {
    const values = collectPicked(
      draft(),
      new Set(['PHONE:053-355-0000', 'PHONE:010-1234-5678']),
    );

    expect(values.phoneNumbers).toBe('053-355-0000, 010-1234-5678');
  });

  it('대표자는 원장 이름 칸으로 간다', () => {
    const values = collectPicked(draft(), new Set(['REPRESENTATIVE:권영재']));

    expect(values.doctorNames).toBe('권영재');
  });

  it('사업자등록번호는 어느 칸에도 넣지 않는다', () => {
    /* AI 답변에 인쇄될 일이 거의 없어 대조에 안 걸린다. 넣으면 칸만 채운다. */
    const one = draft({
      candidates: [candidate({ field: 'BUSINESS_NUMBER', value: '301-95-18791' })],
    });

    expect(collectPicked(one, new Set(['BUSINESS_NUMBER:301-95-18791']))).toEqual({});
  });
});

describe('화면', () => {
  it('읽어 온 값을 항목별로 보여 준다', () => {
    render(
      <SiteIdentityPicker draft={draft()} busy={false} error={null} onLoad={vi.fn()} onApply={vi.fn()} />,
    );

    expect(screen.getByRole('group', { name: '대표번호' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /053-355-0000/ })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /010-1234-5678/ })).not.toBeChecked();
  });

  it('어디서 나온 값인지 함께 보인다', () => {
    render(
      <SiteIdentityPicker draft={draft()} busy={false} error={null} onLoad={vi.fn()} onApply={vi.fn()} />,
    );

    expect(screen.getAllByText(/본문에서 찾은 값입니다/).length).toBeGreaterThan(0);
  });

  it('사업자등록번호는 참고로만 보이고 고를 수 없다', () => {
    const one = draft({
      candidates: [candidate({ field: 'BUSINESS_NUMBER', value: '301-95-18791' })],
    });
    render(
      <SiteIdentityPicker draft={one} busy={false} error={null} onLoad={vi.fn()} onApply={vi.fn()} />,
    );

    expect(screen.getByText(/301-95-18791/)).toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('고른 것만 넘긴다', async () => {
    const onApply = vi.fn();
    render(
      <SiteIdentityPicker draft={draft()} busy={false} error={null} onLoad={vi.fn()} onApply={onApply} />,
    );

    await userEvent.click(screen.getByRole('checkbox', { name: /권영재/ }));
    await userEvent.click(screen.getByRole('button', { name: '고른 값 넣기' }));

    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({ doctorNames: '권영재', phoneNumbers: '053-355-0000' }),
    );
  });

  it('체크를 풀면 넘어가지 않는다', async () => {
    const onApply = vi.fn();
    render(
      <SiteIdentityPicker draft={draft()} busy={false} error={null} onLoad={vi.fn()} onApply={onApply} />,
    );

    await userEvent.click(screen.getByRole('checkbox', { name: /053-355-0000/ }));
    await userEvent.click(screen.getByRole('button', { name: '고른 값 넣기' }));

    expect(onApply).toHaveBeenCalledWith(expect.not.objectContaining({ phoneNumbers: expect.anything() }));
  });

  /** 실제 venomad.com 이 이 모양이다 — 구조화 데이터와 og:site_name 의 상호가 다르다. */
  const twoNames = draft({
    candidates: [
      candidate({ field: 'DISPLAY_NAME', value: '(주)베놈', source: 'DECLARED', preselected: true }),
      candidate({ field: 'DISPLAY_NAME', value: '베놈애드', source: 'DECLARED', preselected: true }),
    ],
  });

  it('선언된 상호가 둘이어도 하나만 체크해 둔다', () => {
    /* 둘 다 체크해 두면 화면은 둘을 고른 것처럼 보이는데 저장은 하나만 된다. */
    render(
      <SiteIdentityPicker draft={twoNames} busy={false} error={null} onLoad={vi.fn()} onApply={vi.fn()} />,
    );

    expect(screen.getByRole('checkbox', { name: /\(주\)베놈/ })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /베놈애드/ })).not.toBeChecked();
  });

  it('상호를 바꿔 고르면 앞의 것이 풀린다 — 칸이 하나다', async () => {
    const onApply = vi.fn();
    render(
      <SiteIdentityPicker draft={twoNames} busy={false} error={null} onLoad={vi.fn()} onApply={onApply} />,
    );

    await userEvent.click(screen.getByRole('checkbox', { name: /베놈애드/ }));

    expect(screen.getByRole('checkbox', { name: /\(주\)베놈/ })).not.toBeChecked();

    await userEvent.click(screen.getByRole('button', { name: '고른 값 넣기' }));
    expect(onApply).toHaveBeenCalledWith({ displayName: '베놈애드' });
  });

  it('못 읽었으면 왜 못 읽었는지 보인다', () => {
    const empty = draft({
      candidates: [],
      notes_ko: ['홈페이지가 503 로 응답했습니다.'],
    });
    render(
      <SiteIdentityPicker draft={empty} busy={false} error={null} onLoad={vi.fn()} onApply={vi.fn()} />,
    );

    expect(screen.getByText('홈페이지가 503 로 응답했습니다.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '고른 값 넣기' })).not.toBeInTheDocument();
  });

  it('주소를 비운 채 누르면 부르지 않는다', async () => {
    const onLoad = vi.fn();
    render(
      <SiteIdentityPicker draft={null} busy={false} error={null} onLoad={onLoad} onApply={vi.fn()} />,
    );

    await userEvent.click(screen.getByRole('button', { name: '불러오기' }));

    expect(onLoad).toHaveBeenCalledWith('');
  });

  it('이미 등록된 홈페이지 주소를 미리 채운다', async () => {
    /* 거래처 등록에서 받은 주소를 여기서 또 치게 두면, 치는 만큼 안 친다. */
    const onLoad = vi.fn();
    render(
      <SiteIdentityPicker
        draft={null}
        busy={false}
        error={null}
        initialUrl="https://chamsarang1075.com"
        onLoad={onLoad}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('읽어 올 홈페이지 주소')).toHaveValue(
      'https://chamsarang1075.com',
    );

    await userEvent.click(screen.getByRole('button', { name: '불러오기' }));
    expect(onLoad).toHaveBeenCalledWith('https://chamsarang1075.com');
  });
});
