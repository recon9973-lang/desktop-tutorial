# RESUME — 다음 세션 이어가기 (2026-07-20 s01 마감)

> 새 세션은 이 파일을 **가장 먼저** 읽고 여기서 이어간다. 상세는 `docs/session-logs/2026-07-20-s01.md`, 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)
- **자동블로그 이미지 거부감 해소 완료**: AI 사진 → **볼드 카드뉴스 전면 교체**.
  - Phase 0 얼굴 제거·네거티브 강화 `#188`, Phase 0.1 화면씬 제거(깨진글자 차단) `#189`.
  - **88글/129 이미지 → jpg+webp 258개 카드뉴스 재생성** `#190`(파일명 유지 → blog-posts.json 무수정, 썸네일=히어로 통일).
  - 제작: 로컬 **Playwright + Pretendard + PIL**(API 0원). 스크립트 `scratchpad/cardgen/render.mjs`.
- **SEO 무료진단기**: 정확도 실측 → **정상**(DOMParser로 h1 카운트, 자사 홈 h1=1 통과). 사용자가 본 "H1 없음"은 JS 렌더링 외부사이트 진단 시.
  - **실패 항목 하단에 "🔧 이렇게 고치세요" 수정 코드블록 24종** 추가 `#191`(seo-engine.js v1.7.0).

## 바로 이어갈 작업 (우선순위)
1. **[핵심·TODO #31] 신규글 이미지 파이프라인을 카드뉴스로 전환**
   - 문제: 자동발행 크론(`api/cron-daily-posts.js` → `lib/image-generator.js`)은 **아직 DALL-E 사진 생성** → 새 글마다 옛 스타일 재유입, 그리드 다시 뒤섞임.
   - 권고안: **GitHub Actions**(`fetch-blog-ai.yml` 패턴)에 카드 렌더링 붙이기 — 크론 발행 후 Action이 `render.mjs`로 신규글 카드 생성·커밋. 크론의 DALL-E 호출 제거(비용↓).
   - 선행: `scratchpad/cardgen/`(render.mjs + Pretendard woff2 4종)을 저장소 정식 경로 `tools/cardgen/`로 이관(폰트는 GitHub raw에서 재다운 가능: orioncactus/pretendard v1.3.9).
   - 방향 확인 후 진행(크론 동작 변경이므로).

## 대기/차단 (사용자 액션 · 이전 세션 이월)
- GSC env 입력·Redeploy(`GSC_SERVICE_ACCOUNT_JSON`·`GSC_SITE_URL`) → `/api/health` `hasGSC:true` 확인.
- 디자인 스튜디오 `marketing-agency-erp` PR 허락(erp-v1 반영).
- misojin v3 → Google Drive 업로드(Drive MCP 불안정).

## 주의·제약 (반드시)
- **브랜치**: desktop-tutorial 작업=`claude/session-review-prep-an0to9`, 라이브=`main`(venom-new-site 자동배포). 파이프라인: implement→검증→commit→PR→squash-merge→`git checkout -B <branch> origin/main`→force-with-lease.
- **비밀키 값·모델 ID**를 커밋/PR/코드/문서/채팅에 넣지 않는다.
- 커밋 트레일러(Co-Authored-By / Claude-Session) 준수.
- 카드뉴스 재생성 자산은 `scratchpad/`(휘발) → 정식 이관 전엔 재현용 스크립트만 신뢰.

## 참고
- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md` · 이번 세션 상세 `docs/session-logs/2026-07-20-s01.md`.
