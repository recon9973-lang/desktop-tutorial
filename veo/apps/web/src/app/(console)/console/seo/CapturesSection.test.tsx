/**
 * 원자료 화면 — **남의 사이트 글자를 우리 콘솔에서 실행하지 않는다.**
 *
 * 이 화면이 그리는 것은 거래처 사이트에서 받아 온 HTML 이다. 그것을 HTML 로 그리면
 * 그 안의 `<script>` 가 **우리 콘솔의 권한으로** 돈다 — 진단하러 간 사이트가 우리
 * 세션을 가져가는 길이 열린다. 화면 하나 고치다가 `dangerouslySetInnerHTML` 을
 * 넣으면 그날 생긴다.
 *
 * 나머지 셋은 이 자리가 무엇을 위한 것인가에 관한 것이다 —
 * 못 읽은 것을 숨기지 않고, 잘린 것을 잘렸다고 말하고, 받은 그대로 보인다.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const readCaptures = vi.fn();
vi.mock('@/lib/scan-report', () => ({ readCaptures }));

const { CapturesSection } = await import('./CapturesSection');

function capture(overrides: Record<string, unknown> = {}) {
  return {
    url: 'https://example.kr/',
    finalUrl: 'https://example.kr/',
    status: 200,
    headers: { 'content-type': 'text/html' },
    requestHeaders: { 'user-agent': 'VeoBot/1.0' },
    body: '<html><body>안녕하세요</body></html>',
    byteSize: 1234,
    truncated: false,
    contentHash: 'abc123',
    fetchedAt: '2026-08-09T00:00:00Z',
    readFailureKo: null,
    ...overrides,
  };
}

function withCaptures(captures: ReturnType<typeof capture>[], noteKo = '') {
  readCaptures.mockResolvedValue({
    ok: true,
    data: { scanRunId: 'run-1', captures, noteKo },
  });
}

async function renderSection() {
  render(await CapturesSection({ scanRunId: 'run-1' }));
}

describe('받아 온 글자를 실행하지 않는다', () => {
  it('이 파일이 innerHTML 을 쓰지 않는다', () => {
    const source = readFileSync(join(import.meta.dirname, 'CapturesSection.tsx'), 'utf-8');

    // **낱말이 아니라 쓰임새를 본다.** 주석이 이 규칙을 설명하려면 그 이름을 적어야
    // 하는데, 이름만 찾으면 설명하는 주석까지 위반으로 잡힌다(실제로 잡혔다).
    // 대입·속성 모양일 때만 위반이다.
    const used = /dangerouslySetInnerHTML\s*[=:]|\.innerHTML\s*=/.test(source);

    expect(
      used,
      '진단 대상 사이트의 HTML 을 그대로 그리면 그 안의 스크립트가 우리 콘솔 권한으로 ' +
        '돈다. 본문은 `<pre>` 안에 글자로만 넣는다.',
    ).toBe(false);
  });

  it('본문의 태그가 글자로 나온다 — 요소로 만들어지지 않는다', async () => {
    withCaptures([capture({ body: '<script>window.__pwned = true</script><b>굵게</b>' })]);
    await renderSection();

    // 태그가 글자 그대로 보인다.
    expect(screen.getByText(/<script>window.__pwned = true<\/script>/)).toBeTruthy();
    // 그리고 요소로는 만들어지지 않았다.
    expect(document.querySelector('script')).toBeNull();
    expect(document.querySelector('b')).toBeNull();
  });
});

describe('무엇을 받았는지 그대로 말한다', () => {
  it('못 읽은 응답의 사유를 보인다', async () => {
    withCaptures([
      capture({ status: 403, readFailureKo: '접근이 차단되었습니다(403).', body: '' }),
    ]);
    await renderSection();

    expect(screen.getByText('접근이 차단되었습니다(403).')).toBeTruthy();
    expect(screen.getByText('403')).toBeTruthy();
  });

  it('잘린 본문을 잘렸다고 말한다', async () => {
    withCaptures([capture({ truncated: true })]);
    await renderSection();

    // 잘린 것을 말하지 않으면 "본문에 그 태그가 없다" 는 판정이 사실처럼 읽힌다.
    expect(screen.getByText(/앞부분만 남겼습니다/)).toBeTruthy();
  });

  it('최종 주소가 다르면 그것도 보인다 — 넘겨진 것을 숨기지 않는다', async () => {
    withCaptures([capture({ finalUrl: 'https://www.example.kr/home' })]);
    await renderSection();

    expect(screen.getByText('https://www.example.kr/home')).toBeTruthy();
  });

  it('주소가 같으면 최종 주소 줄을 만들지 않는다', async () => {
    withCaptures([capture()]);
    await renderSection();

    expect(screen.queryByText('최종 주소')).toBeNull();
  });

  it('우리가 보낸 헤더도 보인다 — 무엇을 보내서 차단됐는지 알아야 한다', async () => {
    withCaptures([capture()]);
    await renderSection();

    expect(screen.getByText(/우리가 보낸 헤더/)).toBeTruthy();
  });
});

describe('없는 것을 있는 것처럼 그리지 않는다', () => {
  it('응답이 없으면 왜 없는지 말한다', async () => {
    withCaptures([], '이 진단보다 앞선 판에서는 원자료를 저장하지 않았습니다.');
    await renderSection();

    expect(screen.getByText(/원자료를 저장하지 않았습니다/)).toBeTruthy();
  });

  it('못 불러오면 빈 목록이 아니라 오류로 그린다', async () => {
    readCaptures.mockResolvedValue({ ok: false, message: '연결 실패' });
    await renderSection();

    // 빈 목록으로 그리면 "받은 응답이 없다" 는 사실이 되어 버린다.
    expect(screen.getByText('원자료를 불러오지 못했습니다')).toBeTruthy();
  });
});
