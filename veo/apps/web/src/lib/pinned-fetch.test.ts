/**
 * 못박은 주소로만 가는가.
 *
 * 이 시험이 지키는 것은 하나다: **이름이 어디를 가리키든, 접속은 우리가 검사한
 * 주소로 간다.** 그것이 아니면 경유 창구의 주소 검사는 아무것도 막지 못한다
 * (DNS 재바인딩 · 2026-08-06 감사).
 */

import { createServer, type Server } from 'node:http';
import { AddressInfo } from 'node:net';
import { afterEach, describe, expect, it } from 'vitest';

import { fetchPinned } from './pinned-fetch';

let server: Server | undefined;

afterEach(() => {
  server?.close();
  server = undefined;
});

async function listen(
  handler: (path: string, headers: Record<string, string | string[] | undefined>) => [number, string],
): Promise<number> {
  server = createServer((request, response) => {
    const [status, body] = handler(request.url ?? '', request.headers);
    response.writeHead(status, { 'content-type': 'text/html' });
    response.end(body);
  });
  await new Promise<void>((resolve) => server!.listen(0, '127.0.0.1', resolve));
  return (server!.address() as AddressInfo).port;
}

describe('접속은 검사한 주소로 간다', () => {
  it('이름이 아니라 주어진 주소로 접속한다', async () => {
    // 이름은 실제로 전혀 다른 곳(공인 IP)을 가리킨다. 그런데 접속은 127.0.0.1 로
    // 가야 한다 — 부르는 쪽이 그 주소를 검사했기 때문이다. 반대로 이름을 다시 풀면
    // 이 시험은 우리 서버에 닿지 못한다.
    const port = await listen(() => [200, '<html><title>받았다</title></html>']);

    const response = await fetchPinned({
      address: '127.0.0.1',
      hostname: 'example.com',
      url: new URL(`http://example.com:${port}/page`),
      userAgent: 'VEOBot/1.0',
      maxBytes: 1024 * 1024,
      timeoutMs: 5000,
    });

    expect(response.status).toBe(200);
    expect(Buffer.from(response.body).toString()).toContain('받았다');
  });

  it('가상 호스팅이 동작하도록 이름을 Host 헤더로 싣는다', async () => {
    let seenHost: string | undefined;
    const port = await listen((_path, headers) => {
      seenHost = headers.host as string;
      return [200, 'ok'];
    });

    await fetchPinned({
      address: '127.0.0.1',
      hostname: 'clinic.example',
      url: new URL(`http://clinic.example:${port}/`),
      userAgent: 'VEOBot/1.0',
      maxBytes: 1024,
      timeoutMs: 5000,
    });

    expect(seenHost).toBe(`clinic.example:${port}`);
  });

  it('요청한 경로와 질의를 그대로 보낸다', async () => {
    let seenPath: string | undefined;
    const port = await listen((path) => {
      seenPath = path;
      return [200, 'ok'];
    });

    await fetchPinned({
      address: '127.0.0.1',
      hostname: 'example.com',
      url: new URL(`http://example.com:${port}/a/b?q=1&r=2`),
      userAgent: 'VEOBot/1.0',
      maxBytes: 1024,
      timeoutMs: 5000,
    });

    expect(seenPath).toBe('/a/b?q=1&r=2');
  });
});

describe('리다이렉트와 크기', () => {
  it('3xx 를 따라가지 않고 그대로 돌려준다', async () => {
    server = createServer((request, response) => {
      if (request.url === '/') {
        response.writeHead(301, { location: '/moved' });
        response.end();
        return;
      }
      response.writeHead(200, { 'content-type': 'text/html' });
      response.end('따라왔다');
    });
    await new Promise<void>((resolve) => server!.listen(0, '127.0.0.1', resolve));
    const port = (server!.address() as AddressInfo).port;

    const response = await fetchPinned({
      address: '127.0.0.1',
      hostname: 'example.com',
      url: new URL(`http://example.com:${port}/`),
      userAgent: 'VEOBot/1.0',
      maxBytes: 1024,
      timeoutMs: 5000,
    });

    expect(response.status).toBe(301);
    expect(response.headers.location).toBe('/moved');
    expect(Buffer.from(response.body).toString()).not.toContain('따라왔다');
  });

  it('상한을 넘으면 자르고 잘랐다고 말한다', async () => {
    const port = await listen(() => [200, 'x'.repeat(5000)]);

    const response = await fetchPinned({
      address: '127.0.0.1',
      hostname: 'example.com',
      url: new URL(`http://example.com:${port}/`),
      userAgent: 'VEOBot/1.0',
      maxBytes: 1000,
      timeoutMs: 5000,
    });

    expect(response.truncated).toBe(true);
    expect(response.body.byteLength).toBe(1000);
  });

  it('상한 안이면 자르지 않는다', async () => {
    const port = await listen(() => [200, 'y'.repeat(500)]);

    const response = await fetchPinned({
      address: '127.0.0.1',
      hostname: 'example.com',
      url: new URL(`http://example.com:${port}/`),
      userAgent: 'VEOBot/1.0',
      maxBytes: 1000,
      timeoutMs: 5000,
    });

    expect(response.truncated).toBe(false);
    expect(response.body.byteLength).toBe(500);
  });
});
