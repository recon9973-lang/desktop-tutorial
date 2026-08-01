import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from './console-api';

import type { ScoringSpecSummary, SeverityTerm } from './scoring';

/**
 * 채점 명세 등록부를 엔진에서 읽는다.
 *
 * 표시용 순수 함수(`./scoring`)와 파일을 갈라 놓는 이유는 이슈 쪽과 같다 — 이 파일은
 * 세션 쿠키를 읽으므로 브라우저 번들에 실리면 안 된다.
 *
 * **실패했을 때 손으로 적은 목록으로 물러서지 않는다.** 그렇게 하면 엔진이 죽어 있는
 * 동안 화면은 아무 일 없다는 얼굴로 옛 버전을 보여 주게 되고, 그것이 애초에 이 등록부를
 * 손으로 적어 두었을 때 벌어진 일이다. 못 읽었으면 못 읽었다고 말한다.
 */

function malformed<T>(): ConsoleOutcome<T> {
  return { ok: false, reason: 'SERVER_ERROR', message: null, retryAfterSeconds: null };
}

export async function readScoringSpecs(): Promise<ConsoleOutcome<ScoringSpecSummary[]>> {
  const found = await callConsoleApi<{ readonly specs: ScoringSpecSummary[] } | null>(
    '/api/scoring/specs',
  );
  if (!found.ok) return found;
  const specs = found.data?.specs;
  return Array.isArray(specs) ? { ...found, data: specs } : malformed();
}

export async function readSeverities(): Promise<ConsoleOutcome<SeverityTerm[]>> {
  const found = await callConsoleApi<{ readonly severities: SeverityTerm[] } | null>(
    '/api/scoring/severities',
  );
  if (!found.ok) return found;
  const severities = found.data?.severities;
  return Array.isArray(severities) ? { ...found, data: severities } : malformed();
}
