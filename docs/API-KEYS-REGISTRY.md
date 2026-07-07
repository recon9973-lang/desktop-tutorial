# 베놈 생태계 — API 키 · 토큰 통합 레지스트리 (v1)

> **목적:** 7개 프로젝트에 흩어진 모든 API 키·토큰·시크릿을 한 곳에서 파악·정규화·관리하기 위한 레지스트리.
> **보안 원칙(절대):** 이 문서에는 **키 값을 절대 적지 않는다.** 이름·용도·발급처·상태만 관리한다. 실제 값은 §5의 시크릿 매니저에 둔다.
> DB와 분리: 시크릿은 DB가 아니라 시크릿 매니저에 저장한다 (DB엔 해시만 — 예: `ApiClient.keyHash`).

상태: `보유`=값 있음/동작 · `필요`=발급/입력 대기 · `연기`=해당 기능 연기.
공유: `공유`=한 자격증명으로 여러 프로젝트 사용 가능 · `전용`=프로젝트 전용.

---

## 1. AI / LLM

| 정규 키 이름 | 제공자·용도 | 쓰는 프로젝트 | 발급처 | 공유 | 상태 |
|-------------|------------|--------------|--------|:--:|:--:|
| `OPENAI_API_KEY` | OpenAI GPT·DALL-E·web_search | 베놈사이트, seo-generator | platform.openai.com | 공유 | 필요 |
| `PERPLEXITY_API_KEY` | Perplexity sonar (AI 노출 실측/AEO) | 베놈사이트 | perplexity.ai | 공유 | 필요 |
| `ANTHROPIC_API_KEY` | Claude (AI 노출 매트릭스 4엔진) | 베놈사이트 | console.anthropic.com | 공유 | 필요 |
| `GEMINI_API_KEY` | Google Gemini (AI 매트릭스) | 베놈사이트 | ai.google.dev | 공유 | 필요 |

> **모델 설정(값 아님, 정규화 대상):** `OPENAI_TEXT_MODEL`·`OPENAI_SEARCH_MODEL`·`OPENAI_IMAGE_MODEL`·`OPENAI_MODEL`·`PERPLEXITY_MODEL`·`ANTHROPIC_MODEL`·`GEMINI_MODEL`. 시크릿 아님 → 코드 기본값/설정으로 관리 권장.
> **✅ 코드 정규화됨:** insights.js가 `GEMINI_API_KEY || GOOGLE_AI_KEY`(정규 이름 우선 + 폴백)로 읽음. **값은 `GEMINI_API_KEY`로만 입력하면 됨** (코드 수정 불필요, 폴백은 안전망으로 유지).

## 2. 네이버 (⚠️ 이름 정규화 최우선)

| 정규 키 이름 | 용도 | 쓰는 프로젝트 | 발급처 | 공유 | 상태 |
|-------------|------|--------------|--------|:--:|:--:|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 검색 API(블로그·웹·쇼핑) | 베놈사이트, 영양제 | developers.naver.com | 공유 | 필요 |
| `NAVER_AD_API_KEY` / `NAVER_AD_SECRET` / `NAVER_AD_CUSTOMER_ID` | 검색광고 키워드도구(검색량·연관어) | 베놈사이트, (원장님앱) | searchad.naver.com | 공유 | 필요 |
| `NAVER_CALENDAR_CLIENT_ID` / `_SECRET` | 캘린더 OAuth | ERP | developers.naver.com | 전용 | 연기 |

> **✅ 코드 정규화됨:** keyword-research.js·insights.js가 `NAVER_AD_API_KEY || NAVER_ACCESS_LICENSE` 식으로 **정규 이름 우선 + 구이름 폴백**으로 읽음. **값은 `NAVER_AD_*`로만 입력**하면 됨 (코드 수정 불필요). 구이름 폴백은 안전망으로 유지, 정리는 선택.

## 3. 카카오 (⚠️ 정규화 필요)

| 정규 키 이름 | 용도 | 쓰는 프로젝트 | 발급처 | 공유 | 상태 |
|-------------|------|--------------|--------|:--:|:--:|
| `KAKAO_API_KEY` / `KAKAO_SENDER_KEY` | 알림톡 발송 | 영양제, (원장님앱 알림) | 카카오비즈니스+발송대행 | 공유 | 필요 |
| `KAKAO_TEMPLATE_RECOMMENDATION` / `_REMINDER` | 알림톡 템플릿 코드 | 영양제 | 카카오 검수 후 발급 | 전용 | 필요 |
| `NEXT_PUBLIC_KAKAO_MAP_KEY` | 카카오맵(약국 지도) | 영양제 | developers.kakao.com | 전용 | 필요 |
| `KAKAOPAY_ADMIN_KEY` | 카카오페이 결제 | ERP | 카카오페이 | 전용 | 연기 |

> **⚠️ 정규화:** 알림톡이 `KAKAO_API_KEY`(직접) vs `ALIMTALK_API_URL/KEY`(대행사) 두 방식 혼재 → 발송대행사(솔라피 등) 채택 시 **한 방식으로 통일**.

## 4. 구글 · GitHub · 저장 · 인프라

