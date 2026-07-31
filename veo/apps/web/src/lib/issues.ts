/**
 * 진단이 찾아낸 문제들.
 *
 * 이 화면이 지켜야 하는 규칙은 엔진 쪽 상태 기계가 정한 것과 같다: **이슈는 재측정이
 * 닫는다. 사람이 '했음'을 눌러서 닫지 않는다.** 담당자가 "고쳤다"고 보고한 것은
 * `FIX_CLAIMED` 이고 그것은 여전히 **열린 상태**다.
 *
 * 그래서 여기에는 "해결 몇 건" 같은 합계를 만들지 않는다. 그 숫자를 만드는 순간
 * 수정 보고와 재측정 확인이 한 칸에 섞이고, 그 결과는 **바뀐 것 없는 사이트 위의
 * 깨끗한 대시보드**다.
 *
 * 어떤 버튼을 그릴지도 여기서 정하지 않는다. `human_transitions` 는 엔진이 상태
 * 표에서 뽑아 준 목록이다. 화면이 자기 목록을 들고 있으면 두 표가 갈라지고, 갈라짐은
 * 늘 같은 방향이다 — 기계가 거부하는 이동에 버튼이 생기고, 누른 사람은 도구가
 * 고장 났다고 결론짓는다.
 */

export interface HumanTransition {
  readonly to_state: string;
  readonly label_ko: string;
  readonly reason_ko: string;
}

export interface Issue {
  readonly id: string;
  readonly project_id: string;
  readonly check_id: string;
  readonly severity: string;
  readonly state: string;
  readonly state_label_ko: string;
  readonly is_open: boolean;
  readonly title_ko: string;
  readonly business_impact_ko: string | null;
  readonly affected_url_count: number;
  readonly remediation_owner: string;
  readonly recurrence_count: number;
  readonly summary_ko: string;
  readonly human_transitions: readonly HumanTransition[];
}

/** 조치 담당 직군. 엔진이 코드로 주므로 표시할 말은 여기서 붙인다. */
export const OWNER_LABELS_KO: Record<string, string> = {
  DEVELOPER: '개발',
  MARKETER: '마케팅',
  BUSINESS_OWNER: '사업 결정',
  OPERATIONS: '운영',
};

export function ownerLabel(value: string): string {
  return OWNER_LABELS_KO[value] ?? value;
}

/**
 * 심각도 정렬 순서.
 *
 * 점수 계산에는 쓰지 않는다 — 감점 계수는 채점 명세에만 있다. 이건 **줄 세우는
 * 순서**일 뿐이고, 명세에 없는 심각도가 오면 맨 뒤로 보낸다.
 */
const SEVERITY_ORDER = ['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO'];

export function severityRank(value: string): number {
  const at = SEVERITY_ORDER.indexOf(value);
  return at === -1 ? SEVERITY_ORDER.length : at;
}

/**
 * 손대야 할 것이 위로 오게 세운다.
 *
 * 재발한 것을 가장 위에 둔다. 한 번 해결로 확인됐다가 다시 나온 문제는, 같은 심각도의
 * 처음 보는 문제와 같은 무게가 아니다 — 고쳤다고 믿고 넘어간 자리가 열려 있었다는
 * 뜻이기 때문이다.
 */
export function inWorkOrder(issues: readonly Issue[]): readonly Issue[] {
  return [...issues].sort((left, right) => {
    if (left.recurrence_count !== right.recurrence_count) {
      return right.recurrence_count - left.recurrence_count;
    }
    const bySeverity = severityRank(left.severity) - severityRank(right.severity);
    if (bySeverity !== 0) return bySeverity;
    return right.affected_url_count - left.affected_url_count;
  });
}

/**
 * 재측정을 기다리는 건수.
 *
 * "고쳤다고 보고됐지만 아직 확인되지 않은" 건수다. 이 숫자를 따로 세는 이유는, 이것이
 * 조용히 사라지면 열린 문제가 해결된 것처럼 보이기 때문이다.
 */
export function claimedButUnverified(issues: readonly Issue[]): number {
  return issues.filter((issue) => issue.state === 'FIX_CLAIMED' || issue.state === 'VERIFYING')
    .length;
}
