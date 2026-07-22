# RESUME — 다음 세션 이어가기 (2026-07-20 s03 마감)

> 새 세션은 이 파일을 **가장 먼저** 읽고 여기서 이어간다. 상세는 `docs/session-logs/2026-07-20-s03.md`, 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)
- **키워드 발굴기 경량 MVP 완료(#202)** — 제목추출("대구 한의원") → 실사용 키워드(대구한의원·대구북구한의원·대구교통사고한의원·대구통증치료·대구다이어트한의원). `data/regions-kr.json`+`data/dept-modifiers.json`+`lib/keyword-discover.js`+`api/keyword-discover.js`, 회귀 24건 통과.
- **SEO 종합 점수 100점 가중 모델(#203)** — content28·tech26·trust14·search12·writing10·security10=100, 속도(CWV)는 +α 별도. 진단 결과 가독성(사이즈·컬러) 개선.
- **'정밀필요'→'확인 필요' 정직화(#204)** — 설명·수정코드 추가, pending을 분모에 0점 유지(부풀림 버그 수정). seo-engine 캐시 **v2.1.1**.
- **추론기반 측정 감사 완료(보고만)** — 실측 vs 추론 분류·권고 전달, 코드 반영은 미승인(TODO #45).

## 바로 이어갈 작업 (우선순위)
1. **[선택·후속] 추론기반 항목 '추정' 배지 + 실측 승격** (TODO #45, 사용자 승인 대기)
   - 대상: `hasAuthor`(정규식), `hasOrg`/`hasContact`, `hasEntity`(extLinks≥2), 콘텐츠 임계값(longContent·hasSubheads·paraOk·hasScan), `usesNextGen`(html-wide `.webp`), `isSPA`/`renderSuspect` — 모두 `seo-engine.js`.
   - ① '추정' 배지로 실측과 구분 ② 실측 승격(WebP→img src만, author/org→마크업 우선, entity→sameAs) ③ 콘텐츠 임계값 '추정 기준' 라벨.
   - 반영 시 seo-engine 캐시 버전 올리고 Playwright 기능테스트로 검증.
2. (여력) 키워드 발굴기 실사용 피드백 반영 — 지역/진료과 사전 확장.

## 대기/차단 (사용자 액션 · 이월)
- GSC env 입력·Redeploy → `/api/health` `hasGSC:true` 확인.
- 디자인 스튜디오 `marketing-agency-erp` erp-v1 PR 허락.
- misojin v3 → Google Drive 업로드(Drive MCP 불안정).

## 주의·제약 (반드시)
- **브랜치**: 작업 `claude/session-review-prep-an0to9`, 라이브 `main`(venom-new-site 자동배포). 파이프라인: implement→검증(node --check·기능테스트)→commit→PR→squash-merge→`git checkout -B <branch> origin/main`→force-with-lease.
- **비밀키 값·모델 ID**를 커밋/PR/코드/문서/채팅에 넣지 않는다. 커밋 트레일러 준수.
- SEO 진단 로직 수정 시 **캐시 버전(`seo-engine.js?v=`) 올리기**(현재 v2.1.1). 엔진 변경은 Playwright 기능테스트로 검증.
- 자동블로그 정적 글(_AI_HERO 12개)은 실사진 유지 — 카드뉴스로 바꾸지 말 것.

## 참고
- 이번 세션 상세 `docs/session-logs/2026-07-20-s03.md` · 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`.
