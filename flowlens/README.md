# FlowLens

개인정보 보호형 웹 행동 분석 SaaS — **대행사(다중 고객) MVP**.
여러 고객사 웹사이트의 클릭·스크롤·체류·좌절클릭을 수집해 히트맵과 한국어 개선 리포트로 만들고,
대행사 로고가 박힌 읽기전용 링크로 고객에게 공유합니다.

> 첨부된 사업계획서(`behavior-analytics-saas-business-plan.md`)를 바탕으로
> 리서치 → 브레인스토밍 → 기획(`docs/`) → **동작하는 코드**까지 구현한 초기 코드베이스입니다.

---

## 빠른 실행

```bash
cd flowlens
npm install
npm run setup     # Prisma 생성 + DB(sqlite) 생성 + 데모 데이터 시드
npm run dev       # http://localhost:4311
```

로그인: **owner@growthlab.kr / demo1234**

데이터를 초기화하려면: `npm run db:reset`

## 화면

| 경로 | 설명 |
|---|---|
| `/` | **마케팅 랜딩페이지 + 무료 진단(진단 히트맵 인포그래픽) + 쿠키동의 배너** |
| `/privacy` · `/terms` | 개인정보처리방침 · 이용약관 (초안 템플릿) |
| `/login` · `/signup` | 로그인 / **대행사 워크스페이스 자체 가입** |
| `/billing` | **요금제·사용량** (요금제 변경, 결제는 스텁) |
| `/dashboard` | 전체 고객사·사이트 한눈에 (멀티테넌시) |
| `/sites/[id]` | 사이트 개요 지표 |
| `/sites/[id]/heatmap` | **히트맵 스튜디오**: 클릭맵 / 셀렉터 / 스크롤맵 / **제스처(탭·더블탭·줌·스와이프)** + 디바이스 필터 |
| `/sites/[id]/funnel` | **전환 퍼널** (단계별 누적 도달·이탈) |
| `/sites/[id]/compare` | **개선 전/후 비교** (최근 14일 vs 이전 14일) |
| `/sites/[id]/sessions` | 세션 목록 → 각 세션 **리플레이(재생)** |
| `/sites/[id]/sessions/[sessionId]` | 세션 리플레이 (클릭 마커 애니메이션 + 이벤트 타임라인) |
| `/sites/[id]/suggestions` | 자동 리포트 + **개선 과제 보드**(열림/진행/완료 상태 관리) |
| `/settings` | 대행사 설정 · **화이트라벨 로고 업로드** |
| `/sites/[id]/install` | 설치 스크립트 + 플랫폼별 설치(워드프레스 플러그인/Cafe24/GTM) + 공유 링크 |
| `/sites/[id]/data` | **데이터 관리**: 방문자 데이터 삭제(기간·경로·세션·전체) + 감사 로그 |
| `/share/[token]` | **화이트라벨 읽기전용 리포트** (계정 불필요) |
| `/demo` | 추적 SDK가 실제로 설치된 테스트 페이지 |

## 동작 확인 (end-to-end)

1. 로그인 → 대시보드에서 3개 사이트 지표 확인
2. 사이트 → 히트맵/개선제안 확인
3. `/demo` 페이지를 열고 클릭·스크롤 → **설치 탭의 이벤트 수가 실시간 증가**
4. 설치 탭에서 공유 링크 생성 → 새 탭에서 열면 대행사 로고 리포트

## 구조

```
public/t.js              추적 SDK (개인정보 미수집 원칙 코드화)
src/app/api/collect      이벤트 수집 API
src/lib/metrics.ts       지표 집계
src/lib/rules.ts         개선 제안 룰 엔진
src/lib/site.ts          멀티테넌시 접근 격리
prisma/schema.prisma     데이터 모델
prisma/seed.mjs          데모 데이터 생성기
docs/                    리서치 · 브레인스토밍 · 기획 문서
```

## 기술 스택

