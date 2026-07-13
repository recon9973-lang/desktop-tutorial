# Google Search Console (GSC) 실측 연동 — 설정 가이드

VENOM 진단기가 **실제 검색 성과(클릭·노출·CTR·순위·대표 검색어)**를 붙이려면 GSC 서비스계정 연동이 필요합니다.
코드(`lib/search-console.js`)는 이미 완성돼 있고, **자격증명만 넣으면** 켜집니다. 없으면 조용히 강등(정적 SEO 결과만).

## 왜 필요한가
- 네이버 OpenAPI는 로컬 색인 한계로 순위/노출을 정확히 못 줍니다 → **구글 실측치는 GSC만 진짜 데이터**.
- 진단 리포트의 "구글 색인 0건" 같은 항목도 GSC 연결 시 실제 수치로 대체됩니다.

## 1) Google Cloud 서비스계정 만들기
1. [Google Cloud Console](https://console.cloud.google.com) → 프로젝트 선택/생성
2. **APIs & Services → Library → "Search Console API" 사용 설정(Enable)**
3. **APIs & Services → Credentials → Create Credentials → Service account**
4. 생성된 서비스계정 → **Keys → Add key → JSON** → 키 파일(.json) 다운로드
   - 이 JSON 안의 `client_email`(예: `venom-gsc@프로젝트.iam.gserviceaccount.com`)을 기억.

## 2) Search Console 속성에 서비스계정 추가 (필수)
1. [Search Console](https://search.google.com/search-console) → **속성 추가**
   - `venom-new-site.vercel.app` (또는 `sc-domain:도메인`)을 등록하고 소유 확인 → **sitemap.xml 제출**
2. 해당 속성 → **설정 → 사용자 및 권한 → 사용자 추가**
   - 위 서비스계정 `client_email`을 **"전체" 또는 "제한"** 권한으로 추가
   - ⚠️ 이 단계를 빼먹으면 토큰은 발급돼도 쿼리가 403.

## 3) Vercel 환경변수 설정
Vercel → 해당 프로젝트 → Settings → Environment Variables. **둘 중 하나**로 자격증명 제공:

| 방식 | 변수 |
| :-- | :-- |
| A (권장·간단) | `GSC_SERVICE_ACCOUNT_JSON` = 다운로드한 JSON 파일 **전체 내용** |
| B (분리) | `GSC_CLIENT_EMAIL` + `GSC_PRIVATE_KEY` (PEM, 줄바꿈은 `\n` 이스케이프 허용) |

공통 필수:
- `GSC_SITE_URL` = 등록한 속성 값. 예: `https://venom-new-site.vercel.app/` 또는 `sc-domain:venom-new-site.vercel.app`

> ⚠️ 비밀키 값은 **코드/문서/채팅에 절대 넣지 않습니다.** Vercel 환경변수에만.

## 4) 연결 확인
- `GET /api/health` 응답의 **`hasGSC: true`** 면 자격증명 인식됨.
- `GET /api/growthops?module=gsc` → 설정 시 최근 28일 클릭·노출·CTR·대표 검색어. 미설정이면 `configured:false` 안내.
- 데이터는 GSC 특성상 **2~3일 지연**됩니다(빈 결과 ≠ 오류).

## 오프라인 검증(자격증명 없이 로직 점검)
```
npm run test:gsc     # RS256 서명 왕복 + 파싱/설정 로직 19케이스
```

## 코드 위치
- 라이브러리: `lib/search-console.js` (JWT RS256 → OAuth 토큰 → Search Analytics, 외부 의존성 0)
- 사용처: `api/growthops.js`(`gsc` 모듈), `hospital-bot/lib/diagnose.js`(연결 고객 실측), `api/health.js`(설정 여부 표시)
- 테스트: `scripts/test-search-console.js`
