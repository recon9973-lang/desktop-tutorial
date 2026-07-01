# 베놈 ERP V2 — 1차 스프린트 구현 착수 패키지 (drop-in)

이 폴더의 코드는 **`recon9973-lang/marketing-agency-erp` (`erp-v1`)** 에 그대로 옮겨 넣도록 작성된 것이다.
(현재 작업 세션은 `desktop-tutorial` 레포에만 권한이 있어 ERP 레포에 직접 push할 수 없으므로 여기에 staging해 둠.)

실제 erp-v1 코드 패턴을 확인하고 맞춰서 작성했다:
- `@/server/db` 의 `db` (Prisma 싱글톤)
- `@/server/session` 의 `getCurrentUser()` → `{ id, name, email, role }`
- `@/domain/access-control` 의 `assertCanAccessClient(user, clientId, scopes, assignedMarketerId)`
- `@/domain/work` 의 `nextWorkStatus(status, action)` (actions: start/submit_for_review/approve/block/resume)
- `prisma/schema.prisma` 의 실제 컬럼명 (Client.active, WorkItem.ownerId/startedAt/completedAt 등)
- 의존성: zod ^3.24, next ^15, @prisma/client ^6 (server actions 사용)

## 배치 위치

| 이 폴더 파일 | ERP 레포 목표 경로 |
|---|---|
| `actions/_helpers.ts` | `src/server/actions/_helpers.ts` |
| `actions/clients.ts` | `src/server/actions/clients.ts` |
| `actions/work.ts` | `src/server/actions/work.ts` |
| `actions/channel-accounts.ts` | `src/server/actions/channel-accounts.ts` |
| `server/crypto.ts` | `src/server/crypto.ts` (자격증명 AES-256-GCM) |
| `prisma/schema-additions.prisma` | `prisma/schema.prisma` 에 병합 (V2.1 마이그레이션) |
| `prisma/seed-masters.ts` | `prisma/seed.ts` 병합 또는 단독 실행 (마스터 시드) |

### V2.1 적용 순서 (스프린트 0~2)
1. `schema-additions.prisma` 내용을 `prisma/schema.prisma`에 병합 → `pnpm prisma migrate dev --name v2_1_structure`
2. `crypto.ts` 배치 + `.env`에 `CREDENTIAL_ENC_KEY`(32바이트 hex64 또는 base64) 설정
3. `_helpers.ts` / `clients.ts` / `work.ts` / `channel-accounts.ts` 배치
4. `seed-masters.ts`로 업종·카테고리·채널 시드
5. `pnpm build` + 테스트 → UI 연결(`/clients`, `/work`, 설정 마스터)

## 새 세션에서 할 일 (순서)

1. ERP 레포(`marketing-agency-erp`)로 스코프된 새 세션 시작.
2. 위 3개 파일을 목표 경로에 복사.
3. **검증 체크리스트**(아래) 수행 후 빌드/테스트.
4. UI 연결: `/clients`, `/work` 화면의 버튼/폼에서 이 액션들을 호출(`formAction` 또는 클라이언트 핸들러).
5. 통과하면 커밋 → PR.

## 검증 체크리스트 (옮긴 직후 반드시 확인)

- [ ] `pnpm prisma:generate` 후 타입 에러 없는지 (`pnpm build`).
- [ ] `getCurrentUser` 반환 타입이 `{id, role}`을 포함 — access-control의 `CurrentUser`와 호환되는지.
- [ ] `db.accessScope.findMany` 필드명(`adminId`)이 스키마와 일치(확인됨).
- [ ] AuditLog 쓰기 컬럼(`beforeState/afterState` Json) 직렬화 — Decimal/Date가 들어가면 `JSON.parse(JSON.stringify())` 또는 평탄화 적용(코드에 toAuditState로 처리).
- [ ] `next/headers`의 `headers()`가 Next 15에서 async — `await headers()` 사용(코드 반영됨).
- [ ] server action 파일 최상단 `"use server"` 유지.
- [ ] `revalidatePath` 경로가 실제 라우트(`/clients`, `/work`, `/clients/[id]`)와 일치.

## 확정된 도메인 규칙 (코드 반영됨)

- **담당자 변경(`reassignMarketer`)**: 해당 거래처의 **미완 업무(WorkItem, status≠COMPLETED)만** 새 담당자로 이관. 다른 거래처/개인 업무는 그대로 둠 → "거래처 업무는 함께 이관, 개인 업무는 유지" 충족.
- **거래처 비활성화(`deactivateClient`)**: 차단 없이 `active=false`. 미수금/미완업무/계약종료 정보는 `getClientDeactivationInfo`로 읽어 UI 확인단계에 표시.
- **업무 상태전이(`changeWorkStatus`)**: 도메인 `nextWorkStatus`로만 전이. 불법 전이는 `ILLEGAL_TRANSITION` 에러.
- **첨부**: 1차는 `attachmentUrl`(외부 링크) 필드 사용.

## 미결(코드에 TODO 표기)

- 업무 상태전이 허용표는 erp-v1 `src/domain/work.ts`의 `transitionMap`을 그대로 사용(확인 완료). 추가 전이가 필요하면 거기서 확장.
- `createById`(작성자) 등 일부 선택 컬럼은 actor.id로 채움.
