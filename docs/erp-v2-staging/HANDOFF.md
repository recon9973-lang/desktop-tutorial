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

## 확정된 결정 (사용자 승인 완료 — 다시 묻지 말 것)
- **§3-D 채널계정 방식 = 통일함.** `ClientAccount.platform`을 nullable(`ClientAccountPlatform?`)로 완화하는
  마이그레이션을 넣고, 신규 채널계정 생성은 `channel-accounts.ts`(channelTypeId + 암호화) 경로로 일원화한다.
  `actions/clients.ts#addClientAccount`의 platform 기반 생성 경로는 제거 또는 이관용으로만 남긴다.
- **인증 = 이메일 매직링크 도입함.** `auth-email.ts`를 `src/server/auth.ts`로 반영한다.
  → **선행 필수**: base Prisma 스키마에 Auth.js 어댑터 모델 `Account`/`Session`/`VerificationToken`(+어댑터형 `User`)이
  있는지 확인, 없으면 어댑터 모델을 먼저 추가·마이그레이션한다. env: `AUTH_SECRET`/`EMAIL_SERVER`/`EMAIL_FROM` 필요.

## env(시크릿) — 사용자가 값 제공/설정. 각 값 준비법은 아래.
로컬은 `.env`(prisma/next가 로드), 배포는 호스팅(예: Vercel) 환경변수에 동일하게 설정.
| 변수 | 무엇 | 준비 방법 |
|---|---|---|
| `CREDENTIAL_ENC_KEY` | 채널계정 자격증명 암호화 키(32B) | 새로 생성: `openssl rand -hex 32` 결과(64자)를 값으로. **한 번 정하면 바꾸지 말 것**(바꾸면 기존 암호문 복호화 불가). |
| `AUTH_SECRET` | Auth.js 세션 서명 키 | 새로 생성: `openssl rand -base64 32` 또는 `npx auth secret`. |
| `EMAIL_SERVER` | 매직링크 발송 SMTP | 메일 발송 서비스의 SMTP 접속 문자열 `smtp://사용자:비번@호스트:포트` (예: SendGrid/Mailgun/AWS SES/Gmail SMTP). |
| `EMAIL_FROM` | 로그인 메일 발신 주소 | 위 서비스에서 인증된 발신 주소 (예: `no-reply@venom.co.kr`). |
| `KW_PROXY_URL` | 키워드 순위 프록시 URL | 신규 생성 아님 — 베놈이 이미 쓰는 네이버 키워드 프록시 엔드포인트 URL(홈페이지 레포 `api/kw-proxy`)을 넣는다. 모르면 확인 필요. |
| `DATABASE_URL` | DB 접속 | erp-v1에 이미 존재(그대로). |

## 이미 반영된 수정(부품 자체)
- `actions/_helpers.ts`: `"use server"` 제거(서버 유틸이라 정상, 빌드 차단 이슈였음).
- `actions/channel-accounts.ts`: 미사용 `Role` import 제거.
