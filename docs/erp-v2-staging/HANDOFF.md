# HANDOFF — erp-v1 조립 세션용 (다음 세션이 읽는 문서)

이 문서는 **`marketing-agency-erp`(erp-v1) 레포로 스코프된 새 세션**에서 조립을 즉시 시작하기 위한 인수인계다.
부품과 가이드는 `desktop-tutorial` 레포의 `docs/erp-v2-staging/` (브랜치 `claude/venom-erp-assembly-246d6s`)에 있다.

## 목표
베놈 ERP V2.1 부품 39개를 erp-v1에 배치·병합·마이그레이션하고, 빌드+테스트를 통과시킨 뒤 PR.

## 이 폴더 문서 지도
- `ASSEMBLY.md` — 전체 조립(배치표, env/npm, 필수수정 A~F, UI↔액션 배선)
- `MERGE-GUIDE.md` — 병합 5개 파일의 붙여넣기-레디 상세 절차(특히 schema)
- `place-parts.sh` — 부품 자동 배치 스크립트
- (본 문서) HANDOFF.md — 실행 순서 요약

## 실행 순서
1. 이 브랜치의 `docs/erp-v2-staging/`를 erp-v1 작업트리로 가져온다(또는 desktop-tutorial을 clone해 참조).
2. 배치: `bash docs/erp-v2-staging/place-parts.sh <erp-repo-root> --dry-run` 로 계획 확인 → 실제 실행.
   - 직접 배치 33개는 목표 경로로, 병합 5개는 `<erp-repo>/_to-merge/`로 들어간다.
3. `_to-merge/MERGE-GUIDE.md` 대로 5개 병합 (순서: schema → seed → repository 2개 → auth).
4. env 설정: `CREDENTIAL_ENC_KEY`(32B hex64/base64), `KW_PROXY_URL`, (이메일 로그인 시) `AUTH_SECRET`/`EMAIL_SERVER`/`EMAIL_FROM`.
5. npm: `next-auth @auth/prisma-adapter nodemailer` + `-D vitest tsx` (playwright devDep 확인).
6. 마이그레이션 → 시드 → 빌드 → 테스트:
   ```
   pnpm prisma migrate dev --name v2_1_structure
   pnpm tsx prisma/seed-masters.ts
   pnpm prisma generate && pnpm build && pnpm vitest run
   ```
7. ASSEMBLY.md §3-B(Role 런타임 enum)·§3-C(getIndustryTree flat) 확인, §4대로 UI 배선.
8. 커밋 → PR.

## 사용자에게 받아야 할 결정/입력
- **§3-D 결정**: `ClientAccount.platform`을 nullable로 완화하고 신규계정은 channel-accounts 경로로 일원화할지.
- **인증**: 이메일 매직링크 로그인을 이번에 도입할지(도입 시 Auth.js 어댑터 모델 `Account`/`Session`/`VerificationToken` 존재 확인 필요). 미도입 시 `auth-email.ts` 병합 보류.
- env 실제 값(시크릿)은 사용자가 제공/설정.

## 이미 반영된 수정(부품 자체)
- `actions/_helpers.ts`: `"use server"` 제거(서버 유틸이라 정상, 빌드 차단 이슈였음).
- `actions/channel-accounts.ts`: 미사용 `Role` import 제거.
