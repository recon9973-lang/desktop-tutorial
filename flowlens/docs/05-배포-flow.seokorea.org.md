# 실행 런북 — flow.seokorea.org 배포 + good-tour.kr 추적

작성일: 2026-07-15
목표: FlowLens를 `https://flow.seokorea.org`에 올리고, **good-tour.kr**(울릉도여행 굿투어)의 방문자 행동을 추적한다.

> ⚠️ 아래 A·B·C는 **계정·권한이 필요한 작업**이라 사업자(사장님)가 직접 하셔야 합니다.
> 각 단계는 제가 옆에서 값·명령을 정확히 알려드리며 함께 진행합니다.

---

## 0. good-tour.kr 사전 점검 (완료)
- 추적 가능: HTTPS·모바일 대응·예약 폼 있음, 정상 HTML 사이트(네이버 등 불가 플랫폼 아님).
- **이미 Google Tag Manager 설치됨: `GTM-PVL5HQDD`** → 사이트 코드 수정 없이 **GTM으로 설치**가 가장 쉬움.
- 전제: good-tour.kr은 사장님이 소유/운영하거나 추적 설치 권한이 있어야 함(방문자 고지·개인정보 처리방침 반영 필요).

---

## A. flow.seokorea.org 배포 (호스팅 — 사장님 계정)

> 코드 준비는 완료했습니다(빌드 검증 통과). **로컬은 SQLite 유지, Vercel 배포 시 자동으로 Postgres로 전환·테이블 생성**되도록 `vercel-build` 스크립트를 넣어뒀습니다. 그래서 사장님은 **스키마 변경·db push를 직접 하지 않아도 됩니다.**

### 관리형(추천) — Vercel + Neon
1. **Neon**(neon.tech) 무료 가입 → 프로젝트 생성 → `DATABASE_URL` 복사(끝에 `?sslmode=require`).
2. 이 `flowlens` 폴더를 GitHub에 올리고 **Vercel**에서 Import (Root Directory를 `flowlens`로).
3. Vercel 환경변수 등록:
   - `DATABASE_URL` = 1번 Neon 값
   - `FLOWLENS_SECRET` = 긴 랜덤 (예: `openssl rand -hex 32`)
   - `NEXT_PUBLIC_TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY` = (결제는 나중에, 비워도 앱 동작)
4. **Deploy** — 빌드 시 `vercel-build`가 Postgres로 전환 + 테이블 생성(db push) + 빌드까지 자동.
5. 배포 성공 후 Vercel → **Settings → Domains → `flow.seokorea.org` 추가.**

---

## B. flow.seokorea.org DNS 등록 (도메인 — 사장님 계정)

seokorea.org DNS 관리 화면(가비아/후이즈/Cloudflare 등)에서 레코드 추가:

| 유형 | 이름(호스트) | 값 |
|---|---|---|
| **CNAME** | `flow` | Vercel이 알려주는 값 (예: `cname.vercel-dns.com`) |

- 자체 서버(VPS)라면: **A** 레코드, 이름 `flow`, 값 = 서버 공인 IP.
- HTTPS 인증서는 Vercel/Caddy가 자동 발급. 전파에 몇 분~수십 분.
- 확인: 브라우저에서 `https://flow.seokorea.org` 접속 → FlowLens 랜딩이 보이면 성공.

---

## C. good-tour.kr 추적 설치 (GTM — 사장님 GTM 계정)

### C-1. FlowLens에서 사이트 등록 (배포된 flow.seokorea.org에서)
1. `https://flow.seokorea.org/signup` 으로 대행사 계정 생성(또는 로그인).
2. 고객사 "굿투어" → 사이트 "good-tour.kr" 등록 → **siteKey 발급**.
3. 설치 탭에서 스크립트 확인:
   ```html
   <script async src="https://flow.seokorea.org/t.js" data-site="발급된_siteKey"></script>
   ```

### C-2. Google Tag Manager(GTM-PVL5HQDD)에 태그 추가
1. GTM 접속 → 컨테이너 **GTM-PVL5HQDD** 선택.
2. **태그 → 새로 만들기 → 태그 유형: 맞춤 HTML** → 위 `<script>` 붙여넣기.
3. **트리거: All Pages(모든 페이지)** 선택.
4. **저장 → 제출/게시.**
5. good-tour.kr 방문 → FlowLens 설치 탭의 "이벤트 수집" 수가 늘면 성공. 며칠이면 히트맵·퍼널이 쌓임.

---

## 배포 후
- **cron 등록**: 매일 `npm run cleanup`(보관기간 초과 이벤트 삭제) — Vercel Cron 또는 서버 crontab.
- **개인정보처리방침**: good-tour.kr에 "행동 분석 도구(FlowLens) 사용" 고지 문구 반영(법무 검토 후).
- 결제(토스 라이브 키)는 유료화 시점에.

## 지금 필요한 결정
1. 호스팅: **Vercel(추천)** vs 자체 서버.
2. good-tour.kr 설치: **GTM(GTM-PVL5HQDD) 접근 가능** 여부.
3. seokorea.org DNS 관리 위치(가비아/Cloudflare 등).
