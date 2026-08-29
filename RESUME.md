# RESUME — 다음 세션 이어가기 (2026-08-29 저녁 · s10 체크포인트)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세는 `docs/session-logs/2026-08-29-s10.md`(직전)·`-s09.md`,
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

ANSEO 이식 로드맵(사장님 확정 5단계)을 순서대로 진행 중. **0~2단계 완료, 3단계(AEO 화면) 사실상 완료 — 사용자 «ㄱㄱ» 대기.**
- 작업 브랜치 **`claude/image-design-workflow-analysis-efuea7`** (분석·시뮬 HTML 전부 여기, 최신 b438f66)
- 산출물: `docs/ANSEO-이식-자산-명세.md`(기준 문서·실물 확정 반영 절 포함) · `docs/ANSEO-파이프라인-시뮬레이션.html` ·
  `docs/ANSEO-SEO-GEO-화면-시뮬레이션.html` · `docs/ANSEO-AEO-화면-시뮬레이션.html` · `docs/ANSEO-AEO-상단-인포그래픽-후보5종.html`
- 아티팩트 URL(재발행 시 유지): SEO·GEO `1160bf6a-…`, AEO `000e361e-…`, 후보5종 `bca62c83-…` — 갱신은 같은 세션 파일 경로 재발행 또는 `url` 지정

## 바로 이어갈 작업

1. **사용자 «ㄱㄱ» 떨어지면 Task #4 완료 처리 → Task #5 «4. 전체 이식 통합 시뮬레이션» 시작.**
   투입 자산: B7 B8 · C13(선택) · D6(선택) + 1~3단계 전부 + NXT 이관분(TOP5 경쟁 순위 카드).
   통합 화면 = 거래처 상세 전체 탭 흐름(진단→SEO→GEO→AEO→이슈→리포트) + 담당자 관점(최고 관리자 1~3, 콘텐츠 담당 1인=10거래처).
2. AEO 화면에 추가 피드백이 오면 v3(확정 배치) 위에 반영: 파일 `scratchpad`가 아니라 **docs 사본을 시작점**으로 복사해 작업
   (`docs/ANSEO-AEO-화면-시뮬레이션.html` → scratchpad → 검증 → 재발행(url 지정) → docs 복사 → 커밋).
3. 검증 루프 고정: Playwright(`/opt/node22/lib/node_modules/playwright/index.mjs`, chromium `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, `--no-sandbox`, colorScheme dark)로 렌더→어서션→스크린샷 후 커밋.

## 대기/차단

- Task #4 완료 승인(«ㄱㄱ») — 사용자.
- 이월: #36 GSC env 입력 · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드 (s08 이월분, 이 방 소관 아님).

## 주의·제약 (반드시)

- 분석·시뮬 커밋은 `claude/image-design-workflow-analysis-efuea7`에만. 체크포인트 산출물만 main.
- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_019pLvoUJ8uv46QhpsR2su5k`(방이 바뀌면 그 방 세션 URL). 모델 ID를 커밋/PR/코드/문서에 넣지 않는다.
- 사장님께 나가는 글은 「커밋」「배포」 두 단어만(민다·푸시 금지). 데이터는 테스트용 — 정합성 지적 금지.
- lovable.app/lovable.dev는 egress 차단 — 프리뷰 열람 재시도 금지(커넥터 소스 판독으로 우회).
- **확정 규격**(되묻지 말 것): 등급 11단(등급 크게·점수 작게)·이력 문법(곡선·끊지 않음·목표선 E50/A90·조치 ◆·판 다르면 Δ «—»)·
  실물 SEO 배점 49+미배점 10·AI 7종(ChatGPT·Gemini·Claude·Grok·Perplexity·네이버 AI브리핑·구글 AI오버뷰)·
  AEO 지표(인용률·인용 출처·자사vs경쟁·인용 콘텐츠 검토)·AEO 배치(s10 로그 «확정 사항» 절 참조).

## 참고

- 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md` · 이식 기준 `docs/ANSEO-이식-자산-명세.md`
- 분석 본문 `docs/ANSEO-콘솔-디자인-워크플로우-인포그래픽-분석.md` (제7·8부=애니메이션 전수 카탈로그)
