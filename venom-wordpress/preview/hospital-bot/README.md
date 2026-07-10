# 베노미(Venomi) — 병원명 한 줄 진단 봇

> 병원명만 넣으면 SEO·GEO·네이버 로컬·광고·의료광고법을 한 번에 진단하는 AI 코워커.
> 기획: [`PLAN.md`](./PLAN.md) · 시각 기획안은 세션 Artifact 참조.

## 현재 상태 — P0 (코어 엔진 완료)

병원명 → **6대 진단서 JSON**을 만드는 오케스트레이터를 구현했습니다.
카카오 오픈빌더 연동·직원 화이트리스트(#2)는 이 위에 얹습니다.

```
hospital-bot/
├── PLAN.md                기획서 v2 (내부 우선 확정)
├── README.md              (이 파일)
├── lib/
│   ├── diagnose.js        ★ 코어 오케스트레이터 — diagnose(병원명) → 진단서
│   ├── naver-openapi.js   병원 탐지·로컬(플레이스/블로그/뉴스) 래퍼
│   └── geo-probe.js       GEO/AI 노출 진단 (P0 스텁 → P1 활성)
└── test/
    └── run.js             오프라인 검증(네트워크·키 불필요)
```

재사용(기존 저장소 자산): `../lib/naver-searchad`(검색량·경쟁도), `../lib/psi`(속도·SEO), `../lib/medical-ad-validator`(금지어).

## 진단 6종

| 영역 | 소스 | 상태 |
|---|---|---|
| SEO(홈페이지) | PageSpeed | ✅ |
| 네이버 로컬(플레이스/블로그/뉴스) | 네이버 OpenAPI | ✅ |
| 광고(검색량·경쟁도) | 네이버 검색광고 키워드도구 | ✅ (CPC는 P1) |
| 의료광고법 스캔 | 금지어 사전 | ✅ |
| GEO/AI 노출 | LLM 다중 프로빙 | ⬜ P1(현재 프롬프트셋만) |
| 경쟁사 비교 | 조립 | ⬜ P2 |

## API

```
GET  /api/hospital-bot                     상태·연동키 설정 여부
POST /api/hospital-bot { hospital, region? }  → 진단서 JSON
```

응답 요지: `{ summary:{grade,urgent[]}, seo, geo, local, ads, adLaw, disclaimer }`.
모든 외부 호출은 개별 가드 — 일부 실패해도 부분 진단서가 나옵니다. **없는 수치는 지어내지 않고** status로 표기합니다.

## 필요 환경변수 (Vercel)

- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` — 네이버 검색 OpenAPI(병원 탐지·로컬)
- `NAVER_AD_API_KEY` / `NAVER_AD_SECRET` / `NAVER_AD_CUSTOMER_ID` — 검색광고 키워드도구(검색량)
- `PSI_KEY` — Google PageSpeed(SEO·속도)

## 검증

```bash
cd venom-wordpress/preview
node hospital-bot/test/run.js                       # 오프라인(mock) — 20개 assert
node hospital-bot/test/run.js --live "대구 수성구 OO치과"   # 실 API(키 설정 시)
```

## 다음 단계

- **#2 카카오 연동**: 오픈빌더 스킬 서버(`api/hospital-bot`에 카톡 포맷터·발신자 화이트리스트 추가) + 5초 타임아웃 대응(즉답 후 채널 메시지 푸시).
- **P1 GEO**: `lib/geo-probe.js` 실 프로빙(ChatGPT·Perplexity·Gemini) → 인용률·SoV·등급.
- **CPC**: 검색광고 입찰가 추정 API 연동.
</content>