| 정규 키 이름 | 용도 | 프로젝트 | 상태 |
|-------------|------|---------|:--:|
| `PSI_KEY` | PageSpeed Insights (성능·CWV) | 베놈사이트 | 필요 |
| `GSC_SERVICE_ACCOUNT_JSON` (또는 `GSC_CLIENT_EMAIL`+`GSC_PRIVATE_KEY`) + `GSC_SITE_URL` | Search Console 순위 실측 | 베놈사이트 | 필요 |
| `GOOGLE_CALENDAR_CLIENT_ID` / `_SECRET` | 캘린더 OAuth | ERP | 연기 |
| `GOOGLE_VISION_API_KEY` | 알약 OCR | 영양제 | 연기 |
| `GITHUB_TOKEN` / `GITHUB_OWNER` / `GITHUB_REPO` / `GITHUB_BRANCH` | 콘텐츠·이미지 커밋 저장 | 베놈사이트 | 보유(가능) |
| `KV_REST_API_URL` / `_TOKEN` (= `UPSTASH_REDIS_REST_URL`/`_TOKEN`) | 방문자 분석·리더보드 | 베놈사이트 | 필요 |
| `DATABASE_URL` | PostgreSQL(Neon) | ERP, (영양제 프로덕션) | 필요 |
| `AUTH_SECRET` / `AUTH_URL` / `EMAIL_SERVER` / `EMAIL_FROM` | 인증(매직링크) | ERP | 필요 |
| `CREDENTIAL_ENC_KEY` | 자격증명 AES-256-GCM | ERP | 필요 |
| `ADMIN_SECRET` / `CRON_SECRET` | 관리자·크론 보호 | 베놈사이트 | 필요 |

> **✅ 코드 정규화됨:** analytics.js가 `KV_REST_API_URL || UPSTASH_REDIS_REST_URL`로 읽음(정규 우선 + 폴백). **값은 `KV_REST_API_*`로만 입력**하면 됨.

## 5. 결제·은행·공공데이터 (기능 연기 — 참고)

- **결제/은행(ERP, 연기):** `TOSSPAYMENTS_SECRET_KEY`, `INICIS_MID`, `KAKAOPAY_ADMIN_KEY`, `BANK_CARD_SYNC_PROVIDER/CLIENT_ID/CLIENT_SECRET`
- **공공·의료 데이터(영양제):** `DATA_GO_KR_KEY`(공공데이터포털), `MFDS_*_API_URL`(식약처·URL), `LNHPD_API_URL`, `NCBI_API_KEY`, `CLOVA_OCR_INVOKE_URL/SECRET`

---

## 6. 통합 운영 방식 (권장 — "앞으로 별도로 모아서 진행")

**원칙: 실제 값은 시크릿 매니저 한 곳(단일 진실 원천) → 각 프로젝트 배포 환경으로 동기화. 값은 절대 git·DB·이 문서에 두지 않는다.**

### 6.1 시크릿 매니저 선택
| 옵션 | 적합성 |
|------|--------|
| **Doppler** (권장) | 프로젝트/환경(dev·prod)별 그룹 + 여러 배포처 동기화 + 공유 시크릿 참조. 멀티 프로젝트에 최적 |
| **Vercel Environment Variables** | 이미 Vercel 배포 중 → 즉시 사용. 단, 프로젝트 간 공유는 수동 복제 |
| **1Password / Infisical** | 팀 열람·감사 필요 시 |

### 6.2 공유 vs 전용 분리
- **공유 그룹**(한 값 → 여러 프로젝트): `OPENAI_API_KEY`, `NAVER_CLIENT_ID/SECRET`, `NAVER_AD_*`, `PERPLEXITY/ANTHROPIC/GEMINI`, `KAKAO_*` → 시크릿 매니저의 "공유" 프로젝트에 두고 각 앱이 참조.
- **전용**: `DATABASE_URL`, `AUTH_SECRET`, `CREDENTIAL_ENC_KEY`, 템플릿 코드 등 → 앱별 분리.

### 6.3 이름 정규화 — 현황
**대부분 코드에서 이미 처리됨**(정규 이름 우선 + 구이름 폴백). 값 입력 시 **정규 이름만 사용**하면 된다.
- ✅ 네이버 검색광고 `NAVER_AD_*` — 코드 폴백 있음 (keyword-research.js·insights.js)
- ✅ `GEMINI_API_KEY` — 코드 폴백 있음 (insights.js)
- ✅ `KV_REST_API_*` — 코드 폴백 있음 (analytics.js)
- ⏳ 카카오 알림톡 — `KAKAO_API_KEY`(직접) vs `ALIMTALK_API_*`(대행사)는 **단순 이름 문제가 아니라 발송 방식 결정** → 대행사(솔라피 등) 채택 여부 결정 후 한 방식으로 확정.

즉 시크릿 매니저엔 **정규 이름으로만 값을 넣으면** 되고, 별도 코드 정규화 작업은 카카오 방식 결정만 남는다.

### 6.4 레지스트리 추적(값 아님)
이 문서(`API-KEYS-REGISTRY.md`)를 **키 상태 대장**으로 유지. 선택적으로 **Airtable "API Key Registry" 베이스**(이름·상태·담당·발급처·프로젝트 — 값 없음)로 옮기면 비개발자도 발급 진행 상황을 관리 가능.

---

*v1 · 2026-07-04 · 값은 절대 미기재 · 이름 정규화 4건 + 시크릿 매니저 단일화가 통합의 핵심.*
