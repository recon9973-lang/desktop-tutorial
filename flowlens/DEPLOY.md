# FlowLens 배포 가이드

개발은 SQLite로 즉시 실행되지만, **운영은 PostgreSQL**을 사용합니다.
아래 두 가지 방법 중 하나를 선택하세요. (초보자는 A, 관리 편의는 B 권장)

---

## 0. 공통 준비 — Postgres로 전환 (필수)

배포 전 `prisma/schema.prisma`의 provider를 한 줄 바꿉니다.

```prisma
datasource db {
  provider = "postgresql"   // 개발 sqlite → 운영 postgresql
  url      = env("DATABASE_URL")
}
```

> 추적 스크립트(`t.js`)는 **자신이 로드된 도메인**으로 데이터를 보냅니다.
> 즉 앱을 `https://app.내도메인.kr`에 배포하면, 그 도메인의 `t.js`를 심은 고객 사이트가
> 자동으로 그 서버로 수집합니다. 추적 코드에 도메인을 하드코딩할 필요가 없습니다.

---

## A. Docker Compose로 자체 서버(VPS) 배포 — 가장 빠름

VPS(예: 라이트세일, EC2, 국내 클라우드)에 Docker가 설치돼 있어야 합니다.

```bash
# 1) 코드 업로드 후 폴더로 이동
cd flowlens

# 2) 0번(Postgres provider) 적용 확인

# 3) 토스 키를 환경변수로 전달하며 실행 (DB + 앱 자동 기동)
NEXT_PUBLIC_TOSS_CLIENT_KEY=live_ck_xxx TOSS_SECRET_KEY=live_sk_xxx docker compose up -d --build

# 4) (선택) 데모 데이터 시드 — 실서비스면 생략
docker compose exec app node prisma/seed.mjs
```

- 앱: `http://서버IP:4311` → 앞단에 Nginx/Caddy로 도메인+HTTPS 연결 권장.
- `docker-compose.yml`의 `POSTGRES_PASSWORD`, `FLOWLENS_SECRET`를 **반드시 교체**하세요.
- 컨테이너 시작 시 `prisma db push`로 테이블이 자동 생성됩니다.

---

## B. Vercel(앱) + Neon(Postgres) — 관리형, 서버 관리 불필요

1. **Neon**(또는 Supabase)에서 무료 Postgres 생성 → `DATABASE_URL` 복사.
2. 이 폴더를 GitHub에 올리고 **Vercel**에서 Import.
3. Vercel 프로젝트 환경변수 등록:
   - `DATABASE_URL` (Neon 연결 문자열, `sslmode=require`)
   - `FLOWLENS_SECRET` (긴 랜덤 문자열)
   - `NEXT_PUBLIC_TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`
4. 최초 1회 스키마 생성: 로컬에서 위 `DATABASE_URL`로
   ```bash
   DATABASE_URL="<neon-url>" npx prisma db push
   ```
5. Vercel 배포 → `https://<프로젝트>.vercel.app` 접속. 이후 커스텀 도메인 연결.

> Vercel은 빌드 시 `prisma generate`가 필요합니다. `package.json`의 build 전에
> `prisma generate`가 실행되도록 Vercel 빌드 커맨드를 `prisma generate && next build`로 두거나,
> `postinstall`에 `prisma generate`를 추가하세요.

---

## ⭐ seokorea.org 서브도메인 배포 (권장 구성)

앱을 `app.seokorea.org`(또는 `flowlens.seokorea.org`)에 올립니다. 추적 스크립트는
`https://app.seokorea.org/t.js` 로 자동 제공되므로 고객사에는 이 한 줄만 설치합니다.

### 방법 B(관리형) 기준 — Vercel + Neon
1. **Neon**에서 Postgres 생성 → `DATABASE_URL` 복사.
2. 로컬에서 스키마 생성(최초 1회): `DATABASE_URL="<neon>" npx prisma db push`
3. GitHub에 올리고 Vercel Import → 환경변수 등록(`DATABASE_URL`, `FLOWLENS_SECRET`, `NEXT_PUBLIC_TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`).
4. Vercel → Settings → **Domains** → `app.seokorea.org` 추가.
5. **seokorea.org DNS**(가비아/Cloudflare 등)에 Vercel이 안내하는 레코드 추가:
   - 유형 **CNAME**, 이름 **app**, 값 **cname.vercel-dns.com** (Vercel이 표시하는 값 그대로)
   - HTTPS 인증서는 Vercel이 자동 발급.
6. 배포 후 `https://app.seokorea.org` 접속 → `/signup`으로 첫 계정 생성.

### 방법 A(자체 서버) 기준 — Docker + 도메인
- DNS: 유형 **A**, 이름 **app**, 값 **서버 공인 IP**.
- 앞단에 Caddy/Nginx로 `app.seokorea.org` → `localhost:4311` 프록시 + HTTPS 자동.

### 보관기간 자동 삭제 cron 등록
운영 서버(또는 별도 워커)에서 매일 1회 실행:
```
# crontab -e  (매일 새벽 4시)
0 4 * * * cd /path/to/flowlens && /usr/bin/npm run cleanup >> /var/log/flowlens-cleanup.log 2>&1
```
Vercel 사용 시엔 **Vercel Cron** 또는 별도 스케줄러에서 `npm run cleanup`에 해당하는 작업을 돌리세요.

### 참고
- 개발 서버는 이제 **자동 포트**를 사용합니다(고정 4311 아님). 추적 스크립트는 로드된 오리진으로 수집하므로 포트가 달라도 동작합니다.
- 크롬 확장(`extension/`)의 팝업에는 배포 도메인 `https://app.seokorea.org`를 입력합니다.

---

## 배포 후 체크리스트

- [ ] `schema.prisma` provider = postgresql
- [ ] `FLOWLENS_SECRET` 무작위 값으로 교체 (`openssl rand -hex 32`)
- [ ] 토스 **라이브** 키 등록 + 토스 개발자센터에서 도메인/리다이렉트 URL 등록
- [ ] HTTPS 적용 (추적 스크립트는 https 사이트에서 https로 전송되어야 함)
- [ ] 첫 계정 만들기(`/signup`) → 고객사·사이트 등록 → 고객 사이트에 `t.js` 설치
- [ ] 개인정보처리방침·이용약관·동의(CMP) 페이지 준비 (운영 필수)
- [ ] (권장) `prisma db push` → `prisma migrate`로 전환해 변경 이력 관리

## 결제(토스페이먼츠) 운영 메모

- 현재 결제 성공은 `successUrl → /billing/success`에서 서버가 `confirm` API로 최종 승인합니다.
- **월 구독**을 자동 갱신하려면 토스 **빌링(자동결제)** 연동이 추가로 필요합니다(현재는 단건 결제로 요금제 활성화).
- 실제 정산·세금계산서·환불 정책은 사업자 등록 및 PG 계약에 따릅니다.
