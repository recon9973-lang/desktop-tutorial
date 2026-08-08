/**
 * 질문을 **어디서 가져오는가** — 화면 쪽 통로.
 *
 * 2026-08-08 까지 질문 집합 화면의 예시 질문은 **내가 지어낸 것**이었다
 * (`docs/CORRECTIONS.md`). 지어낸 문장으로 잰 노출률은 지어낸 세계의 노출률이다.
 * 이제 사람이 실제로 쓴 질문을 네이버 지식iN 에서 가져온다.
 *
 * **못 쓰는 출처도 목록에 남는다.** 구글 관련 질문은 SerpAPI 열쇠가 있어야 켜지고,
 * 없으면 `DISABLED_NO_CREDENTIAL` 로 온다. 화면은 그것을 "열쇠를 넣으면 켜집니다" 로
 * 보여준다 — 목록에서 빼면 열쇠만 넣으면 얻을 수 있었던 질문을 아무도 모른 채 지나간다.
 */

export interface CollectedQuestion {
  readonly text: string;
  readonly source: string;
  /** 원문 주소. 구글 관련 질문은 빈 문자열이다. */
  readonly url: string;
}

export interface QuestionSource {
  readonly source: string;
  readonly label_ko: string;
  /** ENABLED | DISABLED_NO_CREDENTIAL … */
  readonly state: string;
  readonly state_reason_ko: string;
  readonly questions: readonly CollectedQuestion[];
  /** 출처가 보고한 전체 건수. 가져온 개수와 다르다. */
  readonly total: number;
  readonly dropped: number;
  readonly failure_reason_ko: string | null;
  readonly notes_ko: readonly string[];
}

export interface QuestionHarvest {
  readonly query: string;
  readonly sources: readonly QuestionSource[];
  readonly total_questions: number;
  readonly note_ko: string;
}

export type HarvestOutcome =
  | { readonly ok: true; readonly harvest: QuestionHarvest }
  | { readonly ok: false; readonly message: string };

export function isUsable(source: QuestionSource): boolean {
  return source.state === 'ENABLED';
}

export async function harvestQuestions(query: string): Promise<HarvestOutcome> {
  const response = await fetch('/api/question-sources', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  const body: unknown = await response.json().catch(() => null);
  const record = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

  if (!response.ok) {
    return {
      ok: false,
      message:
        typeof record['message'] === 'string'
          ? record['message']
          : '질문을 가져오지 못했습니다.',
    };
  }
  return { ok: true, harvest: record['harvest'] as QuestionHarvest };
}
