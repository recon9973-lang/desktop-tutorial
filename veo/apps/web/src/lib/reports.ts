import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';

/**
 * 리포트 — 고객에게 나가는 문서.
 *
 * 이 화면이 지키는 규칙 하나: **숫자는 실측에서만 온다.**
 *
 * 엔진에는 진단 전체를 요청 본문으로 받는 발행 경로도 있다. 그 경로로 만든 문서의
 * 숫자는 아무도 재지 않은 값일 수 있다. 화면은 그 경로를 쓰지 않는다 — 저장된 진단
 * 실행 하나를 고르면, 그 실행이 남긴 점수·판정·근거·측정 조건으로 문서가 만들어진다.
 *
 * 발행된 버전은 고칠 수 없다. 다시 재면 새 버전이 붙고 옛 버전은 그대로 남는다 —
 * 고객에게 이미 보낸 문서가 나중에 조용히 달라지면 안 되기 때문이다.
 */

export interface ReportRow {
  readonly report_id: string;
  readonly project_id: string;
  readonly title: string;
  readonly audience: string;
  readonly created_at: string;
  /** 아직 한 번도 발행되지 않았으면 비어 있다. 감추지 않는다. */
  readonly latest_version_number: number | null;
  readonly latest_content_hash: string | null;
  readonly latest_generated_at: string | null;
}

export interface ReportableRun {
  readonly scan_run_id: string;
  readonly started_at: string | null;
  readonly status: string;
  readonly urls_collected: number;
}

export async function listReports(
  projectId: string | null,
): Promise<ConsoleOutcome<readonly ReportRow[]>> {
  const query = projectId === null ? '' : `?project_id=${encodeURIComponent(projectId)}`;
  return callConsoleApi(`/api/reports${query}`);
}

export async function listReportableRuns(
  projectId: string,
): Promise<ConsoleOutcome<readonly ReportableRun[]>> {
  return callConsoleApi(
    `/api/reports/reportable-runs?project_id=${encodeURIComponent(projectId)}`,
  );
}

export async function publishFromScan(
  scanRunId: string,
  title: string,
): Promise<ConsoleOutcome<unknown>> {
  return callConsoleApi('/api/reports/from-scan', {
    method: 'POST',
    body: { scan_run_id: scanRunId, title },
  });
}
