# PROJECT_STATE — desktop-tutorial

> 🤖 자동 생성 파일. 직접 수정 금지 — `node scripts/gen-project-state.mjs`(또는 CI)가 push마다 갱신.
> **새 세션은 이 파일부터 읽어 재탐색 토큰을 아낀다.**

- **저장소**: desktop-tutorial  ·  **현재 브랜치**: claude/anseo-screen-layout-optimization-ucs22y  ·  **기본 브랜치**: claude/anseo-screen-layout-optimization-ucs22y
- **이어갈 작업(RESUME)**: 있음 → `RESUME.md` 참조

## 최근 커밋 (8)
- 2026-09-03 docs: 도장 커밋 0065038a main 도달 기록 — 0.3.494~0.3.497 회차 완전 마감
- 2026-09-03 docs: 0.3.494~0.3.497 배포 마감 도장 — 대조표 §7-5·s17 로그·RESUME·PROJECT_STATE
- 2026-09-03 docs: 판 번호 충돌 기록 — 입지 방도 0.3.496, 이 판은 그 방이 main 에 닿으면 0.3.497 로
- 2026-09-03 docs: 누름 영역 마무리 v0.3.496 — 대조표 §7-5 · s17 로그 · RESUME · PROJECT_STATE
- 2026-09-03 docs: 도장 커밋 640866b8 main 도달 기록 — 0.3.489~0.3.495 회차 마감
- 2026-09-03 docs: 0.3.489~0.3.495 배포 도장 · s17 체크포인트 — 대조표 §7-4 실측·세션 로그·RESUME·PROJECT_STATE
- 2026-09-03 docs: s17 — 남은 작업 마감(예외 줄임·누름 영역)·판 번호 물림 0.3.494~0.3.495·동행 배포 진행 — 대조표 §7-4·s17 로그·RESUME
- 2026-09-03 docs: 새 화면 관문 3종·촬영 장치·규칙 문서 — 대조표 §7·s16 로그·RESUME (veo-platform v0.3.490 준비)

## 워크플로 (19)
- `ai-expose-check.yml` · '0 0 1 * *' · 수동
- `api-check.yml` · 수동
- `apply-clinic-schema.yml` · 수동
- `auto-publish.yml` · '*/15 * * * *' · 수동
- `build-covers.yml` · 수동
- `check-sitemap.yml` · 수동
- `clinic-dashboard.yml` · '0 1 1 * *' · 수동
- `config-clinic-auth.yml` · 수동
- `convert-webp.yml` · 수동
- `deploy-clinic-functions.yml` · 수동
- `fetch-blog-ai.yml` · 수동
- `geo-metrics-collect.yml` · '0 22 * * *' · 수동
- `geo-task-recur.yml` · '0 22 * * 0' · 수동
- `geo-weekly-report.yml` · '0 8 * * 5' · 수동
- `project-state.yml` · 수동
- `publish-ig.yml` · '0 12 * * *' · 수동
- `refresh-ig-token.yml` · '0 3 1 * *' · 수동
- `render-blog-cards.yml` · '20 * * * *' · 수동
- `set-clinic-role.yml` · 수동

## Vercel crons
- `/api/cron-seo-monitor` · 0 18 * * *
- `/api/cron-eval` · 0 0 * * 1

## API 엔드포인트 (32)
- `venom-wordpress/preview/api/analytics.js`
- `venom-wordpress/preview/api/chatbot.js`
- `venom-wordpress/preview/api/contact.js`
- `venom-wordpress/preview/api/cron-daily-posts.js`
- `venom-wordpress/preview/api/cron-eval.js`
- `venom-wordpress/preview/api/cron-seo-monitor.js`
- `venom-wordpress/preview/api/eval-judge.js`
- `venom-wordpress/preview/api/generate-post.js`
- `venom-wordpress/preview/api/geo-ops.js`
- `venom-wordpress/preview/api/growthops.js`
- `venom-wordpress/preview/api/health.js`
- `venom-wordpress/preview/api/hospital-bot.js`
- `venom-wordpress/preview/api/insights.js`
- `venom-wordpress/preview/api/keyword-discover.js`
- `venom-wordpress/preview/api/posting-settings.js`
- `venom-wordpress/preview/api/publish-post.js`
- `venom-wordpress/preview/api/seo-proxy.js`
- `venom-wordpress/preview/api/statutes-refresh.js`
- `venom-wordpress/preview/api/store.js`
- `venom-wordpress/preview/api/usage-stats.js`
- `your-supplement/apps/web/app/api/dur/route.js`
- `your-supplement/apps/web/app/api/evidence-search/route.js`
- `your-supplement/apps/web/app/api/kakao/route.js`
- `your-supplement/apps/web/app/api/nearby/route.js`
- `your-supplement/apps/web/app/api/offers/route.js`
- `your-supplement/apps/web/app/api/products/route.js`
- `your-supplement/apps/web/app/api/recommend/route.js`
- `your-supplement/apps/web/app/api/safety/route.js`
- `your-supplement/server/api/kakao.js`
- `your-supplement/server/api/offers.js`
- `…(+2)`

## package 스크립트
`convert-webp` · `build`  ·  deps 1개

## 환경변수 표면 (이름만, 값 아님 · 76)
`ADMIN_SECRET` · `AIRTABLE_API_KEY` · `AIRTABLE_LEAD_BASE` · `AIRTABLE_LEAD_TABLE` · `AIRTABLE_TOKEN` · `ALIMTALK_API_KEY` · `ALIMTALK_API_URL` · `ANTHROPIC_API_KEY` · `ANTHROPIC_JUDGE_MODEL` · `ANTHROPIC_MODEL` · `BLOG_IMAGE_MODE` · `BUILD_TS` · `CARD_FORCE` · `CHROME_BIN` · `CLOVA_OCR_INVOKE_URL` · `CLOVA_OCR_SECRET` · `CRON_SECRET` · `DATA_GO_KR_KEY` · `GEMINI_MODEL` · `GITHUB_BRANCH` · `GITHUB_OWNER` · `GITHUB_REPO` · `GITHUB_SHA` · `GITHUB_TOKEN` · `GOOGLE_PAGESPEED_KEY` · `GOOGLE_PSI_KEY` · `GOOGLE_VISION_API_KEY` · `GROWTHOPS_MONITOR_URLS` · `GSC_CLIENT_EMAIL` · `GSC_PRIVATE_KEY` · `GSC_SERVICE_ACCOUNT_JSON` · `GSC_SITE_URL` · `IG_ID` · `KAKAO_API_KEY` · `KAKAO_SENDER_KEY` · `KAKAO_TEMPLATE_RECOMMENDATION` · `KAKAO_TEMPLATE_REMINDER` · `KV_REST_API_TOKEN` · `KV_REST_API_URL` · `LAW_OC` · `…(+36)`

---
*생성: 커밋 1825272 기준. 값·비밀은 포함하지 않음.*
