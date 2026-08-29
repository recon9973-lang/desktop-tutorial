# RESUME — 다음 세션 이어가기 (2026-08-29 밤 · s11 체크포인트)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세는 `docs/session-logs/2026-08-29-s11.md`(직전)·`-s10.md`,
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

ANSEO 이식 로드맵(사장님 확정 5단계) **전 단계 완료**: 0.자산 추출 → 1.파이프라인 시뮬 →
2.SEO·GEO 시뮬 → 3.AEO 시뮬 → 4.통합 시뮬 → **5.실물 이식 S1~S7 + 명세 발행까지 끝**.

- desktop-tutorial 작업 브랜치 `claude/image-design-workflow-analysis-efuea7` (시뮬 HTML·격차표, 최신 ab5b54d)
- veo-platform 작업 브랜치 **`claude/anseo-console-port`** (실물 이식 일곱 판 v0.3.380~386,
  최신 `21fd12b`, 전부 커밋됨) — 세션에 안 붙어 있으면 `add_repo`로 붙여 클론
- 5단계 기준 문서: **`docs/ANSEO-실물-이식-격차표.md`** (G1~G18·S1~S8·규율 체크)
- 명세 **발행 완료**: SEO 1.12.0 · GEO 1.6.0 PUBLISHED(시행 08-29T22:00+09, 등급 11단 E+/E 추가)

## 바로 이어갈 작업

1. **veo-platform 배포 — 사장님 오더 대기.** 배포 대기 **열두 판(0.3.375~0.3.386)**,
   앞 다섯(0.3.375~379)은 다른 방 작업분. 배포는 `VEO_DEPLOY_ORDER`(사장님 오더 원문)
   없이는 deploy.sh가 스스로 거부 — 오더가 떨어지면 `docs/ANSEO-배포-인계.md` 런북대로.
   매 판 web verify 초록·계약 동기화·관문 정산은 이미 끝나 있다.
2. 오더가 배포가 아니면 **S8 백로그**(실물 WORKLIST 대장 등재됨): 주제×엔진 매트릭스(주제
   태깅 설계부터)·질문 생키·TOP5 경쟁 순위·서버 트랙 4건(인용 스니펫·채택 영속화·주제
   태깅·조치 발행 이벤트).
3. veo-platform 검증 루프: `pnpm --filter @veo/web verify`(typecheck·lint·test·build·smoke) +
   `.venv`(python3.12) pytest(`VEO_SCORING_SPECS_DIR` 필요)·ruff·mypy. 서버 창구 변경 시
   `apps/api/scripts/export_openapi.py` → `pnpm --filter @veo/api-client generate`,
   명세 수 변경 시 `export_spec_counts.py`.

## 대기/차단

- **배포 오더**(`VEO_DEPLOY_ORDER` 원문) — 사장님.
- 이월: #36 GSC env 입력 · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드 (이 방 소관 아님).

## 주의·제약 (반드시)

- **깊숙한 전수 비교(영구 지시)**: 이식 작업은 시간이 걸려도 하나도 빠짐없이 실물과 비교 검토 후 진행.
- 브랜치: desktop-tutorial 시뮬·분석은 `claude/image-design-workflow-analysis-efuea7`,
  veo-platform 이식은 `claude/anseo-console-port`. 체크포인트 산출물만 main.
- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_019pLvoUJ8uv46QhpsR2su5k`(방 바뀌면 그 방 URL).
  모델 ID를 커밋/PR/코드/문서에 넣지 않는다. 비밀키 값 노출 금지.
- 사장님께 나가는 글은 「커밋」「배포」 두 단어만(민다·푸시 금지). 데이터는 테스트용 — 정합성 지적 금지.
- **관문을 무력화하지 않는다** — 기준선 변경 시 사유를 그 자리에(say-why는 `사장님 (지시|결정|지적)`
  어휘만 인정). 실측 원칙: 못 잰 값은 0이 아니라 —(ADR 0002). 판 다르면 비교 금지(ADR 0010,
  bridgeBreaks 점선 다리=참고). formatScore만·두 낱말·색으로만 말하지 않기.
- veo-platform 판 규율: changelog.ts 맨 앞=APP_VERSION, api `__version__`·계약 info.version 동기화,
  WORKLIST §2 미배포 목록+HISTORY 등재(관문이 강제). 발행 명세는 불변 — 고치려면 새 판.
- lovable.app/lovable.dev egress 차단 — 재시도 금지.

## 확정 규격 (되묻지 말 것)

- 등급 11단 A+(95)~F(0~49), E+(55~59)·E(50~54) — **발행 완료**. 등급 크게·점수 작게.
  등급 색: 90+통과/75~89 기본/60~74주의/<60실패 (색+글자 병용).
- 운영 목표선 취약 탈출 50·관리 목표 90(운영 목표 — 명세 따라 안 움직임) + 실측 기울기
  도달 예상(«관측값·보장 아님» 단서 분리 불가).
- AI 7종: ChatGPT·Gemini·Claude·Grok·Perplexity·네이버 AI브리핑·구글 AI오버뷰
  (글로벌 5종/검색 결합 2종 구분). 실물 SEO 배점 49+미배점 10=59검사.
- AEO: 키워드→질문(기본 5)→AI별 답변. 지표=인용률·인용 출처·자사vs경쟁·인용 콘텐츠 검토.
  배치·생키 문법은 s10·s11 로그 «확정 사항» 절.
- 콘텐츠 실제 생성(의료광고법 검수 포함)=5단계 실행 구간(화면에 실행 체인 명시).

## 참고

- 세션 상세 `docs/session-logs/2026-08-29-s11.md` · `-s10.md` · `-s09.md`
- 격차표 `docs/ANSEO-실물-이식-격차표.md` · 이식 기준 `docs/ANSEO-이식-자산-명세.md`
- 배포 런북 `docs/ANSEO-배포-인계.md` · veo-platform 대장 `docs/WORKLIST.md` §2 · `WORKLIST-HISTORY.md`
