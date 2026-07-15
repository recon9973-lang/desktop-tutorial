# GROUND · 자동발행 시스템 운영 문서

> GROUND 브랜드의 콘텐츠 자동발행 3트랙(사이트 블로그 · seokorea.org 매거진 · 배나미 인스타)과
> 베놈 ERP "인스타 관리"의 구조·운영 절차를 한 곳에 정리한 캐논 문서.
> 최종 갱신: 2026-07-15

---

## 0. 한눈에 보기 — 자동발행 3트랙

| # | 트랙 | 대상 | 메커니즘 | 무인 여부 |
|---|---|---|---|---|
| 1 | 사이트 블로그(병원) | 베놈 사이트 | `auto-publish.yml` 15분 cron → 예약 글 발행 | ✅ 완전 무인 |
| 2 | 자사 미디어 매거진 | **seokorea.org** | ERP 매거진 → 초안 크론 → 검토 → WordPress 발행 | ⚠️ 반자동 |
| 3 | 소셜 카드뉴스 | **인스타 @ground_geo** | `publish-ig.yml` 매일 21:00 KST → 5장 캐러셀 | ✅ 완전 무인 |

- 트랙 2·3은 같은 **GROUND 브랜드**(자사 미디어). 지향점: **원소스 멀티유즈**(주제 1개 → 웹 글 + 인스타 카드뉴스).
- 관제: 베놈 ERP `/magazine`(트랙2) + `/insta`(트랙3, 다계정).

---

## 1. 배나미 인스타 카드뉴스 (트랙 3)

### 1.1 페르소나 · 계정
- 계정 **@ground_geo** (IG Business ID `17841472664941872`), 페이지 GROUNDai, Meta 앱 GROUND(App ID `2008871193323648`)
- 배나미: 25세 한국인 여성, 캔디드 톤, "훅 먼저 → 정보 뒤"
- 정체성 기준 이미지: `persona-nami/nami-face.png`

### 1.2 콘텐츠 구조 — 항상 5장 캐러셀
1. **커버** — 배나미 사진(이 장만 인물) + 형광펜 훅
2. **인트로** — 개념 한 줄 + 부제(인물 없음)
3. **포인트** — 핵심 3~4가지(라임 숫자 스티커)
4. **팁** — 한 줄 강조(에메랄드 배경)
5. **CTA** — 팔로우 유도

### 1.3 이미지 · 디자인 규칙(확정)
- 배나미: **테마 단색 배경에서 직접 생성**(누끼 매팅 없이 머리카락 완벽), 날씨 맞춤 패션, **글마다 배경색·각도·표정·의상 상이**, 얼굴·정체성 보존, 프롬프트에 텍스트·로고·워터마크 없음.
- 커버: 텍스트가 인물 안 가림(훅 왼쪽), 넓은 줄간격(line-height 1.42). 콘텐츠 카드: 인물 없이 톤 통일, 인트로·포인트 세로 중앙.
- 디자인 토큰: 라임 `#C7F24E` · 에메랄드 `#12574F` · 잉크 `#14201d` · 크림 `#F4F1E8`. 형광펜 강조 + 손그림 두들.

### 1.4 제작 파이프라인(샌드박스 egress 차단 우회)
```
Higgsfield(nano_banana_2) 배나미 생성(테마 단색배경) → show_generations로 URL
 → cover-manifest.json 기록
 → build-covers.yml(러너: browser-actions/setup-chrome + fonts-noto-cjk)로 커버 합성·커밋
 → 콘텐츠 카드(2~5장)는 텍스트뿐 → 샌드박스 headless chrome로 직접 렌더·커밋
 → queue.json images[5] 반영
 → 커밋 후 git pull → 로컬 Read로 직접 QC
```
관련 파일: `persona-nami/ig/build-cover.mjs`, `publish-next.mjs`, `queue.json`, 카드 렌더러 `.claude/skills/nami-cardnews/render-content-cards.py`

### 1.5 발행 · 자동화 워크플로우(desktop-tutorial, main)
| 워크플로우 | 역할 | 주기 |
|---|---|---|
| `publish-ig.yml` + `publish-next.mjs` | 큐 다음 1건 5장 캐러셀 발행(자식 컨테이너→CAROUSEL→media_publish) 후 큐 상태 커밋 | 매일 21:00 KST + 수동 |
| `build-covers.yml` + `build-cover.mjs` | 배나미 full-bleed 커버 합성 | 수동 |
| `refresh-ig-token.yml` | `IG_TOKEN` 60일 토큰 자동 연장(fb_exchange_token) 후 시크릿 교체 | 매월 1일 |

> ⚠️ GitHub cron·workflow_dispatch는 **기본 브랜치(main)에 워크플로우가 있어야** 동작한다.

### 1.6 시크릿(등록 완료)
| 시크릿 | 용도 |
|---|---|
| `IG_TOKEN` | 발행용 장기 토큰(60일, 매월 자동 갱신) |
| `META_APP_SECRET` | 토큰 갱신용 Meta 앱 시크릿 |
| `GH_PAT` | 갱신 토큰을 시크릿에 다시 쓰기(Secrets: Read/Write, 무기한) |

