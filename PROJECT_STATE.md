# PROJECT_STATE — desktop-tutorial

> 🤖 자동 생성 파일. 직접 수정 금지 — `node scripts/gen-project-state.mjs`(또는 CI)가 push마다 갱신.
> **새 세션은 이 파일부터 읽어 재탐색 토큰을 아낀다.**

- **저장소**: desktop-tutorial  ·  **현재 브랜치**: main  ·  **기본 브랜치**: main
- **이어갈 작업(RESUME)**: 있음 → `RESUME.md` 참조

## 최근 커밋 (8)
- 2026-07-15 diag(gsc): health에 GSC 진단 필드 추가 (비밀 미노출·불리언만)
- 2026-07-15 chore: PROJECT_STATE 자동 갱신 [skip ci]
- 2026-07-15 chore(checkpoint): 세션 인계 — session-log·RESUME·PROJECT_STATE·CLAUDE.md
- 2026-07-15 chore: PROJECT_STATE 자동 갱신 [skip ci]
- 2026-07-15 chore(checkpoint): 세션 s01 인계 — 로그·RESUME·PROJECT_STATE·CLAUDE.md
- 2026-07-15 chore: PROJECT_STATE 자동 갱신 [skip ci]
- 2026-07-15 feat(skill): 최강스킬 — 연속성·토큰절약 시스템 설치형 스킬
- 2026-07-15 chore: PROJECT_STATE 자동 갱신 [skip ci]

## 워크플로 (18)
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
- `set-clinic-role.yml` · 수동

## Vercel crons
- `/api/cron-seo-monitor` · 0 18 * * *
- `/api/cron-eval` · 0 0 * * 1

## API 엔드포인트 (31)
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
- `your-supplement/server/api/recommend.js`
- `…(+1)`

## package 스크립트
`convert-webp` · `build`  ·  deps 1개

## 환경변수 표면 (이름만, 값 아님 · 69)
`ADMIN_SECRET` · `AIRTABLE_API_KEY` · `AIRTABLE_LEAD_BASE` · `AIRTABLE_LEAD_TABLE` · `AIRTABLE_TOKEN` · `ALIMTALK_API_KEY` · `ALIMTALK_API_URL` · `ANTHROPIC_API_KEY` · `ANTHROPIC_JUDGE_MODEL` · `ANTHROPIC_MODEL` · `BUILD_TS` · `CHROME_BIN` · `CLOVA_OCR_INVOKE_URL` · `CLOVA_OCR_SECRET` · `CRON_SECRET` · `DATA_GO_KR_KEY` · `GEMINI_MODEL` · `GITHUB_BRANCH` · `GITHUB_OWNER` · `GITHUB_REPO` · `GITHUB_SHA` · `GITHUB_TOKEN` · `GOOGLE_VISION_API_KEY` · `GROWTHOPS_MONITOR_URLS` · `GSC_CLIENT_EMAIL` · `GSC_PRIVATE_KEY` · `GSC_SERVICE_ACCOUNT_JSON` · `GSC_SITE_URL` · `IG_ID` · `KAKAO_API_KEY` · `KAKAO_SENDER_KEY` · `KAKAO_TEMPLATE_RECOMMENDATION` · `KAKAO_TEMPLATE_REMINDER` · `KV_REST_API_TOKEN` · `KV_REST_API_URL` · `LAW_OC` · `LB_DISCLOSURE` · `LNHPD_API_URL` · `MFDS_DUR_API_URL` · `MFDS_MATERIAL_API_URL` · `…(+29)`

---
*생성: 커밋 c009758 기준. 값·비밀은 포함하지 않음.*
