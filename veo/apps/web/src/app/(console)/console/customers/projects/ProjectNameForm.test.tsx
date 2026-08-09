/**
 * 프로젝트 이름 고치기 — **이름만 바꾼다.**
 *
 * 이 화면이 지키는 것 셋 —
 *
 * 1. **측정 조건을 건드리지 않는다.** 서버는 slug·업체·지역·명세 판까지 받는다. 여기서
 *    그중 하나라도 함께 보내면 지난 진단과의 비교가 조용히 끊긴다(ADR 0010). 보내는
 *    것은 `name` 하나여야 한다.
 * 2. **서버가 준 사유를 그대로 낸다.** 우리 문장으로 덮으면 사람이 엉뚱한 곳을 고친다.
 * 3. **안 바뀐 이름을 저장하지 않는다.** 아무 일도 안 일어난 것을 "고쳤습니다" 로
 *    보이게 만들 이유가 없다.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const refresh = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }));

const { ProjectNameForm } = await import('./ProjectNameForm');

function reply(body: unknown, ok = true) {
  return { ok, json: () => Promise.resolve(body) } as unknown as Response;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply({ ok: true, name: '새 이름' })));
});

async function openForm() {
  const user = userEvent.setup();
  render(<ProjectNameForm projectId="prj-1" projectName="옛 이름" />);
  await user.click(screen.getByRole('button', { name: '이름 고치기' }));
  return user;
}

describe('평소에는 접혀 있다', () => {
  it('목록에서는 링크 하나만 보인다', () => {
    render(<ProjectNameForm projectId="prj-1" projectName="옛 이름" />);

    // 프로젝트 다섯 개짜리 화면이 입력칸 다섯 개가 되면 안 된다.
    expect(screen.queryByLabelText('프로젝트 이름')).toBeNull();
    expect(screen.getByRole('button', { name: '이름 고치기' })).toBeTruthy();
  });

  it('누르면 지금 이름이 채워진 채로 열린다', async () => {
    await openForm();

    expect(screen.getByLabelText<HTMLInputElement>('프로젝트 이름').value).toBe('옛 이름');
  });
});

describe('이름만 보낸다', () => {
  it('보내는 몸통에 name 과 projectId 뿐이다', async () => {
    const user = await openForm();

    const field = screen.getByLabelText('프로젝트 이름');
    await user.clear(field);
    await user.type(field, '새 이름');
    await user.click(screen.getByRole('button', { name: '저장' }));

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    const sent = JSON.parse(String(init?.body)) as Record<string, unknown>;

    expect(sent).toEqual({ projectId: 'prj-1', name: '새 이름' });
    // 측정 조건이 하나라도 섞이면 지난 진단과의 비교가 끊긴다.
    for (const forbidden of ['slug', 'locale', 'customer_id', 'customerId', 'settings']) {
      expect(sent).not.toHaveProperty(forbidden);
    }
  });

  it('앞뒤 공백을 떼고 보낸다', async () => {
    const user = await openForm();

    const field = screen.getByLabelText('프로젝트 이름');
    await user.clear(field);
    await user.type(field, '  새 이름  ');
    await user.click(screen.getByRole('button', { name: '저장' }));

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(JSON.parse(String(init?.body)).name).toBe('새 이름');
  });
});

describe('안 바뀌었으면 보내지 않는다', () => {
  it('열자마자 저장 단추가 눌리지 않는다', async () => {
    await openForm();

    expect(screen.getByRole('button', { name: '저장' }).hasAttribute('disabled')).toBe(true);
  });

  it('공백만 더한 것도 안 바뀐 것이다', async () => {
    const user = await openForm();
    await user.type(screen.getByLabelText('프로젝트 이름'), '   ');

    expect(screen.getByRole('button', { name: '저장' }).hasAttribute('disabled')).toBe(true);
  });
});

describe('실패를 삼키지 않는다', () => {
  it('서버가 준 사유를 그대로 보인다', async () => {
    vi.mocked(fetch).mockResolvedValue(
      reply({ ok: false, message: '같은 주소이름(slug)을 쓰는 프로젝트가 이미 있습니다.' }, false),
    );
    const user = await openForm();

    const field = screen.getByLabelText('프로젝트 이름');
    await user.clear(field);
    await user.type(field, '새 이름');
    await user.click(screen.getByRole('button', { name: '저장' }));

    expect(
      await screen.findByText('같은 주소이름(slug)을 쓰는 프로젝트가 이미 있습니다.'),
    ).toBeTruthy();
    // 실패했는데 닫으면 사람은 저장된 줄 안다.
    expect(screen.getByLabelText('프로젝트 이름')).toBeTruthy();
    expect(refresh).not.toHaveBeenCalled();
  });

  it('연결이 끊겨도 조용히 넘어가지 않는다', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('boom'));
    const user = await openForm();

    const field = screen.getByLabelText('프로젝트 이름');
    await user.clear(field);
    await user.type(field, '새 이름');
    await user.click(screen.getByRole('button', { name: '저장' }));

    expect(await screen.findByText('서버에 연결하지 못했습니다.')).toBeTruthy();
  });

  it('성공하면 닫고 목록을 다시 읽는다', async () => {
    const user = await openForm();

    const field = screen.getByLabelText('프로젝트 이름');
    await user.clear(field);
    await user.type(field, '새 이름');
    await user.click(screen.getByRole('button', { name: '저장' }));

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(screen.queryByLabelText('프로젝트 이름')).toBeNull();
  });
});
