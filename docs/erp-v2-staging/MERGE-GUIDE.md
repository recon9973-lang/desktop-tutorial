# 병합 가이드 — `_to-merge/` 5개 파일 처리법

`place-parts.sh`가 `<erp-repo>/_to-merge/`에 넣은 5개 파일을 erp-v1 대상 파일에 합치는 정확한 절차다.
직접 배치 33개는 이 문서 대상이 아니다(복사로 끝). 병합 순서 권장: **1(schema) → 2(seed) → 3·4(repository) → 5(auth)**.

---

## 1. `prisma/schema-additions.prisma` → `prisma/schema.prisma` 【가장 중요】

### 1-a. 신규 6모델 — 파일 끝에 그대로 추가
`schema-additions.prisma`의 `model IndustryCategory` … `model CompanySetting`까지(주석 블록 이전) **전체를 복사해
`prisma/schema.prisma` 맨 끝에 붙여넣는다.** 수정 불필요.

### 1-b. 기존 5개 모델에 필드 추가 — 아래 블록을 각 모델 본문 안에 붙여넣기
schema-additions 하단의 주석은 마이그레이션에 안 잡히므로, 아래를 **실제 코드로** 해당 `model { }` 안에 넣어야 한다.
(넣지 않으면 역관계 누락으로 `prisma generate` 실패.)

**`model Client { … }` 안에 추가:**
```prisma
  industryCategoryId String?
  industryCustom     String?           // 업종 "기타" 수기 입력
  industryCategory   IndustryCategory? @relation(fields: [industryCategoryId], references: [id])

  @@index([industryCategoryId])
```

**`model WorkItem { … }` 안에 추가:**
```prisma
  parentId         String?
  sequence         Int                 @default(0)
  scheduledStart   DateTime?
  scheduledEnd     DateTime?
  estimatedMinutes Int?
  workCategoryId   String?             // WorkCategoryMaster FK (기존 category enum과 병행/이관)
  parent           WorkItem?           @relation("WorkSubtasks", fields: [parentId], references: [id])
  subtasks         WorkItem[]          @relation("WorkSubtasks")
  workCategory     WorkCategoryMaster? @relation(fields: [workCategoryId], references: [id])

  @@index([parentId])
  @@index([ownerId, scheduledStart])
  @@index([workCategoryId])
```
> 주의: `@@index([ownerId, scheduledStart])`는 base에 `ownerId` 필드가 있다는 전제(README 확인됨). 없으면 조정.

**`model ClientAccount { … }` 안에 추가:**
```prisma
  channelTypeId String?
  usernameEnc   String?      // AES-256-GCM 암호화 저장 (crypto.ts)
  passwordEnc   String?
  channelType   ChannelType? @relation(fields: [channelTypeId], references: [id])

  @@index([channelTypeId])
```
> §3-D 결정 반영: 신규 계정을 channel-accounts 경로로 일원화한다면 기존 `platform`을 nullable로 완화(`platform ClientAccountPlatform?`)하는 마이그레이션도 여기서 함께.

**`model User { … }` 안에 추가:**
```prisma
  loginHistory LoginHistory[] @relation("UserLoginHistory")
```

**`model BillingRecord { … }` 안에 추가:**
```prisma
  bankMatches BankTransaction[] @relation("BillingBankMatch")
```

### 1-c. 마이그레이션
```bash
pnpm prisma format
pnpm prisma migrate dev --name v2_1_structure
```

---

## 2. `prisma/seed-masters.ts` — 병합 불필요, 단독 실행 권장
이 파일은 자체 `PrismaClient` + `main().finally(...)`를 갖는 **독립 실행 스크립트**다. 병합하지 말고 그대로 두고 실행:
```bash
pnpm tsx prisma/seed-masters.ts
```
`prisma/seed.ts`에 합치고 싶다면, `main()` 본문(업종/카테고리/채널/정책 upsert)만 기존 seed의 `main` 안으로 옮기고
중복 `PrismaClient`/`$disconnect`는 제거한다. (권장: 단독 유지.)

---

## 3. `src/server/repositories/clients-v2.ts` → `repositories/clients.ts`
추가되는 **export는 `listClientsForUser` 하나**(내부 헬퍼 `clientScopeWhere` 포함).
- 대상 `clients.ts`에 **동명 export가 없으면**: 파일 내용을 통째로 append.
- **있으면**: 기존 `listClientsForUser`를 이 버전으로 교체(업종/색상/미수금 select가 추가된 V2). import 중복 정리.
- 확인: 이 함수가 `client.industryCategory.parent`를 select하므로 §1-b의 `Client` 필드추가가 선행돼야 한다.

## 4. `src/server/repositories/work-v2.ts` → `repositories/work.ts`
추가 export: **`getSchedulerDay`, `listWorkTree`** 두 개. 대상에 동명 함수 없으면 append, 있으면 교체.
- 확인: `scheduledStart/End`, `estimatedMinutes`, `sequence`, `parentId`, `subtasks` 사용 → §1-b의 `WorkItem` 필드추가 선행 필요.

## 5. `src/server/auth-email.ts` → `src/server/auth.ts` 【교체/결정】
이 파일은 `export const { handlers, auth, signIn, signOut } = NextAuth({…})` 로 **auth.ts를 통째로 대체**하는 형태다
(기존 Kakao provider → 이메일 매직링크).
- **선행 확인(필수):** base Prisma 스키마에 Auth.js 어댑터 모델 `Account`·`Session`·`VerificationToken`(+어댑터형 `User`)이 있어야
  `PrismaAdapter` + `session.strategy:"database"` + nodemailer provider가 동작한다. 없으면 어댑터 모델 마이그레이션 먼저.
- env: `AUTH_SECRET`, `EMAIL_SERVER`(SMTP URL), `EMAIL_FROM`.
- npm: `next-auth`(v5) `@auth/prisma-adapter` `nodemailer`.
- 이메일 로그인을 아직 채택하지 않을 거면 이 파일 병합은 **보류**하고 나머지(1~4)만 진행해도 된다.

---

## 병합 후
```bash
pnpm prisma generate
pnpm build
pnpm vitest run          # tests/server/crypto, tests/domain/finance-leave-rules
```
그 다음 ASSEMBLY.md §3-B(`Role` 런타임 enum)·§3-C(`getIndustryTree` flat)·§4(UI 배선) 확인 → 커밋 → PR.
```
