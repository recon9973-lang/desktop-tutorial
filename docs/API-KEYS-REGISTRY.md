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
> **⚠️ 이름 중복:** 코드에 `GEMINI_API_KEY`와 `GOOGLE_AI_KEY`가 혼재 → **`GEMINI_API_KEY`로 통일** 권장.

## 2. 네이버 (⚠️ 이름 정규화 최우선)

| 정규 키 이름 | 용도 | 쓰는 프로젝트 | 발급처 | 공유 | 상태 |
|-------------|------|--------------|--------|:--:|:--:|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 검색 API(블로그·웹·쇼핑) | 베놈사이트, 영양제 | developers.naver.com | 공유 | 필요 |
| `NAVER_AD_API_KEY` / `NAVER_AD_SECRET` / `NAVER_AD_CUSTOMER_ID` | 검색광고 키워드도구(검색량·연관어) | 베놈사이트, (원장님앱) | searchad.naver.com | 공유 | 필요 |
| `NAVER_CALENDAR_CLIENT_ID` / `_SECRET` | 캘린더 OAuth | ERP | developers.naver.com | 전용 | 연기 |

> **⚠️ 정규화 필수:** 검색광고 키가 코드에 **두 이름으로 혼재** — `NAVER_AD_API_KEY/SECRET/CUSTOMER_ID` **와** `NAVER_ACCESS_LICENSE/NAVER_SECRET_KEY/NAVER_CUSTOMER_ID`. **`NAVER_AD_*`로 통일**하고 나머지는 폐기.

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

> **⚠️ 정규화:** `KV_REST_API_*`와 `UPSTASH_REDIS_REST_*`는 같은 저장소 → 한 쌍으로 통일.

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

### 6.3 이름 정규화(선행 과제)
위 ⚠️ 표시 4건을 코드에서 먼저 통일: ① 네이버 검색광고 `NAVER_AD_*` ② 카카오 알림톡 방식 ③ `GEMINI_API_KEY` ④ `KV_REST_API_*`. → 정규 이름으로 통일해야 시크릿 매니저에서 중복 없이 관리 가능.

### 6.4 레지스트리 추적(값 아님)
이 문서(`API-KEYS-REGISTRY.md`)를 **키 상태 대장**으로 유지. 선택적으로 **Airtable "API Key Registry" 베이스**(이름·상태·담당·발급처·프로젝트 — 값 없음)로 옮기면 비개발자도 발급 진행 상황을 관리 가능.

---

*v1 · 2026-07-04 · 값은 절대 미기재 · 이름 정규화 4건 + 시크릿 매니저 단일화가 통합의 핵심.*
