# 베노미(Venomi) — 병원명 한 줄 진단 봇

> 병원명만 넣으면 SEO·GEO·네이버 로컬·광고·의료광고법을 한 번에 진단하는 AI 코워커.
> 기획: [`PLAN.md`](./PLAN.md) · 시각 기획안은 세션 Artifact 참조.

## 현재 상태 — P0 코어 엔진 + 카카오 연동(#2) 완료

병원명 → **6대 진단서 JSON** 오케스트레이터 + **카카오 오픈빌더 스킬 서버**(직원 화이트리스트·5초 콜백 대응)를 구현했습니다.

```
hospital-bot/
├── PLAN.md                기획서 v2 (내부 우선 확정)
├── README.md              (이 파일)
├── lib/
│   ├── diagnose.js        ★ 코어 오케스트레이터 — diagnose(병원명) → 진단서
│   ├── naver-openapi.js   병원 탐지·로컬(플레이스/블로그/뉴스) 래퍼
│   ├── geo-probe.js       GEO/AI 노출 실 프로빙(preview/probe) — 인용률·SoV·감성
│   ├── kakao-format.js    진단서 → 카카오 SkillResponse + 발화 파싱
│   ├── whitelist.js       직원 발신자 게이팅(VENOMI_WHITELIST)
│   ├── compete.js         경쟁사 비교(동네 순위표)
│   └── proposal.js        진단 → 제안서/견적 자동 초안(결정론)
├── report.html            웹 풀리포트(라이브 진단·시각화·제안서·PDF)
└── test/
    ├── run.js             코어 오프라인 검증
    ├── kakao.js           카톡 연동 오프라인 검증
    ├── geo.js             GEO 프로빙 오프라인 검증
    ├── compete.js         경쟁사 비교 오프라인 검증
    ├── proposal.js        제안서 초안 오프라인 검증
    ├── cache.js           진단 캐시 오프라인 검증
    └── smoke.sh           배포 스모크(curl)
```

재사용(기존 저장소 자산): `../lib/naver-searchad`(검색량·경쟁도), `../lib/psi`(속도·SEO), `../lib/medical-ad-validator`(금지어).

## 진단 6종

| 영역 | 소스 | 상태 |
|---|---|---|
| SEO(홈페이지) | PageSpeed | ✅ |
| 네이버 로컬(플레이스/블로그/뉴스) | 네이버 OpenAPI | ✅ |
| 광고(검색량·경쟁도·CPC) | 네이버 검색광고 키워드도구 + 입찰가 추정 | ✅ 검색량·경쟁도·CPC(모바일 2위 추정) |
| 의료광고법 스캔 | 금지어 사전 | ✅ |
| GEO/AI 노출 | ChatGPT·Perplexity·Gemini·Claude 실질의 | ✅ P1 — 인용률·SoV·감성·등급 |
| 경쟁사 비교 | 네이버 로컬 + GEO 경쟁 재활용 | ✅ P2 — 동네 순위표(블로그·뉴스·AI언급) |

## API

```
GET  /api/hospital-bot                          상태·연동키·화이트리스트 모드
POST /api/hospital-bot
  ① 순수 API:   { hospital, region? }            → 진단서 JSON(내부·테스트)
  ② 카카오 스킬: { userRequest, action, ... }     → SkillResponse v2.0
```

응답 요지(순수 API): `{ summary:{grade,urgent[]}, seo, geo, local, ads, adLaw, disclaimer }`.
모든 외부 호출은 개별 가드 — 일부 실패해도 부분 진단서가 나옵니다. **없는 수치는 지어내지 않고** status로 표기합니다.

## 카카오 오픈빌더 연동

발화(병원명) → 6대 요약 카드 + 뷰 전환 버튼(quickReplies). 상세 뷰는 발화로도 진입:
`OO치과 seo` · `OO치과 광고` · `OO치과 geo` · `OO치과 플레이스` · `OO치과 심의` · `상담`.

**5초 타임아웃 대응**: 블록에 **콜백(callback) 사용**을 켜면, 봇이 먼저 "진단 중…" ack를 보내고
진단 완료 시 `callbackUrl`로 최종 카드를 POST합니다(서버리스에서도 반환 프라미스까지 함수 유지).

**연결 순서**
1. 카카오톡 채널 챗봇(오픈빌더) 생성 → **폴백 블록**에 스킬 연결.
2. 스킬 URL: `https://<배포도메인>/api/hospital-bot` (POST).
3. 블록에서 **콜백 사용 ON**(권장) → 느린 진단도 타임아웃 없이 전달.
4. `VENOMI_WHITELIST`에 직원 `botUserKey`를 등록해 **enforced**로 잠금(미설정 시 open).

> `userRequest.user.id`(botUserKey)는 채널·봇마다 고유값입니다. 직원별로 한 번 발화시켜 로그에서 확보 후 등록하세요.

