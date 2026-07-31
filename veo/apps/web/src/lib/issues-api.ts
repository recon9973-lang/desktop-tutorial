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
