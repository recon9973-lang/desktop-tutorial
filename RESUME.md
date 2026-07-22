# RESUME — 다음 세션 이어가기 (2026-07-22 s04 마감)

> 새 세션은 이 파일을 **가장 먼저** 읽고 여기서 이어간다. 상세는 `docs/session-logs/2026-07-22-s04.md`, 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)
- **SEO 진단 추론항목 실측화 완료(#216)** — `markTri()`로 저자/조직/연락처/엔티티는 마크업 실측만 통과, 본문 단어 정황은 '확인 필요' 강등. seo-engine **v2.1.8**.
- **GEO 도구 실측 중심 재편(#217·#218)** — 온페이지 준비도 막대(중복) 제거, `📘 가이드` 유지. 막대 자리에 **메인 키워드 4개 AI(ChatGPT·Gemini·Claude·Perplexity) 실제 질의** 실측 파트 신설(인용/언급/미노출/측정불가 + 원문·인용출처 ✓우리 + 노출 요약). 병원명·질문 자동 프리필. `runGeoAeo`/`_geoAeoCell`/`_geoAeoFinish`/`_GEO_AI4`/`_geoCtx`.
- **스키마/JSON-LD 층위 정리(#219·#220)** — telephone=schema.org 속성임을 명확화하고 조직 스키마 하위(└)로 귀속, `구조화 데이터 JSON-LD 형식`을 별도 항목으로 신설. 총점 100 유지.
- **체크리스트 사라짐 버그 수정(#221)** — 리터럴 `<script>` 미이스케이프 주입 → `_geoAttr` 이스케이프. 17항목 전부 렌더.

## 바로 이어갈 작업 (우선순위)
> **명시적으로 지시된 다음 작업 없음.** 아래는 후보/여력 항목. 새 세션은 사용자 신규 오더를 우선한다.
1. (여력) GEO 실측 파트 **라이브 스모크 테스트** — 배포 반영 후 실제 병원 URL로 4엔진 실측이 정상 동작하는지 사용자와 함께 1회 확인(egress 차단으로 에이전트 단독 확인 불가).
2. (여력) 메인 키워드 질문 자동추정 사전(`_regs`/`_deps` in `runGEO`) 확장 — 현재 주요 도시+대표 진료과만. 구 단위·세부 진료과 보강 여지.
3. (여력) SEO 남은 추론항목 = 콘텐츠 구조 임계값(소제목·문단·스캔)뿐 — DOM 실측이라 '추정 기준' 라벨만 유지 중. 추가 실측화는 불필요(이미 정직).

## 대기/차단 (사용자 액션 · 이월)
- **#36** GSC env 입력·Redeploy → `/api/health` `hasGSC:true` 확인.
- **#37** 디자인 스튜디오 `marketing-agency-erp` erp-v1 PR 허락.
- **#40** misojin v3 → Google Drive 업로드(Drive MCP 불안정).

## 주의·제약 (반드시)
- **브랜치**: 작업 `claude/session-review-prep-an0to9`, 라이브 `main`(venom-new-site 자동배포). 파이프라인: implement→검증(node 구문 + Playwright 기능테스트)→commit→PR→squash-merge→`git checkout -B <branch> origin/main`→force-with-lease.
- **비밀키 값·모델 ID**를 커밋/PR/코드/문서/채팅에 넣지 않는다. 커밋 트레일러 준수(Co-Authored-By: Claude Opus 4.8 / Claude-Session).
- **캐시**: GEO 도구는 `index.html`(no-cache)이라 새로고침 즉시 반영. **seo-engine.js 로직 변경 시에만** `?v=` 올림(현재 **v2.1.8**). 엔진 변경은 Playwright 기능테스트로 검증.
- **실측 원칙**: 실측(파싱·실제 AI 답변) > 추론(정규식·임의계수) > **통계 날조 금지**. GEO 실측·관리자 AI 매트릭스는 동일 `_INSIGHTS?type=aeo&engine=` 소스.
- **HTML 주입 주의**: 체크 항목 문자열에 코드 예시(`<script>` 등)를 넣을 땐 반드시 `_geoAttr` 이스케이프(그 버그로 #221 발생).
- egress: 컨테이너에서 vercel.app 라이브 직접 확인 불가(프록시 403). 소스+Playwright로 검증, 라이브는 사용자 새로고침 확인.
- 자동블로그 정적 글(_AI_HERO 12개)은 실사진 유지 — 카드뉴스로 바꾸지 말 것.

## 참고
- 이번 세션 상세 `docs/session-logs/2026-07-22-s04.md` · 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`.
- GEO 도구 핵심 함수: `runGEO`/`renderGEOResult`/`runGeoAeo`(모두 `venom-wordpress/preview/index.html`). SEO 엔진: `venom-wordpress/preview/seo/seo-engine.js`.
