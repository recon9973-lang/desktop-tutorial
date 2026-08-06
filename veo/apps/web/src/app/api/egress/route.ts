/**
 * 한국 관측점 — 페이지 한 장을 한국에서 대신 받아 API 에 돌려준다.
 *
 * **왜 여기인가.** 이 앱은 Vercel `icn1`(서울)에서 돈다. 실측으로 확인한 나가는 IP 는
 * `3.37.129.161` = `ec2-3-37-129-161.ap-northeast-2.compute.amazonaws.com` (인천, AWS
 * 서울)이다. API 는 Railway 싱가포르(`34.21.188.186`)에 있어서 거래처 일부가 내는
 * 자바스크립트 쿠키 검사(759·760바이트)에 막힌다. 같은 주소를 여기서 받으면
 * 51,262·64,262바이트가 정상적으로 온다.
 *
 * 타사(NXT)가 같은 사이트를 문제없이 재는 이유도 그쪽이 AWS 서울이기 때문이다.
 *
 * ## 이 창구가 위험해지지 않도록
 *
 * 아무 주소나 받아 주는 창구는 **남의 서버를 우리 이름으로 두드리는 도구**가 된다.
 * 그래서 네 겹으로 막는다.
 *
 * 1. **열쇠.** `x-veo-egress-token` 이 맞지 않으면 아무 일도 하지 않는다.
 * 2. **주소를 다시 확인한다.** API 쪽 가드가 이미 봤지만, 여기서 접속하는 IP 는 다를 수
 *    있다(DNS 가 다르게 답할 수 있다). 그 틈이 곧 SSRF 다. 그래서 여기서도 이름을 풀어
 *    **사설·루프백·링크로컬** 이면 거절한다. 특히 `169.254.169.254`(클라우드 메타데이터)
 *    가 이 목록에 든다.
 * 3. **리다이렉트를 따라가지 않는다.** 3xx 는 그대로 돌려주고, 다음 홉은 API 쪽 가드가
 *    다시 검증한다. 여기서 따라가면 경유가 재검증을 건너뛰는 구멍이 된다.
 * 4. **크기를 자른다.** 4MB 를 넘으면 자르고 잘랐다고 말한다.
 *
 * 응답 본문은 base64 로 담는다. 원문 바이트를 그대로 넘겨야 해시와 인코딩 판정이
 * 어긋나지 않는다 — 문자열로 옮기면 그 순간 우리가 잰 것이 아니게 된다.
 */

import { NextResponse } from 'next/server';
import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';

import { fetchPinned, type PinnedResponse } from '@/lib/pinned-fetch';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 30;

//: 직접 수집(`veo.common.security.limits.FetchLimits.max_response_bytes`)과 **같은 값**으로
//: 둔다. 다르면 같은 사이트가 경로에 따라 다르게 잘리고, 어느 쪽이 진짜인지 알 수 없게 된다.
const MAX_BODY_BYTES = 2 * 1024 * 1024;

//: API 쪽 응답 대기(30초)보다 짧아야 한다 — 우리가 먼저 포기해야 사유가 남는다.
const FETCH_TIMEOUT_MS = 25_000;
const NO_STORE = { 'cache-control': 'no-store' } as const;

/** 돌려줄 헤더. 목록에 없으면 버린다 — 새 헤더가 생겨도 자동으로 새어 나가지 않는다. */
const KEPT_HEADERS = [
  'content-type',
  'content-length',
  'content-encoding',
  'location',
  'x-robots-tag',
  'last-modified',
  'etag',
  'cache-control',
] as const;

function deny(status: number, message: string): NextResponse {
  return NextResponse.json({ message }, { status, headers: NO_STORE });
}

/** 이 주소로 나가도 되는가 — 사설·루프백·링크로컬이면 안 된다. */
function isPublicAddress(address: string): boolean {
  const version = isIP(address);
  if (version === 4) {
    const octets = address.split('.').map(Number);
    if (octets.length !== 4 || octets.some((n) => !Number.isInteger(n))) return false;
    const [a, b] = octets as [number, number, number, number];
    if (a === 10 || a === 127 || a === 0) return false;
    if (a === 169 && b === 254) return false; // 클라우드 메타데이터가 여기 있다
    if (a === 172 && b >= 16 && b <= 31) return false;
    if (a === 192 && b === 168) return false;
    if (a === 100 && b >= 64 && b <= 127) return false; // 통신사 내부(CGNAT)
    return a < 224; // 멀티캐스트·예약 대역은 제외
  }
  if (version === 6) {
    const lower = address.toLowerCase();
    if (lower === '::1' || lower === '::') return false;
    if (lower.startsWith('fe80') || lower.startsWith('fc') || lower.startsWith('fd')) return false;
    // IPv4 를 감싼 형태는 감싼 주소로 다시 판단한다.
    const mapped = lower.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
    return mapped?.[1] !== undefined ? isPublicAddress(mapped[1]) : true;
  }
  return false;
}

export async function POST(request: Request): Promise<NextResponse> {
  const expected = process.env.VEO_EGRESS_TOKEN ?? '';
  if (expected === '') {
    // 열쇠가 설정되지 않은 배포에서는 **창구 자체가 없는 것으로 한다.**
    return deny(404, 'not found');
  }
  if (request.headers.get('x-veo-egress-token') !== expected) {
    return deny(401, 'unauthorized');
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return deny(400, 'invalid body');
  }
  const source = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const target = typeof source.url === 'string' ? source.url : '';
  const userAgent = typeof source.userAgent === 'string' ? source.userAgent : '';
  if (target === '' || userAgent === '') return deny(400, 'url and userAgent are required');

  let parsed: URL;
  try {
    parsed = new URL(target);
  } catch {
    return deny(400, 'invalid url');
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return deny(400, 'unsupported scheme');
  }

  // 이름을 여기서 다시 푼다. API 가 검증한 주소와 여기서 닿는 주소는 다를 수 있고,
  // 그 틈으로 내부망을 두드리게 하는 것이 SSRF 다.
  let pinned: string;
  try {
    const addresses = await lookup(parsed.hostname, { all: true });
    if (addresses.length === 0) return deny(400, 'unresolvable host');
    if (!addresses.every((entry) => isPublicAddress(entry.address))) {
      return deny(403, 'destination is not a public address');
    }
    // **검사한 바로 그 주소로 간다.** 이름을 한 번 더 풀게 두면 검사한 주소와 접속한
    // 주소가 달라질 수 있고(DNS 재바인딩), 그 순간 위의 검사는 아무것도 막지 못한다.
    pinned = addresses[0]!.address;
  } catch {
    return deny(400, 'unresolvable host');
  }

  let response: PinnedResponse;
  try {
    response = await fetchPinned({
      address: pinned,
      hostname: parsed.hostname,
      url: parsed,
      userAgent,
      maxBytes: MAX_BODY_BYTES,
      timeoutMs: FETCH_TIMEOUT_MS,
    });
  } catch (error) {
    return deny(502, `upstream failed: ${String(error)}`);
  }

  const headers: Record<string, string> = {};
  for (const name of KEPT_HEADERS) {
    const value = response.headers[name];
    if (value !== undefined) headers[name] = value;
  }

  return NextResponse.json(
    {
      status: response.status,
      finalUrl: parsed.toString(),
      headers,
      bodyBase64: Buffer.from(response.body).toString('base64'),
      truncated: response.truncated,
    },
    { headers: NO_STORE },
  );
}
