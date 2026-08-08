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

export interface ReportVersionRow {
  readonly report_id: string;
  readonly version_number: number;
  readonly title_ko: string;
  readonly audience: string;
  readonly generated_at: string;
  readonly content_hash: string;
  /** 엔진이 이 버전에 허용한 내보내기 형식 — 화면은 이 목록에 있는 것만 그린다. */
  readonly export_formats: readonly string[];
  readonly measurement_window_start: string | null;
  readonly measurement_window_end: string | null;
}

export async function listReportVersions(
  reportId: string,
): Promise<ConsoleOutcome<readonly ReportVersionRow[]>> {
  return callConsoleApi(
    `/api/reports/${encodeURIComponent(reportId)}/versions?page_size=200`,
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

/* ── 발행된 버전 본문 ─────────────────────────────────────────────── */

/**
 * 숫자 하나, 또는 **숫자가 없다는 명시**.
 *
 * `value` 가 `null` 인 것과 `0` 인 것은 정반대의 사실이다 — 못 쟀다와 쟀는데 0이다.
 * 그래서 화면은 `value` 를 직접 포맷하지 않고 서버가 준 `display` 를 그대로 쓴다.
 * 스키마가 그렇게 못박아 두었다: *"모든 화면·내보내기가 동일하게 출력하는 표기입니다."*
 * 화면이 따로 포맷하면 같은 버전이 화면과 내려받은 파일에서 다르게 보인다.
 */
export interface ReportValue {
  readonly display: string;
  readonly value: number | null;
  readonly unit: string;
  readonly status: string;
  readonly status_ko: string;
  readonly reason_ko: string | null;
  readonly source: string;
}

export interface ReportMetric {
  readonly metric_key: string;
  readonly label_ko: string;
  readonly section: string;
  readonly note_ko: string;
  readonly value: ReportValue;
}

export interface ReportAction {
  readonly rank: number;
  readonly title_ko: string;
  readonly why_ko: string;
  readonly owner_ko: string;
  readonly severity: string;
  readonly domain: string;
}

/** 판정하지 못한 검사. **감추지 않는다** — 빼면 문서가 실제보다 튼튼해 보인다. */
export interface ReportUnmeasured {
  readonly check_id: string;
  readonly title_ko: string;
  readonly status: string;
  readonly status_ko: string;
  readonly reason_ko: string | null;
  readonly domain: string;
}

/** 이 문서가 무엇을 어떻게 쟀는지. 숫자 옆에 늘 함께 나가야 하는 것들이다. */
export interface ReportDisclosure {
  readonly scope_ko: string;
  readonly coverage_ko: string;
  readonly confidence_ko: string;
  readonly measured_at_ko: string;
  readonly methodology_ko: string;
  readonly rank_prediction_notice_ko: string;
  readonly lines_ko: readonly string[];
}

/** 한 독자를 위한 한 판. 셋이 같은 모양이라 화면이 하나로 그린다. */
export interface ReportAudienceView {
  readonly audience: string;
  readonly audience_ko: string;
  readonly title_ko: string;
  readonly summary_ko: string;
  readonly status_ko: string | null;
  readonly metrics: readonly ReportMetric[];
  readonly top_actions: readonly ReportAction[];
  readonly unmeasured_checks: readonly ReportUnmeasured[];
  readonly changes_ko: readonly string[];
  readonly reverification_ko: readonly string[];
  readonly disclosure: ReportDisclosure;
}

export interface ReportVersionDetail {
  readonly report_id: string;
  readonly version_number: number;
  readonly title_ko: string;
  readonly generated_at: string;
  readonly content_hash: string;
  readonly measurement_window_start: string | null;
  readonly measurement_window_end: string | null;
  readonly disclosures_ko: readonly string[];
  readonly views: {
    readonly executive: ReportAudienceView;
    readonly marketing: ReportAudienceView;
    readonly developer: ReportAudienceView;
  };
}

/**
 * 발행된 버전 하나의 **본문**.
 *
 * 지금까지 화면에는 목록·내보내기·공유 링크만 있었다. 본문을 보려면 파일로
 * 내려받아야 했다 — 서버에는 처음부터 이 창구가 있었는데 부르는 곳이 없었다
 * (`docs/audit/2026-08-08-server-ui-gap.md` §A-3).
 */
export async function readReportVersion(
  reportId: string,
  versionNumber: number,
): Promise<ConsoleOutcome<ReportVersionDetail>> {
  return callConsoleApi(
    `/api/reports/${encodeURIComponent(reportId)}/versions/${versionNumber}`,
  );
}
