# 베노미 라이브 실측 런북 (RUNBOOK)

> 6대 진단을 **실제 데이터로** 돌리는 운영 절차. 코어 로직은 검증 완료(오프라인 68 assert + 렌더/엔드포인트 E2E). 남은 건 **키 설정 + 실행**뿐.

> ⚠️ Claude 웹/원격 세션(샌드박스)에선 아웃바운드 프록시가 `api.searchad.naver.com` 등을 차단하고 node 직접호출이 프록시 터널을 타지 않아 **풀 실측이 불가**합니다. 아래는 **프록시가 없는 Vercel(또는 로컬)** 기준입니다.

---

## 1. 환경변수 (Vercel → Settings → Environment Variables)

| 차원 | 키 | 없으면 |
|---|---|---|
| 병원 탐지·로컬(플레이스/블로그/뉴스) | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | 탐지 실패 → 부분 진단 |
| 광고(검색량·경쟁도) | `NAVER_AD_API_KEY`, `NAVER_AD_SECRET`, `NAVER_AD_CUSTOMER_ID` | ads `unconfigured` |
| SEO(속도) | `PSI_KEY` | seo `unavailable` |
| GEO 실측(1개↑) | `PERPLEXITY_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | geo `unconfigured` |
| 직원 게이팅(운영 시) | `VENOMI_WHITELIST` = 직원 botUserKey 쉼표목록 | open(개발) |
| 카톡 카드 웹링크 | `VENOMI_SITE_BASE` = `https://<배포도메인>` | 링크 숨김 |

> 모든 키는 선택적으로 동작(부분 성공). 없는 차원은 **수치를 지어내지 않고** status로 표기.

## 2. 배포

```bash
# 브랜치 프리뷰 배포 or main 병합(자동 배포)
git push -u origin claude/hospital-seo-geo-chatbot-4wqobs
# Vercel: 브랜치 프리뷰 URL 확인 (Deployments 탭)
```

## 3. 스모크 테스트 (배포 후)

```bash
BASE="https://<배포도메인>"   # 예: 프리뷰 URL

# 상태·키 설정 확인
curl -s "$BASE/api/hospital-bot" | jq

# 6대 진단(GEO 제외 light) — 실제 병원명
curl -s "$BASE/api/hospital-bot?hospital=대구 수성구 OO치과" | jq '.summary, .seo.score100, .local, .ads.keywords[0]'

# GEO 실측 포함(느림, 20~30초)
curl -s "$BASE/api/hospital-bot?hospital=대구 수성구 OO치과&geo=1" | jq '.geo'

# 웹 리포트(브라우저)
open "$BASE/hospital-bot/report.html?hospital=대구 수성구 OO치과"
```

기대: `summary.grade` 산정, `seo.score100` 숫자, `local.blog.total` 실수치, `ads.keywords[]` 실검색량, `geo.status:"done"`(키 있을 때) 또는 `unconfigured`.

## 4. 카카오 오픈빌더 연결

1. 채널 챗봇(오픈빌더) → **폴백 블록**에 스킬 연결, URL `"$BASE/api/hospital-bot"` (POST).
2. 블록 **콜백 사용 ON**(느린 진단 타임아웃 방지).
3. 직원 1회 발화 → 로그에서 `userRequest.user.id`(botUserKey) 확보 → `VENOMI_WHITELIST` 등록 → enforced 잠금.
4. 발화 테스트: `대구 수성구 OO치과` → 종합 카드 / `OO치과 geo` → AI검색 실측 / `상담` → CTA.

## 5. 로컬 실측(대안)

```bash
cd venom-wordpress/preview
NAVER_CLIENT_ID=.. NAVER_CLIENT_SECRET=.. \
NAVER_AD_API_KEY=.. NAVER_AD_SECRET=.. NAVER_AD_CUSTOMER_ID=.. \
PSI_KEY=.. PERPLEXITY_API_KEY=.. \
node hospital-bot/test/run.js --live "대구 수성구 OO치과"
```

## 6. 트러블슈팅

- **ads `unconfigured`**: 검색광고 3종 키 확인. 403이면 `NAVER_AD_SECRET` 재입력(base64 디코딩 없이 원문).
- **seo `unavailable`**: `PSI_KEY` 확인. 429는 PSI 일일 한도 → 잠시 후 재시도.
- **geo `unconfigured`**: AI 엔진 키 1개 이상 필요. Gemini는 무료 모델 폴백 내장.
- **병원 탐지 실패**: 지역+정식명칭으로 재시도(`대구 수성구 OO치과`).
- **카톡 5초 타임아웃**: 블록 콜백 ON 필수(느린 진단은 ack 후 callbackUrl 전송).
</content>
