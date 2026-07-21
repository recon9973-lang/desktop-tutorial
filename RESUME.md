# RESUME — 다음 세션 이어가기 (2026-07-20 s02 마감)

> 새 세션은 이 파일을 **가장 먼저** 읽고 여기서 이어간다. 상세는 `docs/session-logs/2026-07-20-s02.md`, 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)
- **자동블로그 카드뉴스 파이프라인 완성** — 기존 90글 교체 + **신규글 자동 카드뉴스**(`BLOG_IMAGE_MODE=card` + `tools/cardgen` + `.github/workflows/render-blog-cards.yml`). 실운영 `auto(card)` 커밋으로 자동 작동 확인. **범위: 자동발행 글만**(정적 개념글 12개는 실사진 유지). PR #193·#194.
- **비만클리닉 컨설팅 Artifact** 제작(달서구 진천역, 마운자로>위고비 데이터 반영).
- **SEO 무료진단기 정밀 감사·실측 강화** — PSI 로딩 단축(#195), NXT 벤치마크(보안헤더+정적속도 #196, 키워드+검색량 #197), 키워드 추출 정확도(#198), robots.txt 소프트404 오탐(#199), sitemap·favicon·JSON-LD 실측 + PSI 무한'측정중' 수정(#200). seo-engine 캐시 **v2.0.3**.

## 바로 이어갈 작업 (우선순위)
1. **[핵심] 키워드 발굴기 경량 MVP** — 분석 완료, 구현 대기.
   - 목표: `대구한의원`·`대구북구한의원`·`대구교통사고한의원`·`대구통증치료`·`대구다이어트한의원` 같은 **실사용 키워드** 도출. (현재 진단 카드는 제목추출 "대구 한의원" 수준)
   - 방법: ① 지역계층 데이터(시·구·역 JSON) ② 진료과별 증상·시술 사전 ③ 붙여쓰기 조합 생성기 ④ **네이버 검색광고 API로 검색량·경쟁 검증·랭킹**(`lib/naver-searchad.fetchKeywordTool` 보유) ⑤ 자동완성 확장(`lib/keyword-research.js` 보유).
   - MVP 범위: 대구 등 타깃 1~2 지역 + 주요 진료과 → **신규 `api/keyword-discover`** + 진단 결과 '핵심 키워드' 카드 연동.
   - 이미 있는 것: 검색광고·자동완성 API, 진료과·지역 입력. **새로 만들 것: 지역계층 JSON + 증상사전 + 조합·랭킹 로직.**

## 대기/차단 (사용자 액션 · 이월)
- GSC env 입력·Redeploy → `/api/health` `hasGSC:true` 확인.
- 디자인 스튜디오 `marketing-agency-erp` erp-v1 PR 허락.
- misojin v3 → Google Drive 업로드(Drive MCP 불안정).

## 주의·제약 (반드시)
- **브랜치**: 작업 `claude/session-review-prep-an0to9`, 라이브 `main`(venom-new-site 자동배포). 파이프라인: implement→검증(node --check·기능테스트)→commit→PR→squash-merge→`git checkout -B <branch> origin/main`→force-with-lease.
- **비밀키 값·모델 ID**를 커밋/PR/코드/문서/채팅에 넣지 않는다. 커밋 트레일러 준수.
- SEO 진단 로직 수정 시 **캐시 버전(`seo-engine.js?v=`) 올리기**. 엔진 변경은 Playwright 기능테스트로 검증.
- 자동블로그 정적 글(_AI_HERO 12개)은 실사진 유지 — 카드뉴스로 바꾸지 말 것.

## 참고
- 이번 세션 상세 `docs/session-logs/2026-07-20-s02.md` · 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`.
