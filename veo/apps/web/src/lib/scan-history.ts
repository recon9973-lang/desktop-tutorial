/**
 * 공개 진단의 측정 이력 — 이 브라우저에만 남는다.
 *
 * 서버에는 아무것도 저장하지 않는다: 공개 표면은 익명 방문자의 URL 을 수집하지
 * 않는 것이 경계다. 대신 완료된 진단이 자동으로 여기 남아, 같은 주소를 다시 재면
 * 지난 점수와의 차이를 보여줄 수 있다. 직원 전체가 공유하는 이력은 콘솔(로그인)
 * 스캔의 몫이다 — 그쪽은 DB 에 남고 조직 구성원이 함께 본다.
 *
 * 이 파일은 앱에서 웹 스토리지를 만질 수 있는 **유일한** 모듈이다
 * (test/token-never-reaches-the-client.test.ts 가 강제한다). 그래서 여기에는
 * 어떤 인증·공유 식별자도 들어올 수 없다 — 저장되는 것은 아래 다섯 필드가 전부고,
 * 같은 시험이 이 파일에 그런 단어가 등장하지 않는 것까지 본다.
 */

export interface HistoryEntry {
  readonly url: string;
  readonly kind: 'SEO' | 'GEO';
  readonly score: number | null;
  readonly band: string | null;
  readonly at: string;
}

const KEY = 'veo-scan-history';

export const HISTORY_LIMIT = 50;

/** 시험 환경(jsdom)에는 웹 스토리지가 없다 — 그때는 프로세스 메모리로 대신한다. */
let memoryFallback: string | null = null;

function storedText(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return memoryFallback;
  }
}

function persistText(value: string): void {
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    memoryFallback = value;
  }
}

/**
 * React 가 구독하는 외부 스토어. 스냅숏은 내용이 바뀔 때만 새 배열이 된다 —
 * useSyncExternalStore 는 참조가 바뀌면 다시 그리므로, 매번 새로 파싱하면 무한
 * 렌더가 된다.
 */
let snapshot: HistoryEntry[] | null = null;
const listeners = new Set<() => void>();

const EMPTY: readonly HistoryEntry[] = [];

export function subscribeHistory(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getHistorySnapshot(): readonly HistoryEntry[] {
  snapshot ??= readHistory();
  return snapshot;
}

/** 서버 렌더에는 브라우저 스토리지가 없다 — 항상 빈 목록으로 그려 hydration 을 맞춘다. */
export function getServerHistorySnapshot(): readonly HistoryEntry[] {
  return EMPTY;
}

export function readHistory(): HistoryEntry[] {
  try {
    const parsed: unknown = JSON.parse(storedText() ?? '[]');
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (entry): entry is HistoryEntry =>
        typeof entry === 'object' &&
        entry !== null &&
        typeof (entry as HistoryEntry).url === 'string' &&
        typeof (entry as HistoryEntry).at === 'string',
    );
  } catch {
    return [];
  }
}

export function writeHistory(entries: readonly HistoryEntry[]): void {
  const bounded = entries.slice(0, HISTORY_LIMIT);
  persistText(JSON.stringify(bounded));
  snapshot = bounded;
  for (const listener of listeners) {
    listener();
  }
}

export function resetHistoryForTests(): void {
  memoryFallback = null;
  snapshot = null;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // 스토리지가 없는 환경이면 메모리만 비우면 된다.
  }
}