### 1.7 현재 발행 상태
| 글 | 상태 |
|---|---|
| geo-01 | 발행 7/14 (단일 구버전) |
| aeo-02 | 발행 7/15 (5장 캐러셀) |
| seo-03 | 발행 7/15 (5장 캐러셀) |
| eeat-04 ~ smartblock-08 (5편) | 매일 21:00 자동 대기 |

---

## 2. 베놈 ERP "인스타 관리" (트랙 3 관제, marketing-agency-erp)

네비 **운영 > 인스타 관리** (`/insta`). GitHub 큐와 별개의 ERP 발행 경로(다계정).

| 구성 | 내용 |
|---|---|
| 모델 | `InstagramAccount`(토큰은 `tokenRef` 환경변수명만 저장, 원문 미저장) · `InstagramPost`(큐) |
| provider | `instagram-multi.ts` — 계정별 단일/캐러셀(2~10장) 발행 |
| 액션 | 계정 추가·토글 / 발행 예약(DRAFT·QUEUED) / 즉시 발행 / 삭제 |
| 크론 | `runInstagramScheduledPublish` — 예약 도래분 자동 발행. `{job:"insta-scheduled"}` |
| UI | `/insta` 페이지 + `InstaManager` |

**계정 추가 절차**: ERP `/insta` → 표시명·핸들·비즈니스ID·**토큰 환경변수명** 입력 → 실제 토큰은 Vercel 환경변수에 등록(예: `IG_TOKEN_XXX`).

---

## 3. GROUND / seokorea.org 매거진 (트랙 2, marketing-agency-erp)

- 관리자단 **"GROUND · 자사 미디어" = 매거진 모듈**. 병원 콘텐츠와 분리 트랙.
- 발행 경로: 매거진 → WordPress REST API `https://seokorea.org/wp-json/wp/v2/posts`
- 모델 `MagazinePost` (status: QUEUED → DRAFTED → REVIEWED → PUBLISHED), 커버 있으면 인스타 동시 발행 옵션.

### 흐름
```
큐(주제) → [ANTHROPIC_API_KEY] AI 초안 자동 생성(하루 소량, magazine-draft 크론)
        → 매거진에서 검토 → 발행 → [WORDPRESS_*] seokorea.org 게시
```

### 가동에 필요한 환경변수(ERP/Vercel)
| 키 | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | AI 초안 자동 생성 ON |
| `WORDPRESS_SITE_URL` | `https://seokorea.org` |
| `WORDPRESS_USER` | seokorea.org 관리자 |
| `WORDPRESS_APP_PASSWORD` | WP 애플리케이션 비밀번호 |

### 시딩(완료)
- `prisma/seed-magazine.mjs` — SEO/GEO/AEO 16주제를 QUEUED로 시딩(멱등). 빌드 파이프라인 배선 → 배포 시 빈 큐 자동 충전.

---

## 4. 지원 자동화 (ERP 백엔드)
- **llms.txt 공개 서빙**: `/portal/[token]/llms.txt` (AI 크롤러가 직접 fetch)
- **IndexNow + 사이트맵 핑**: `jobs/indexnow-submit.ts`(env 게이트, 크론 배선)
- 컴플라이언스(의료광고법)·리스크·데이터모델 정합·네이버 10채널·A/B/C 등급 등 스펙 정합화 완료.

---

## 5. 배나미 스킬
`.claude/skills/nami-cardnews/` — SKILL.md(전 과정 규칙) + render-content-cards.py. "배나미"/"그라운드 카드뉴스"로 재현.

---

## 6. 운영 런북 (자주 하는 일)

### 6.1 배나미 인스타 새 시리즈 만들기
1. 발행 시점 서울 날씨 확인(WebSearch) → 계절 룩 결정
2. Higgsfield로 글 수만큼 배나미 생성(배경색·각도·표정·룩 상이) → 위젯에서 인체·정체성 QC → URL 수집
3. `cover-manifest.json` 갱신 → `build-covers.yml` 실행(커버 합성·커밋)
4. `render-content-cards.py`로 2~5장 렌더·커밋
5. `queue.json` 5장 반영 → main 병합
6. `publish-ig.yml` 트리거(또는 매일 21:00 cron 대기)

### 6.2 인스타 토큰 만료 대비
- 자동: `refresh-ig-token.yml`이 매월 1일 자동 갱신(무기한 유지).
- 수동 재발급 필요 시: Meta 앱 → 그래프 탐색기 → 토큰 → 토큰 디버거 "액세스 토큰 연장"(60일) → `IG_TOKEN` 시크릿 교체.

### 6.3 인스타 계정 추가
- ERP `/insta`에서 계정 등록(토큰 환경변수명) + Vercel 환경변수에 실제 토큰.

### 6.4 seokorea.org 매거진 가동
- ERP 환경변수 4종(§3) 등록 → 재배포 → 큐 시딩분에서 초안 자동 생성 → 검토 → 발행.

---

## 7. 다음 단계 / 백로그
1. seokorea.org 매거진 살리기 — 키 등록 → 발행 연결 점검 → 배나미 연동(원소스 멀티유즈)
2. (선택) seokorea.org 완전 무인화(예약 자동발행 크론)
3. 원고/이미지 스튜디오 2종(원고·이미지) 병합 정리
4. (선택) ERP 3트랙 공통 관제판
