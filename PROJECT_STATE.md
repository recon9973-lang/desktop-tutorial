# PROJECT_STATE — desktop-tutorial

> 🤖 자동 생성 파일. 직접 수정 금지 — `node scripts/gen-project-state.mjs`(또는 CI)가 push마다 갱신.
> **새 세션은 이 파일부터 읽어 재탐색 토큰을 아낀다.**

- **저장소**: desktop-tutorial  ·  **현재 브랜치**: main  ·  **기본 브랜치**: main
- **이어갈 작업(RESUME)**: 있음 → `RESUME.md` 참조

## 최근 커밋 (8)
- 2026-07-23 GEO 실측 파트: Perplexity 단일 → 4개 AI(ChatGPT·Gemini·Claude·Perplexity) 실측 (#218)
- 2026-07-22 chore: PROJECT_STATE 자동 갱신 [skip ci]
- 2026-07-23 GEO 도구: 중복 준비도 막대 제거 → 메인 키워드 AI 노출 실측 파트 신설 (#217)
- 2026-07-22 chore: PROJECT_STATE 자동 갱신 [skip ci]
- 2026-07-23 fix(seo-tool): 신뢰 항목 추론 통과 제거 — 마크업 실측만 통과, 본문 정황은 '확인 필요' 강등 (#45) (#216)
- 2026-07-22 chore: PROJECT_STATE 자동 갱신 [skip ci]
- 2026-07-23 fix(geo-tool): 날조 수치 제거 — 업종 벤치마크→해석 기준구간, 4대 AI→온페이지 준비도(실측 기반) (#215)
- 2026-07-22 chore: PROJECT_STATE 자동 갱신 [skip ci]

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

## 환경변수 표면 (이름만, 값 아님 · 71)
`ADMIN_SECRET` · `AIRTABLE_API_KEY` · `AIRTABLE_LEAD_BASE` · `AIRTABLE_LEAD_TABLE` · `AIRTABLE_TOKEN` · `ALIMTALK_API_KEY` · `ALIMTALK_API_URL` · `ANTHROPIC_API_KEY` · `ANTHROPIC_JUDGE_MODEL` · `ANTHROPIC_MODEL` · `BLOG_IMAGE_MODE` · `BUILD_TS` · `CARD_FORCE` · `CHROME_BIN` · `CLOVA_OCR_INVOKE_URL` · `CLOVA_OCR_SECRET` · `CRON_SECRET` · `DATA_GO_KR_KEY` · `GEMINI_MODEL` · `GITHUB_BRANCH` · `GITHUB_OWNER` · `GITHUB_REPO` · `GITHUB_SHA` · `GITHUB_TOKEN` · `GOOGLE_VISION_API_KEY` · `GROWTHOPS_MONITOR_URLS` · `GSC_CLIENT_EMAIL` · `GSC_PRIVATE_KEY` · `GSC_SERVICE_ACCOUNT_JSON` · `GSC_SITE_URL` · `IG_ID` · `KAKAO_API_KEY` · `KAKAO_SENDER_KEY` · `KAKAO_TEMPLATE_RECOMMENDATION` · `KAKAO_TEMPLATE_REMINDER` · `KV_REST_API_TOKEN` · `KV_REST_API_URL` · `LAW_OC` · `LB_DISCLOSURE` · `LNHPD_API_URL` · `…(+31)`

---
*생성: 커밋 782b4c3 기준. 값·비밀은 포함하지 않음.*
