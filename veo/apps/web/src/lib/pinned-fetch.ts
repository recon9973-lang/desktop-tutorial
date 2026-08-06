/**
 * 검증한 주소로 **못박아** 접속한다.
 *
 * ## 왜 필요한가 — 2026-08-06 감사에서 나왔다
 *
 * 경유 창구는 `dns.lookup` 으로 주소를 검사한 뒤 `fetch(url)` 을 불렀다. 그런데
 * `fetch` 는 **이름을 다시 푼다.** 검사한 주소와 접속한 주소가 다를 수 있고, 그 틈이
 * 곧 SSRF 다(DNS 재바인딩). 짧은 TTL 로 공인 IP 와 `169.254.169.254` 를 번갈아 답하면
 * 검사만 통과하고 접속은 내부로 간다.
 *
 * 도달 경로가 실제로 있었다. 무료 공개 진단은 **누구나 아무 주소나** 넣을 수 있고,
 * 받은 응답이 관문 페이지처럼 보이면 경유가 자동으로 발동한다.
 *
 * 파이썬 쪽 `veo.common.security.fetcher.SafeFetcher` 는 처음부터 이 창을 닫아 두었다 —
 * 가드가 돌려준 IP 로 접속하고, 호스트 이름은 `Host` 헤더와 SNI 로 실어 보낸다.
 * 여기서 하는 일이 그것과 같다. 같은 제품이 경로에 따라 다른 기준을 갖지 않게 한다.
 *
 * `undici` 를 쓰지 않는 이유: 이 앱의 의존성에 없다. 표준 라이브러리만으로 충분하고,
 * 의존성이 하나 줄면 공급망도 그만큼 줄어든다.
 */

import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { checkServerIdentity } from 'node:tls';

export interface PinnedResponse {
  status: number;
  headers: Record<string, string>;
  body: Uint8Array;
  truncated: boolean;
}

export interface PinnedFetchOptions {
  /** 접속할 IP. 이름을 다시 풀지 않는다 — 이 주소로만 간다. */
  address: string;
  /** 인증서 검증과 `Host` 헤더에 쓸 이름. 주소가 아니라 이름이어야 한다. */
  hostname: string;
  url: URL;
  userAgent: string;
  maxBytes: number;
  timeoutMs: number;
}

/**
 * 못박은 주소로 한 번 요청한다. 리다이렉트는 **따라가지 않는다** — 3xx 는 그대로
 * 돌려주고 다음 홉은 부르는 쪽 가드가 다시 본다.
 */
export function fetchPinned(options: PinnedFetchOptions): Promise<PinnedResponse> {
  const { address, hostname, url, userAgent, maxBytes, timeoutMs } = options;
  const secure = url.protocol === 'https:';
  const send = secure ? httpsRequest : httpRequest;
  const port = url.port !== '' ? Number(url.port) : secure ? 443 : 80;

  return new Promise<PinnedResponse>((resolve, reject) => {
    const outgoing = send(
      {
        // **이름이 아니라 주소로 간다.** 이 한 줄이 이 파일의 전부다.
        host: address,
        port,
        path: `${url.pathname}${url.search}`,
        method: 'GET',
        headers: {
          // 가상 호스팅이 동작하려면 이름이 필요하다. 주소로 접속하고 이름은 여기 싣는다.
          host: url.host,
          'user-agent': userAgent,
          accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.1',
          'accept-encoding': 'identity',
        },
        // SNI 와 인증서 검증은 **이름**으로 한다. 주소로 접속한다고 해서 인증서 검증을
        // 느슨하게 하면, SSRF 를 막으려다 중간자를 열어 주는 꼴이 된다.
        servername: secure ? hostname : undefined,
        checkServerIdentity: secure
          ? (_host: string, cert: Parameters<typeof checkServerIdentity>[1]) =>
              checkServerIdentity(hostname, cert)
          : undefined,
        timeout: timeoutMs,
      },
      (incoming) => {
        const chunks: Buffer[] = [];
        let received = 0;
        let truncated = false;

        incoming.on('data', (chunk: Buffer) => {
          if (truncated) return;
          received += chunk.byteLength;
          if (received > maxBytes) {
            // 상한을 넘었다. 앞부분만 남기고 **잘랐다는 사실을 남긴다** — 잘린 것을
            // 전부인 척하지 않는다.
            const keep = chunk.subarray(0, chunk.byteLength - (received - maxBytes));
            if (keep.byteLength > 0) chunks.push(keep);
            truncated = true;
            incoming.destroy();
            return;
          }
          chunks.push(chunk);
        });

        const finish = (): void => {
          const headers: Record<string, string> = {};
          for (const [name, value] of Object.entries(incoming.headers)) {
            if (value === undefined) continue;
            headers[name] = Array.isArray(value) ? value.join(', ') : value;
          }
          resolve({
            status: incoming.statusCode ?? 0,
            headers,
            body: new Uint8Array(Buffer.concat(chunks)),
            truncated,
          });
        };

        incoming.on('end', finish);
        // 상한에 걸려 우리가 끊은 경우다. 받은 만큼은 돌려준다.
        incoming.on('close', () => {
          if (truncated) finish();
        });
        incoming.on('error', reject);
      },
    );

    outgoing.on('timeout', () => {
      outgoing.destroy(new Error('timeout'));
    });
    outgoing.on('error', reject);
    outgoing.end();
  });
}