- Next.js 15 (App Router, TypeScript) — 대시보드 + 수집 API 단일 앱
- Prisma + SQLite (개발) → PostgreSQL (운영 전환은 `docs/03-기획.md` 9장 참고)
- 히트맵/차트는 외부 라이브러리 없이 Canvas/SVG 직접 구현

## 개인정보 보호 · 보안 (구현됨, 법무 검토 반영)

- 폼 입력값·비밀번호는 수집 코드 경로에 존재하지 않음
- 이메일/전화/카드/주민번호 패턴 **클라이언트 + 서버 2중 마스킹** (`lib/sanitize.ts`)
- 좌표는 상대값(0~1)만 저장, 절대 픽셀·IP 미저장
- **URL query/hash 제거**, **referrer 호스트명만** 저장, **conversion meta는 allowlist(dir)** 로 제한·민감키 차단
- **수집 API 도메인 검증**(Origin/Referer vs `Site.domain`, 로컬호스트 예외)
- **민감영역 제외**: `data-fl-ignore`/`.fl-sensitive`(수집 안 함), `data-fl-label`(안전 라벨)
- 운영 시크릿 강제(기본값이면 기동 실패)·로그인 쿠키 Secure(운영)·공유 링크 랜덤토큰+30일 만료
- **보관기간 자동 삭제**: `npm run cleanup` (운영에서 cron 등록) — 사이트별 `retentionDays` 초과 이벤트 삭제
- **추적 거부 존중**: GPC/DNT/`window.flowlens.optOut()` 감지 시 수집 완전 중단
- **방문자 데이터 삭제 도구**: `/sites/[id]/data` — 기간·경로·세션키·전체 단위 삭제(삭제요청 대응)
- **감사 로그**: 로그인·삭제·공유링크·요금제 변경 기록(같은 화면에서 열람)
- 상세 법무 정리: `docs/04-법무검토-사업내용.md`

## 추가 구현된 기능 (2차)

- **세션 리플레이** — DOM을 녹화하지 않고 수집된 이벤트를 시간순으로 재생(클릭 마커 + 스크롤 위치 + 이벤트 로그). 개인정보 안전.
- **AI 자동 리포트** (`lib/report.ts`) — 룰 엔진 결과를 고객 보고용 한국어 서술형으로 합성. 개선제안 탭·공유 리포트 상단에 표시. LLM 문장 다듬기 연결 지점은 `lib/llm.ts`(ANTHROPIC_API_KEY 설정 시 확장).
- **플랫폼별 설치** — 워드프레스는 siteKey가 박힌 전용 플러그인(`/api/sites/[id]/wp-plugin`, `flowlens-tracker.php`)을 다운로드해 설치. Cafe24/아임웹/GTM은 단계 가이드 + 복사 스니펫.

## 랜딩페이지 & 무료 진단 (획득 채널)

- 루트 `/`는 마케팅 랜딩페이지. 히어로의 **무료 진단** 입력에 URL을 넣으면 `/api/diagnose`가
  해당 페이지 HTML을 실제로 가져와(SSRF 방어 포함) HTTPS·모바일 대응·제목/메타·CTA·폼·이미지 alt·
  페이지 무게·분석툴 설치를 점검하고 점수를 냅니다.
- 결과는 **진단 히트맵 인포그래픽**(`DiagnoseHeatmap.tsx`)으로 시각화: 브라우저 목업 위에 페이지 영역(상단·첫화면·제목·CTA·콘텐츠·폼)을 문제=뜨거움(빨강)/양호=차가움(초록)으로 열지도 표시하고 "가장 뜨거운 영역"을 짚어줍니다.
- 행동 데이터(실제 클릭 히트맵·rage click·이탈·퍼널)는 추적 설치가 있어야만 알 수 있으므로 **잠금 티저**로
  보여주고 `/signup`으로 유도합니다. (사업계획서 12장 "무료 진단 랜딩" 구현)
