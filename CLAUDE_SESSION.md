# 베놈 홈페이지 작업 세션 인수인계

## 프로젝트 기본 정보

- **저장소**: `recon9973-lang/desktop-tutorial`
- **배포 URL**: `https://desktop-tutorial-chi-peach.vercel.app/`
- **배포 방식**: Vercel 자동 배포 (`main` 브랜치 push 시)
- **출력 디렉토리**: `venom-wordpress/preview/` (vercel.json `outputDirectory`)
- **작업 브랜치**: `main` 직접 push (claude/ 브랜치는 더 이상 사용 안 함)

---

## 프로젝트 구조

```
desktop-tutorial/
├── venom-wordpress/preview/       ← Vercel 웹루트 (여기 파일만 서빙됨)
│   ├── index.html                 ← 메인 SPA (전체 페이지 포함)
│   ├── admin.html                 ← 관리자 페이지
│   ├── llms.txt                   ← AI 인용용 사이트 설명
│   ├── robots.txt                 ← 크롤러 설정
│   ├── sitemap.xml                ← 사이트맵
│   ├── images/                    ← 팀/사무실 사진
│   │   ├── Lee jae-hoon_profile.jpeg   ← 이재훈 대표
│   │   ├── Kim bo-hyeong_profile.jpeg  ← 김보형 총괄이사
│   │   ├── Seo min-goo_profile.png     ← 서민구 영업이사
│   │   └── office.jpeg                 ← 사무실 사진
│   └── content/images/            ← 자동발행 포스트 이미지 저장 위치
├── api/
│   ├── generate-post.js           ← 포스트 생성 API
│   ├── publish-post.js            ← 발행/삭제 API
│   ├── cron-daily-posts.js        ← 자동발행 크론 (매일 00:00)
│   └── posting-settings.js        ← 발행 설정
├── lib/
│   ├── post-generator.js          ← GPT로 포스트 생성
│   ├── image-generator.js         ← DALL-E 이미지 생성 → WebP 변환 → GitHub 저장
│   ├── sitemap-builder.js         ← 사이트맵 자동 갱신
│   ├── github-store.js            ← GitHub API로 JSON 저장
│   └── medical-ad-validator.js    ← 의료광고법 검증
├── scripts/
│   └── convert-to-webp.js         ← 로컬 이미지 WebP 변환 스크립트
├── .github/workflows/
│   └── convert-webp.yml           ← images/ 폴더 push 시 WebP 자동 변환
├── package.json                   ← sharp 의존성 포함
├── vercel.json                    ← 보안헤더·캐시·함수 설정
└── robots.txt                     ← (루트에도 있지만 실제 서빙은 preview/ 내 파일)
```

---

## 주요 CSS 변수 (index.html)

```css
--p: #533afd          /* 브랜드 보라 */
--bd: #1c1e54         /* 브랜드 다크 */
--ink: #0d253d
--ink2: #273951
--mute: #64748d
--soft: #f6f9fc
--border: #e3e8ee
--r12: 12px
--r16: 16px
```

---

## 완료된 작업 목록

### 1. Lucide 아이콘 교체 (admin.html)
- 사이드바·대시보드의 모든 이모지를 Lucide Icons SVG로 교체
- CDN: `https://unpkg.com/lucide@latest/dist/umd/lucide.min.js`
- `lucide.createIcons()` DOMContentLoaded에서 초기화

### 2. 회사소개(About) 페이지 전면 개편 (index.html `#pg-about`)
구성 순서:
1. 히어로: "병원이 잘 되어야 우리도 존재합니다" + 8초 철학
2. 철학 3분할 (Trust / Behavior / Emotion)
3. 회사 정보 2컬럼 (왼쪽: 정보 카드들 / 오른쪽: stats카드 + 해시태그)
4. 연혁 타임라인 (2022~2025)
5. 리더십 3컬럼 그리드
6. 핵심 가치 5개 (01~05)

### 3. Stats 카드 → 사무실 사진 배경으로 교체
- `office.jpeg`를 배경으로, 보라색 그라디언트 오버레이 적용
- 숫자: 300%, 98%, 230%, 900+

### 4. 팀 사진 교체 (leadership 섹션)
- 이재훈 대표: `Lee jae-hoon_profile.jpeg`
- 서민구 영업이사: `Seo min-goo_profile.png`
- 김보형 총괄이사: `Kim bo-hyeong_profile.jpeg`

**주의**: 이전에 seomingu.jpeg / bohyeong.jpeg 파일이 있었는데 사람이 바뀌어 있어서 올바른 파일명 파일로 교체함

