import { callConsoleApi, type ConsoleOutcome } from './console-api';

/**
 * 브랜드 식별 — 고객이 **자기가 누구인지** 말하는 자리.
 *
 * `identity_strength` 가 이 화면의 요점이다. `INSUFFICIENT` 인 브랜드는 AI 답변 속
 * 언급이 **전부 검수 대기로 넘어간다** — 흔한 상호를 이름만으로 이 업체라고 말할 수
 * 없기 때문이다. 등록 화면이 그 사실을 말하지 않으면, 사용자는 관측을 돌려 놓고
 * "왜 다 보류지" 를 나중에 묻게 된다.
 */

export interface Brand {
  readonly id: string;
  readonly entity_key: string;
  readonly display_name: string;
  readonly is_own_brand: boolean;
  readonly aliases: readonly string[];
  readonly own_domains: readonly string[];
  readonly address_terms: readonly string[];
  readonly phone_numbers: readonly string[];
  readonly distinguishing_terms: readonly string[];
  /** SUFFICIENT | PARTIAL | INSUFFICIENT — 측정이 되느냐. */
  readonly identity_strength: string;
  readonly name_is_generic: boolean;
  /** 무엇을 더 넣으면 측정이 되는지 — 효과가 큰 순서로. */
  readonly gaps_ko: readonly string[];
}

export interface ProjectBrands {
  readonly ours: Brand | null;
  readonly competitors: readonly Brand[];
  /** 자사 브랜드가 없으면 GEO 관측이 실행되지 않는다. */
  readonly can_observe: boolean;
  /**
   * 우리 쪽만 잘 적혀 있을 때의 경고.
   *
   * 그 상태의 점유율은 **실제 노출 차이가 아니라 등록 정보 차이**를 보여준다 —
   * 경쟁사 언급이 더 자주 검수 대기로 떨어져 분자에서 빠지기 때문이다.
   */
  readonly asymmetry_ko: readonly string[];
}

export const STRENGTH_LABELS_KO: Record<string, string> = {
  SUFFICIENT: '측정 가능',
  PARTIAL: '정보 부족',
  INSUFFICIENT: '측정 불가',
};

export function strengthLabel(value: string): string {
  return STRENGTH_LABELS_KO[value] ?? value;
}

export async function readBrands(projectId: string): Promise<ConsoleOutcome<ProjectBrands>> {
  return callConsoleApi(`/api/projects/${encodeURIComponent(projectId)}/brands`);
}