## 필요 환경변수 (Vercel)

- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` — 네이버 검색 OpenAPI(병원 탐지·로컬)
- `NAVER_AD_API_KEY` / `NAVER_AD_SECRET` / `NAVER_AD_CUSTOMER_ID` — 검색광고 키워드도구(검색량)
- `PSI_KEY` — Google PageSpeed(SEO·속도)
- `VENOMI_WHITELIST` — (선택) 직원 카카오 botUserKey 쉼표목록. 미설정 시 open(개발), 설정 시 직원만 허용.
- `VENOMI_SITE_BASE` — (선택) 웹 리포트 절대 URL 베이스(예: `https://<배포도메인>`). 설정 시 카톡 카드에 웹 리포트 링크 노출.
- `KV_REST_API_URL` / `KV_REST_API_TOKEN` — (선택) Vercel KV/Upstash. 설정 시 진단 24h 캐시(재조회 비용·지연 절감). 미설정 시 캐시 off(정상 동작).
- **GEO 실측(1개 이상)**: `PERPLEXITY_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`(또는 GOOGLE_AI_KEY) / `ANTHROPIC_API_KEY`. 미설정 시 GEO는 'unconfigured'로 표기(허위수치 없음).

## 검증

```bash
cd venom-wordpress/preview
node hospital-bot/test/run.js                       # 코어 오프라인(mock) — 20 assert
node hospital-bot/test/kakao.js                     # 카톡 연동 오프라인 — 25 assert
node hospital-bot/test/geo.js                        # GEO 프로빙 오프라인 — 18 assert
node hospital-bot/test/run.js --live "대구 수성구 OO치과"   # 실 API(키 설정 시)
```

## GEO 진단 — 2모드 (비용·지연 통제)

- **preview(종합 카드)**: AI 호출 없이 엔진 가용성·프롬프트셋만 즉시 반환.
- **probe(`geo` 명령)**: 환자 의도 프롬프트 4개 × 가용 엔진 최대 3개를 실질의 → **인용률·SoV·감성·등급**.
  브랜드 질의(병원명 직접 언급)는 인용률 부풀림 방지를 위해 기본 세트에서 제외.

## 웹 풀리포트

- 페이지: `/hospital-bot/report.html?hospital=<병원명>` (`&geo=1` → AI 검색 실측 포함).
- 라이브 진단(`GET /api/hospital-bot?hospital=..`)을 불러와 점수 바·경쟁·처방을 렌더, **인쇄→PDF 저장** 지원.
- 카톡 종합 카드에서 링크로 연결(`VENOMI_SITE_BASE` 설정 시 자동 노출).

## 경쟁사 비교(동네 순위) — opt-in

- 발화 `병원명 순위`(또는 `경쟁`), 웹 `?hospital=..&compete=1`.
- 후보 = 네이버 로컬 검색 상위 + (GEO 실측 시) AI가 대신 추천한 병원. 타깃 제외·중복 제거.
- 타깃+경쟁 최대 4곳에 대해 **블로그·뉴스 노출 + AI 언급수**만 값싸게 수집해 순위표 산출(풀 진단 N회 안 함).

## 제안서 자동 초안(P3, 트랙 B) — opt-in

- 발화 `병원명 제안서`(또는 `견적`), 웹 `?hospital=..&proposal=1`(제안서는 경쟁 데이터 자동 포함).
- 진단 gap → 베놈 서비스 매칭(SEO·GEO·콘텐츠·PR·광고·심의·경쟁) + 근거.
- **견적**: 대행 수수료는 지어내지 않고 "협의" 표기. 광고비만 실제 CPC×검색량으로
  가정(클릭률 4%)을 명시해 추정 → 월 광고비 밴드. `lib/proposal.js`.
- 웹 리포트에 제안서 섹션 렌더 + PDF 저장.

## 진단 캐시(24h)

병원+지역 기준으로 **베이스 번들·GEO 실측·경쟁 비교를 각각 24h 캐시**(Vercel KV).
드릴다운(종합→GEO→순위→제안서)에서 값싼 베이스 재계산·중복 GEO 호출을 스킵.
`report.meta.cache`로 hit 여부 노출. `?cache=0`(또는 opts.cache=false)로 강제 갱신. KV 미설정 시 자동 off.

## 다음 단계

- **제안서 운영**: 슬랙·CRM 연동, LLM 프로즈 다듬기(선택).
- **사용량·비용 모니터링**: 변동 한도 소프트 조절(트랙 B 운영).

> CPC(입찰가 추정)는 완료 — `lib/naver-searchad.fetchBidEstimate`(POST /estimate/average-position-bid/keyword). 실측 불가 환경 대비 응답 스키마 불일치 시 null로 안전 degrade. 프로덕션 첫 호출 시 실제 응답 필드(bid/estimate) 확인 권장.
</content>
