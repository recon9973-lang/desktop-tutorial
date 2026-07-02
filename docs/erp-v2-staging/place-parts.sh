#!/usr/bin/env bash
# 베놈 ERP V2.1 부품 배치 스크립트
#
# 용도: docs/erp-v2-staging/의 부품을 marketing-agency-erp(erp-v1) 레포로 배치한다.
#   - 직접 배치 파일: 목표 경로로 복사(디렉터리 자동 생성).
#   - 병합 필요 파일(schema/기존 repository/seed/auth): 기존 파일을 덮지 않고
#     <erp-repo>/_to-merge/ 에 복사한 뒤 병합 안내를 출력한다.
#
# 사용법:
#   ./place-parts.sh <erp-repo-root>            # 실제 배치
#   ./place-parts.sh <erp-repo-root> --dry-run  # 복사 없이 계획만 출력
#
# 실행 후 반드시 ASSEMBLY.md §3(필수 수정 A~F)과 §0 체크리스트를 따를 것.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-}"
DRY="${2:-}"

if [[ -z "$DEST" ]]; then
  echo "사용법: $0 <erp-repo-root> [--dry-run]" >&2
  exit 1
fi
if [[ ! -d "$DEST" ]]; then
  echo "오류: erp-repo-root '$DEST' 디렉터리가 없습니다." >&2
  exit 1
fi
if [[ "$DRY" == "--dry-run" ]]; then
  echo "== DRY RUN (복사하지 않음) =="
fi

# 직접 배치: "staging상대경로|목표상대경로"
DIRECT=(
  "actions/_helpers.ts|src/server/actions/_helpers.ts"
  "actions/clients.ts|src/server/actions/clients.ts"
  "actions/work.ts|src/server/actions/work.ts"
  "actions/work-schedule.ts|src/server/actions/work-schedule.ts"
  "actions/channel-accounts.ts|src/server/actions/channel-accounts.ts"
  "actions/masters.ts|src/server/actions/masters.ts"
  "actions/finance.ts|src/server/actions/finance.ts"
  "actions/leave.ts|src/server/actions/leave.ts"
  "actions/reports.ts|src/server/actions/reports.ts"
  "actions/employees.ts|src/server/actions/employees.ts"
  "server/crypto.ts|src/server/crypto.ts"
  "server/tracking.ts|src/server/tracking.ts"
  "server/report-pdf.ts|src/server/report-pdf.ts"
  "server/repositories/masters.ts|src/server/repositories/masters.ts"
  "domain/finance-rules.ts|src/domain/finance-rules.ts"
  "domain/leave-rules.ts|src/domain/leave-rules.ts"
  "jobs/keyword-rank.ts|src/server/jobs/keyword-rank.ts"
  "components/ClientForm.tsx|src/components/clients/ClientForm.tsx"
  "components/ClientList.tsx|src/components/clients/ClientList.tsx"
  "components/ClientDetail.tsx|src/components/clients/ClientDetail.tsx"
  "components/CredentialField.tsx|src/components/clients/CredentialField.tsx"
  "components/WorkStatusButtons.tsx|src/components/work/WorkStatusButtons.tsx"
  "components/MasterManager.tsx|src/components/settings/MasterManager.tsx"
  "components/EmployeeSettings.tsx|src/components/settings/EmployeeSettings.tsx"
  "components/BankReconcile.tsx|src/components/finance/BankReconcile.tsx"
  "components/CalendarScheduler.tsx|src/components/calendar/CalendarScheduler.tsx"
  "components/DashboardCards.tsx|src/components/dashboard/DashboardCards.tsx"
  "components/LeavePanel.tsx|src/components/leave/LeavePanel.tsx"
  "components/ReportEditor.tsx|src/components/reports/ReportEditor.tsx"
  "app-routes/clients-page.tsx|src/app/(erp)/clients/page.tsx"
  "app-routes/report-pdf-route.ts|src/app/api/reports/[id]/pdf/route.ts"
  "tests/crypto.test.ts|tests/server/crypto.test.ts"
  "tests/finance-leave-rules.test.ts|tests/domain/finance-leave-rules.test.ts"
)

# 병합 필요: "staging상대경로|_to-merge하위경로|병합대상 설명"
MERGE=(
  "prisma/schema-additions.prisma|prisma/schema-additions.prisma|prisma/schema.prisma 에 신규 6모델 + 주석 필드추가 병합 (ASSEMBLY §3-A)"
  "prisma/seed-masters.ts|prisma/seed-masters.ts|prisma/seed.ts 에 병합 또는 'tsx prisma/seed-masters.ts' 단독 실행"
  "server/repositories/clients-v2.ts|src/server/repositories/clients-v2.ts|src/server/repositories/clients.ts 에 export 병합"
  "server/repositories/work-v2.ts|src/server/repositories/work-v2.ts|src/server/repositories/work.ts 에 export 병합"
  "server/auth-email.ts|src/server/auth-email.ts|src/server/auth.ts 교체 검토 (Auth.js 어댑터 모델 확인, ASSEMBLY §3 인증)"
)

place() { # src_rel  dest_rel
  local s="$SRC/$1" d="$DEST/$2"
  if [[ ! -f "$s" ]]; then echo "  ! 누락: $1" >&2; return; fi
  echo "  $1  ->  $2"
  if [[ "$DRY" != "--dry-run" ]]; then
    mkdir -p "$(dirname "$d")"
    cp "$s" "$d"
  fi
}

echo
echo "== 직접 배치 (${#DIRECT[@]}개) =="
for row in "${DIRECT[@]}"; do
  IFS='|' read -r s d <<< "$row"
  place "$s" "$d"
done

echo
echo "== 병합 필요 → _to-merge/ 로 복사 (${#MERGE[@]}개, 기존 파일 미변경) =="
for row in "${MERGE[@]}"; do
  IFS='|' read -r s sub desc <<< "$row"
  place "$s" "_to-merge/$sub"
  echo "      ↳ 병합: $desc"
done

# ASSEMBLY.md도 참고용으로 함께 배치
place "ASSEMBLY.md" "_to-merge/ASSEMBLY.md"

cat <<'NOTE'

== 배치 후 필수 절차 (ASSEMBLY.md 참조) ==
  1. _to-merge/ 의 5개 파일을 대상 파일에 손으로 병합 (특히 schema 주석 필드추가 §3-A)
  2. env 설정: CREDENTIAL_ENC_KEY, KW_PROXY_URL, (이메일 로그인 시) AUTH_SECRET/EMAIL_SERVER/EMAIL_FROM
  3. npm: next-auth @auth/prisma-adapter nodemailer / -D vitest tsx  (playwright devDep 확인)
  4. 필수 수정 확인: §3-B(Role 런타임 enum), §3-C(getIndustryTree flat), §3-D(ClientAccount 생성경로)
  5. pnpm prisma migrate dev --name v2_1_structure
  6. tsx prisma/seed-masters.ts
  7. pnpm prisma generate && pnpm build && pnpm vitest run
  8. UI 배선 (ASSEMBLY §4) → 커밋 → PR
NOTE
echo "완료."
