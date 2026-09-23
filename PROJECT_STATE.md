# PROJECT_STATE — desktop-tutorial

> 🤖 자동 생성 파일. 직접 수정 금지 — `node scripts/gen-project-state.mjs`(또는 CI)가 push마다 갱신.
> **새 세션은 이 파일부터 읽어 재탐색 토큰을 아낀다.**

- **저장소**: desktop-tutorial  ·  **현재 브랜치**: claude/practical-shannon-pcfyru  ·  **기본 브랜치**: claude/practical-shannon-pcfyru
- **이어갈 작업(RESUME)**: 이 방 것 → `RESUME-same-subject.md` (가지 표시로 짝지음) · 전체 14개

## 최근 커밋 (8)
- 2026-09-22 docs(same-subject): 남은 것 — 셋은 「안 한다」로 정해졌고 하나를 만들었다 (0.3.650)
- 2026-09-22 docs(same-subject): 이 일감은 닫혔다 — 넘길 것이 없다 · 경쟁 목록 43→21→15
- 2026-09-21 docs(same-subject): 체크포인트 — 0.3.641 나감 · 0.3.643 인계 · 남은 것은 코드 바깥
- 2026-09-21 docs(same-subject): 0.3.640 은 반쪽만 나갔다 — 설명글이 먼저 거짓이 된 자리
- 2026-09-20 docs(same-subject): 사장님 화면이 잡은 결함 — 만들어 놓고 연결을 안 했다 (0.3.640)
- 2026-09-20 docs(same-subject): 0.3.639 배포 인계 — 세션 기록 · 방 인계본 갱신
- 2026-09-19 docs(checkpoint): 같은 과 방 — 세션 기록 · 인계본 · PROJECT_STATE
- 2026-09-19 docs(anseo): 상권 탭 이름이 「입지」로 남아 있던 줄 고침

## 워크플로 (21)
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
- `fetch-file.yml` · 수동
- `geo-metrics-collect.yml` · '0 22 * * *' · 수동
- `geo-task-recur.yml` · '0 22 * * 0' · 수동
- `geo-weekly-report.yml` · '0 8 * * 5' · 수동
- `market-data.yml` · 수동
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
*생성: 커밋 c4dda0e 기준. 값·비밀은 포함하지 않음.*