### 5. 푸터 SNS 아이콘 추가
- 텍스트 링크 → SVG 아이콘 버튼 9개로 교체
- 아이콘: 네이버블로그, 인스타그램, 유튜브, 링크드인, 네이버카페, 페이스북, 티스토리, 핀터레스트, 스레드
- 스타일: 연보라 원형 배경 + 보라색 아이콘, hover 시 진한 보라 + 흰색

**중요**: `.footer` CSS가 `background:#fff`(흰색)이므로 아이콘 색상은 반드시 `fill:var(--p)`(보라색) 사용. `fill:#fff`로 하면 안 보임

### 6. WebP 자동 변환 시스템

#### GitHub Actions (`.github/workflows/convert-webp.yml`)
- `main` 브랜치의 `venom-wordpress/preview/images/**` 변경 시 자동 실행
- `sharp`로 jpg/jpeg/png → webp (quality 85) 변환
- 변환된 파일 자동 커밋 push

#### 자동발행 이미지 (lib/image-generator.js)
- DALL-E `response_format: 'b64_json'`으로 직접 받음 (별도 다운로드 없음)
- `sharp`로 WebP 변환 후 GitHub 저장
- **파일명**: 포스트 제목 기반 slug (예: `치과-임플란트-마케팅.webp`)

### 7. SEO / LLMs.txt / AI 인용 최적화

#### llms.txt (`venom-wordpress/preview/llms.txt`)
- ChatGPT·Claude·Perplexity 등 AI가 사이트 개요·서비스·인용 허용 범위 인식
- `/llms.txt`로 접근 가능

#### OG·Twitter 이미지 추가 (index.html `<head>`)
```html
<meta property="og:image" content="...office.jpeg">
<meta name="twitter:image" content="...office.jpeg">
```

#### vercel.json 보안·캐시 헤더
- 보안: `X-Frame-Options`, `X-Content-Type-Options`, `HSTS`, `Referrer-Policy`, `Permissions-Policy`
- 이미지·WebP·CSS·JS 장기 캐시: `max-age=31536000 immutable`

#### sitemap.xml 자동 갱신 (lib/sitemap-builder.js)
- cron 실행 시 발행된 포스트 URL 자동 포함
- `venom-wordpress/preview/sitemap.xml`로 GitHub 업데이트

#### Article JSON-LD (lib/post-generator.js)
- 자동발행 포스트마다 Article 스키마 자동 삽입
- `datePublished`, `author`, `publisher` 포함

#### robots.txt 보강 (`venom-wordpress/preview/robots.txt`)
- 추가된 AI 크롤러: CCBot, Applebot-Extended, YouBot, ChatGPT-User
- `LLMs:` 필드 등록

---

## 현재 미완료 / 추가 가능 작업

| 항목 | 설명 |
|------|------|
| 김보형·서민구 SNS 채널 URL | 푸터 아이콘 중 일부 `javascript:void(0)` 상태 |
| Review/AggregateRating 스키마 | 별점 신뢰 시그널 없음 |
| hreflang | 현재 단일 언어 (낮은 우선순위) |
| 포스트 개별 HTML 페이지 | SPA 동적 렌더링이라 크롤러가 포스트별 메타 수집 불가 |

---

## 이미지 Raw URL 패턴

```
https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/venom-wordpress/preview/images/[파일명]
```

예:
- `Lee%20jae-hoon_profile.jpeg`
- `Kim%20bo-hyeong_profile.jpeg`
- `Seo%20min-goo_profile.png`
- `office.jpeg`

---

## Git 작업 시 주의사항

1. **반드시 `main` 브랜치에서 작업** — Vercel은 main만 배포
2. `venom-wordpress/preview/` 안에 있는 파일만 웹에서 접근 가능
   - `robots.txt`, `sitemap.xml`, `llms.txt` 모두 이 폴더 안에 있어야 함
   - 루트의 `robots.txt`, `sitemap.xml`은 Vercel이 서빙 안 함
3. 이미지 파일명에 공백 있으면 URL에서 `%20` 인코딩 필요
4. git config 설정:
   ```bash
   git config user.email noreply@anthropic.com
   git config user.name Claude
   ```

---

## 환경 변수 (Vercel에 설정 필요)

| 변수 | 용도 |
|------|------|
| `OPENAI_API_KEY` | GPT 포스트 생성 + DALL-E 이미지 |
| `GITHUB_TOKEN` | 포스트·이미지 GitHub 저장 |
| `ADMIN_SECRET` | 관리자 페이지 인증 |
| `GITHUB_OWNER` | `recon9973-lang` |
| `GITHUB_REPO` | `desktop-tutorial` |
| `GITHUB_BRANCH` | `main` |
