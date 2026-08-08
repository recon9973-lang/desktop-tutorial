import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from './console-api';

import type { Issue, IssueDetail } from './issues';

/**
 * 이슈를 읽고 쓰는 쪽.
 *
 * 표시에 쓰는 순수 함수들과 **파일을 갈라 놓는다.** 브라우저에서 도는 카드가 이 파일에
 * 닿으면 세션 쿠키를 읽는 코드가 브라우저 번들에 실린다 — 빌드가 그걸 잡아냈다.
 */

export async function readIssues(projectId: string | null): Promise<ConsoleOutcome<Issue[]>> {
  const query = projectId === null ? '' : `&project_id=${encodeURIComponent(projectId)}`;
  return callConsoleApi(`/api/issues?page_size=200${query}`);
}

/**
 * 상태를 옮긴다.
 *
 * 어떤 이동이 가능한지 여기서 판정하지 않는다. 거부는 엔진이 하고, 거부 문장은 **지금
 * 가능한 상태를 한국어로 이름 붙여** 돌려준다 — 그 문장을 그대로 사람에게 보인다.
 * 여기서 미리 걸러 내는 규칙을 하나라도 쓰면 표가 둘이 된다.
 */
export async function transitionIssue(
  issueId: string,
  toState: string,
): Promise<ConsoleOutcome<Issue>> {
  return callConsoleApi(`/api/issues/${encodeURIComponent(issueId)}/transitions`, {
    method: 'POST',
    body: { to_state: toState },
  });
}


export async function readIssue(issueId: string): Promise<ConsoleOutcome<IssueDetail>> {
  return callConsoleApi(`/api/issues/${encodeURIComponent(issueId)}`);
}

/** 재검사가 무엇을 다시 재야 하는지. 서버가 정하고, 화면은 그대로 보인다. */
export interface VerificationRequested {
  readonly id: string;
  readonly state: string;
  readonly state_label_ko: string;
  readonly summary_ko: string;
  readonly request: {
    readonly check_id: string;
    readonly target_urls: readonly string[];
    readonly note_ko: string;
  };
}

/** 재측정이 무엇으로 판정됐는지. **판정은 우리가 보내지 않는다.** */
export interface VerificationRecorded {
  readonly id: string;
  readonly state: string;
  readonly state_label_ko: string;
  readonly outcome: string;
  readonly reason_ko: string;
  readonly summary_ko: string;
}

/**
 * 표적 재검사를 요청한다 — 이슈를 `VERIFYING` 으로 옮긴다.
 *
 * 사이트 전체를 다시 진단하지 않는다. 무엇을 다시 재야 하는지(검사 하나와 URL 목록)를
 * 서버가 돌려준다.
 */
export async function requestVerification(
  issueId: string,
): Promise<ConsoleOutcome<VerificationRequested>> {
  return callConsoleApi(
    `/api/issues/${encodeURIComponent(issueId)}/verification-requests`,
    { method: 'POST' },
  );
}

/**
 * 재측정 결과를 반영한다 — **해결로 가는 유일한 경로.**
 *
 * 진단 실행 번호만 보낸다. 판정(`RESOLVED`/`STILL_FAILING`/`INCONCLUSIVE`)은 그 실행이
 * 남긴 검사 결과에서 서버가 도출한다. **"해결로 표시해 달라" 는 요청은 보낼 수 없다** —
 * 보낼 수 있으면 아무것도 안 고치고 대시보드만 깨끗해진다.
 */
export async function recordVerificationResult(
  issueId: string,
  scanRunId: string,
): Promise<ConsoleOutcome<VerificationRecorded>> {
  return callConsoleApi(
    `/api/issues/${encodeURIComponent(issueId)}/verification-results`,
    { method: 'POST', body: { scan_run_id: scanRunId } },
  );
}

/** 담당자를 지정한다. `null` 이면 지정을 해제한다. */
export async function assignIssue(
  issueId: string,
  userId: string | null,
): Promise<ConsoleOutcome<unknown>> {
  return callConsoleApi(`/api/issues/${encodeURIComponent(issueId)}/assignee`, {
    method: 'POST',
    body: { assigned_to: userId },
  });
}