- 진단 로직: `lib/diagnose.ts`, 위젯: `components/DiagnoseWidget.tsx` + `DiagnoseHeatmap.tsx`.

## 법무·동의 (초안)

- `/privacy`(개인정보처리방침), `/terms`(이용약관) — **초안 템플릿**. 상단에 "법률 검토 필요" 경고 배너 포함. 회사명·연락처·수탁사 등은 `[ ]`로 비워둠.
- 쿠키/행태정보 동의 배너 `CookieConsent.tsx` — 랜딩 하단 고정, 선택을 localStorage에 저장. 가입 화면에 약관·개인정보 동의 안내.
- ⚠️ 실제 오픈 전 반드시 전문가 검토 후 실제 정보로 확정할 것.

## 배포

운영 배포는 [DEPLOY.md](DEPLOY.md) 참고. 요약:
- 개발은 SQLite, 운영은 PostgreSQL (`schema.prisma`의 provider 한 줄 변경).
- **Docker Compose** (`docker compose up -d --build`) 또는 **Vercel + Neon** 중 선택.
- 추적 스크립트 `t.js`는 자신이 로드된 도메인으로 수집하므로 도메인 하드코딩 불필요.
- 산출물: `Dockerfile`, `docker-compose.yml`, `.env.production.example`.

## 결제 (토스페이먼츠)

- `/billing` → 요금제 선택 → `/billing/checkout` (토스 결제위젯) → `/billing/success`(서버 confirm) → 요금제 반영.
- 키는 환경변수(`NEXT_PUBLIC_TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`). **테스트 키**를 넣으면 실제 결제 없이 흐름을 확인, **라이브 키**로 실결제. 키가 없으면 체크아웃이 "키 설정 안내 + 개발용 적용" 상태로 표시된다.
- 서버 `lib/toss.ts`가 금액 위변조를 검증(요청 금액 == 요금제 가격)한 뒤 confirm API로 최종 승인.
- 월 자동갱신은 토스 빌링(자동결제) 추가 연동 필요 — 현재는 단건 결제로 요금제 활성화.

## 추가 구현된 기능 (3차)

- **전환 퍼널** (`getFunnel`) — 방문→스크롤25%→몰입50%→클릭/행동→전환. 각 단계는 누적 조건이라 항상 단조 감소. 최대 이탈 구간 자동 표시.
- **개선 전/후 비교** (`getComparison`) — 최근 14일 vs 이전 14일 지표를 좋은 방향 기준으로 개선/악화 색상 판정.
- **자체 회원가입** (`/signup`, `/api/auth/signup`) — 대행사 워크스페이스 + OWNER 계정 실제 생성 후 로그인.
- **요금제·사용량** (`/billing`, `lib/plans.ts`) — 현재 요금제/이번 달 세션 사용량, 요금제 변경. ⚠️ 결제는 스텁(`/api/billing/change-plan`) — 운영에서는 국내 PG/Stripe 결제 후 반영.

## MVP에서 제외 (다음 단계)

완전한 DOM 픽셀 단위 리플레이(rrweb), A/B 테스트, 실결제(PG) 연동,
GTM OAuth 자동 태그 생성, Shopify 앱, NextAuth/SSO — `docs/02-브레인스토밍.md`의 스코프 컷 참고.

## ⚠️ 운영 전 반드시 교체할 것

이 코드베이스는 **초기 MVP**입니다. 운영 전 아래를 반드시 강화하세요.

- 인증: 현재 단순 쿠키 세션 → NextAuth/OAuth + 안전한 세션 스토어
- DB: SQLite → PostgreSQL (+ 이벤트는 추후 ClickHouse 분리)
- `.env`의 `FLOWLENS_SECRET`을 안전한 랜덤 값으로 교체
- 수집 API에 rate limit / 도메인 화이트리스트 강제 / 봇 필터 강화
- 개인정보처리방침·이용약관·DPA·동의(CMP) 연동
