/**
 * 채점 명세를 **읽어서 보여 주는** 쪽. 명세를 정의하는 쪽이 아니다.
 *
 * 이 파일에는 한때 발행된 명세 목록이 손으로 적혀 있었다. 두 줄, 둘 다 1.0.0. 그동안
 * 엔진은 SEO 를 1.6.0 까지, GEO 를 1.2.0 까지 발행했고 화면은 그 개정 내내 옛 버전을
 * 현재라고 말했다. 아무것도 깨지지 않았다 — 두 목록을 맞춰 보는 것이 없었기 때문이다.
 *
 * 그래서 명세 목록도 심각도 목록도 여기 두지 않는다. 타입은 `@veo/api-client` 가 OpenAPI
 * 계약에서 생성한 것을 그대로 쓰고, 값은 엔진이 준다. 여기 남은 것은 **받은 것을 어떻게
 * 배열해 보일지**뿐이며, 그중 어느 것도 새 사실을 만들지 않는다.
 *
 * 가중치·심각도 계수 같은 숫자는 여기에도, 화면 어디에도 두지 않는다.
 */
import type { SeverityTermPayload, SpecSummary } from '@veo/api-client';

export type ScoringSpecSummary = SpecSummary;
export type SeverityTerm = SeverityTermPayload;

export function specLabel(spec: ScoringSpecSummary): string {
  return `${spec.spec_id} ${spec.version}`;
}

/** 명세 ID 하나의 이력. 지금 쓰는 판 하나와, 지나간 판들. */
export interface ScoringSpecFamily {
  readonly specId: string;
  readonly domain: string;
  /** 엔진이 `is_current` 로 지목한 판. 없으면 발행본이 없다는 뜻이다. */
  readonly current: ScoringSpecSummary | null;
  /** 최근 것부터. */
  readonly superseded: readonly ScoringSpecSummary[];
}

/**
 * 명세 ID 별로 묶는다.
 *
 * **버전 번호를 비교하지 않는다.** 어느 판이 현재인지는 엔진이 `is_current` 로 알려
 * 주고, 순서도 엔진이 준 순서(오래된 것부터)를 뒤집어 쓸 뿐이다. 여기서 semver 를 다시
 * 해석하기 시작하면 "지금 쓰는 판" 의 뜻이 두 곳에 생기고, 둘이 갈라져도 화면은 태연히
 * 한쪽 답을 말한다 — 처음에 이 파일을 틀리게 만든 것이 정확히 그것이었다.
 */
export function bySpecFamily(
  specs: readonly ScoringSpecSummary[],
): readonly ScoringSpecFamily[] {
  const order: string[] = [];
  const grouped = new Map<string, ScoringSpecSummary[]>();

  for (const spec of specs) {
    const seen = grouped.get(spec.spec_id);
    if (seen === undefined) {
      order.push(spec.spec_id);
      grouped.set(spec.spec_id, [spec]);
    } else {
      seen.push(spec);
    }
  }

  return order.map((specId) => {
    const versions = grouped.get(specId) ?? [];
    const current = versions.find((spec) => spec.is_current) ?? null;
    const newest = versions[versions.length - 1];
    return {
      specId,
      domain: current?.domain ?? newest?.domain ?? specId,
      current,
      superseded: versions.filter((spec) => !spec.is_current).reverse(),
    };
  });
}
