# ANSEO / VEO 프로젝트에 쓸 만한 GitHub · 공개 자료 목록

> **오더** (2026-09-04): *"예를들어 법령정보 같은 것도 있더라고, 입지와 관련된것 외에도 우리 프로젝트와 연관된 것들이 있는지 에이전트 가동해서 모두 찾아줘"*
>
> **방법**: 여섯 개 주제로 나눠 서브에이전트 병렬 조사 (GitHub Search API + WebSearch). 별 · 갱신 · 라이선스 · 우리 어디에 쓸지를 실측으로 정리. 지어내지 않음.
>
> **원칙**:
> - **라이선스 명확한 것 우선** — SIL OFL · MIT · Apache · CC-BY · 공공누리 1유형
> - **미명시는 ⚠**, **비상업만은 ✗ SaaS 불가**로 표시
> - 별 ≥1 또는 갱신 2년 이내
> - 우리가 이미 하고 있는 것보다 못한 것은 「없다·낫지 않음」으로 정직

---

## 1. 법률·법령 · 의료광고 심의 (콘텐츠 검수의 뿌리)

| # | 자료 | 링크 | 별·갱신 | 라이선스 | 우리 어디에 |
|---|---|---|---|---|---|
| 1 | **국가법령정보 공동활용 Open API** | https://open.law.go.kr/ | 정부·상시 | 공공누리 | **런타임 RAG 1차 소스** — 의료법 56조·심의규정·개인정보보호법 조문 |
| 2 | finalchild/law-mcp | https://github.com/finalchild/law-mcp | 31★ · 2026-06 | 미명시 ⚠ | Claude Code 워크플로에 조문 즉시 조회 MCP |
| 3 | tjdwls101010/MOLEG-API | https://github.com/tjdwls101010/MOLEG-API | 0★ · 2026-07 | 미명시 ⚠ | 검수 시점에 조문 최신본 자동 fetch(개정 반영) Python SDK |
| 4 | KLUE-benchmark/KLUE | https://github.com/KLUE-benchmark/KLUE | 604★ · 2026-08 | CC-BY-SA 4.0 | 의료기관명·진료과·시술명 NER 베이스 코퍼스 |
| 5 | AI Hub 법률/규정 텍스트 (판례 60,000+) | https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71723 | 국가 · 활성 | AI Hub 약관 (조건부 상업 허용) | 광고 심의 판정 분류기 학습셋 |
| 6 | 대한의사협회 의료광고심의 가이드 | https://www.admedical.org/ | 협회 · 활성 | 저작권 협회 (인용만) | 콘텐츠 승인 규칙엔진 시드 (전후사진·최상급 금지) — 우리가 PDF 파싱해 룰로 |
| ⚠ | lbox-kr/lbox-open · lbox/lbox_open (판례 벤치) | https://github.com/lbox-kr/lbox-open | 108★ | ✗ CC BY-NC 4.0 추정 · **SaaS 불가** | 사내 R&D·모델 평가만 |

**세 추천**: ⑴ 국가법령정보 Open API (상시 최신·상업 안전) · ⑵ finalchild/law-mcp (Claude Code 즉시) · ⑶ AI Hub 판례 60K (라이선스 명확).
**리스크**: lbox 계열은 별점 높지만 CC BY-NC 로 SaaS 불가 — 우회는 국가법령정보 API.
**없더라**: 의료광고 심의 사례 공개 데이터셋은 존재 안 함. 협회 가이드 PDF 를 우리가 파싱해 룰 KB 로 만들어야 함.

---

## 2. 교통·지리·행정 (입지 확장)

| # | 자료 | 링크 | 별·갱신 | 라이선스 | 축 | 커버 | 우리 어디에 |
|---|---|---|---|---|---|---|---|
| 1 | **vuski/admdongkor** | https://github.com/vuski/admdongkor | 526★ · 2026-07 | **CC BY 4.0** | 경계 | **전국·분기별·시계열** | 반경 히트맵·행정동 슬라이싱 (**경계 1순위**) |
| 2 | **WooilJeong/PublicDataReader** | https://github.com/WooilJeong/PublicDataReader | 599★ · 활성 | **MIT** | 상권·인구·부동산 API wrapper | 전국 | data.go.kr API 인증키만 있으면 CSV/DF |
| 3 | **henewsuh/subway_crd_line_info** | https://github.com/henewsuh/subway_crd_line_info | – | **MIT** | 지하철역+노선 | 서울교통공사 노선 | 수도권 지하철 좌표 즉시 |
| 4 | southkorea/southkorea-maps | https://github.com/southkorea/southkorea-maps | 481★ · 2026-08 | 혼합 (KOSTAT 자유·POPONG CC BY) | 경계 | 전국 | 단순화 TopoJSON (vuski 폴백) |
| 5 | vuski/SeoulBikeStationLocation | https://github.com/vuski/SeoulBikeStationLocation | 9★ | 미명시 ⚠ | 따릉이 | 서울 | 미시 접근성 가중 |
| 6 | LiF-Lee/Subway_Station_Data | https://github.com/LiF-Lee/Subway_Station_Data | 1★ · 2024-05 | **MIT** | 지하철역 | 전국 (격자좌표) | 좌표 변환 필요 |
| ⚠ | hyereekang/seoul-bus-stops-data | https://github.com/hyereekang/seoul-bus-stops-data | 0★ | 미명시 ⚠ | 버스 | 서울 CP949 | 라이선스 리스크 |
| ⚠ | chanyou/open-seoul-subway | https://github.com/chanyou/open-seoul-subway | 8★ | 미명시 ⚠ | 지하철 | 수도권 UTF-8 | 라이선스 리스크 |
| ✗ | gisman/geocoder-kr | https://github.com/gisman/geocoder-kr | 13★ | ✗ 상업 사용 금지 | 지오코딩 | 전국 | **SaaS 불가** |

**축별 최선 (전국·라이선스 명확)**:
- 경계 → vuski/admdongkor (CC BY 4.0, pip/npm)
- API wrapper → PublicDataReader (MIT)
- 지하철 수도권 → henewsuh/subway_crd_line_info (MIT, EPSG:4326)

**없더라**:
- **버스정류장 전국 GitHub 미러 없음** — 공공데이터포털 TAGO 정류소 API 직접 호출 유일
- 행정동 성/연령 인구 GitHub 없음 → jumin.mois.go.kr 월간 CSV 또는 PublicDataReader
- 전국 유동인구·상권 오픈 없음 (KT/SKT 유료)
- 상업 지오코더 없음 → juso.go.kr + VWorld

**결정** (사장님 2026-09-04): **교통은 원 자료(공공데이터포털 TAGO)로**. 이 판에 스키마·로더·「파일 올리기」·읽기·화면·시험 심고, 사장님이 파일 넘겨주시면 진짜 값 뜸.

---

## 3. 한국어 NLP · 의료 어휘 · 콘텐츠 검수

| # | 자료 | 링크 | 라이선스 | 축 | 우리 어디에 |
|---|---|---|---|---|---|
| 1 | **KM-BERT** (Korean Medical BERT) | https://github.com/KU-RIAS/KM-BERT-Korean-Medical-BERT | Apache-2.0 | 모델 | 진료·질환 임베딩·NER 파인튜닝 |
| 2 | **BGE-m3-ko** (upskyy/dragonkue) | HF | MIT | 모델 | **AI 인용 관측·유사글 1순위** — 8192 토큰·MTEB-ko 최상위 |
| 3 | **Marker-Inc-Korea/ko-pii** | https://github.com/Marker-Inc-Korea/ko-pii | Apache-2.0 | PII | **상담·CS 로그 마스킹 즉시** — 33 카테고리 |
| 4 | jhgan/ko-sroberta-multitask | HF | MIT | 임베딩 | 768d 콜드스타트 |
| 5 | monologg/KoBigBird | GitHub | Apache-2.0 | 모델 | 블로그 장문 심의 (4096 토큰) |
| 6 | KLUE + KLUE-NER | https://github.com/KLUE-benchmark/KLUE | CC BY-SA 4.0 | 벤치 | 한국어 NER/유사도 벤치 |
| 7 | datanada/Awesome-Korean-NLP | https://github.com/datanada/Awesome-Korean-NLP | CC0 | 색인 | 새 자료 최신 |
| 8 | AI Hub 초거대 AI 헬스케어 Q&A | https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71762 | AI Hub 약관 | 데이터 | 챗상담·FAQ·의도 분류 (19 질환·500 질환명·11 질문유형) |
| 9 | 식약처 e약은요 OpenAPI | https://www.data.go.kr/data/15075057/openapi.do | 공공누리 1유형 | 사전 | 처방·복약 카드 자동생성 |
| 10 | 의료광고 사전심의 가이드 | https://www.admedical.org/guide/regulations.do | 공공기관 | 사전 | 금지 표현 어휘 원전 |
| 11 | mecab-ko · pecab · kiwipiepy | GitHub | MIT/Apache | 형태소 | 카드뉴스·릴스 문장 정제 |
| 12 | spellcheck-ko/korean-dict-nikl | GitHub | CC BY-SA 2.0-KR | 사전 | 국립국어원 표준 국어사전 |

**콘텐츠 심의 즉시**: ko-pii(마스킹) + badwords-ko(비속어) + 심의 가이드 PDF 자체 파싱한 금지어 사전 (**공개 통합본 없음** — 우리가 만들어야).
**임베딩 하나**: BGE-m3-ko — AI 인용 관측·유사글·FAQ 다 재활용.
**없더라**: 진료과·시술·질환 통합 공개 사전 (HIRA 는 우리에 있음), 공개 광고 금지어 리스트, DUR 성분은 OpenAPI 만.

---

## 4. AI 검색 · LLM 관측 · GEO/AEO 벤치

| # | 자료 | 링크 | 별·갱신 | 라이선스 | 우리 어디에 |
|---|---|---|---|---|---|
| 1 | **elmohq/elmo** — 7종 AI(ChatGPT·Claude·Perplexity·Gemini·Copilot·Grok·Google AIO) 인용/멘션 관측 오픈소스 SaaS | https://github.com/elmohq/elmo | 292★ · 활발 | MIT | **우리 SaaS와 스코프 사실상 동일** — 스코어링·share-of-voice 감사 |
| 2 | GEO-Optim/geo-bench (HF) | https://huggingface.co/datasets/GEO-Optim/geo-bench | 논문 부속 | 논문 | AEO 최적화 A/B 표준 벤치 (10K 쿼리) |
| 3 | **GEO 논문** Aggarwal KDD '24 | https://arxiv.org/abs/2311.09735 | — | — | GEO/AEO 학술 원점. 9가지 전략 실측 (quotes +40% 등) 근거 |
| 4 | vectara/hallucination-leaderboard (HHEM) | https://github.com/vectara/hallucination-leaderboard | 3.3k★ | Apache-2.0 | 인용 검증 · 모델별 신뢰도 가중치 |
| 5 | amazon-science/RefChecker | https://github.com/amazon-science/RefChecker | 434★ | Apache-2.0 | 트리플 단위 사실성 체커 |
| 6 | **langfuse/langfuse** | https://github.com/langfuse/langfuse | 34k★ · 활발 | MIT | 7종 AI 호출 트레이싱·프롬프트 버전 |
| 7 | comet-ml/opik | https://github.com/comet-ml/opik | 21.8k★ | Apache-2.0 | Langfuse 대체안 |
| 8 | isnow890/naver-search-mcp | https://github.com/isnow890/naver-search-mcp | 84★ · 활발 | MIT | 네이버 AI 브리핑 인용원 관측 MCP |
| 9 | WooilJeong/PyNaver | https://github.com/WooilJeong/PyNaver | 55★ | MIT | DataLab·지오코딩 백엔드 배치 |
| 10 | joshcarty/google-searchconsole | https://github.com/joshcarty/google-searchconsole | 253★ | MIT | 거래처 GSC 리포트 자동화 |
| 11 | ItzCrazyKns/Perplexica | https://github.com/ItzCrazyKns/Perplexica | 36.6k★ | MIT | AI 인용 시뮬 |
| 12 | firecrawl/fireplexity | https://github.com/firecrawl/fireplexity | 2.0k★ | MIT | 크롤→인용 파이프라인 |
| 13 | EdinburghNLP/awesome-hallucination-detection | https://github.com/EdinburghNLP/awesome-hallucination-detection | 1.1k★ | Apache-2.0 | 벤치 소스풀 |
| 14 | ContextJet-ai/awesome-llm-observability | https://github.com/ContextJet-ai/awesome-llm-observability | 33★ | CC0 | 관측 툴 최신 순위 |

**바로 쓸 셋**: elmohq/elmo(스코어링 감사) · vectara HHEM + RefChecker(인용 사실성 채점) · GEO-bench + Aggarwal 논문(제안서 근거).
**없더라**: 네이버 AI 브리핑 전용 벤치·구글 AIO 인용 로그·한국어 의료 특화 AEO 벤치 셋 다 없음 — **우리가 만들면 우위**.

---

## 5. 디자인 · 카드뉴스 · 릴스 · 접근성

| # | 자료 | 링크 | 별 | 라이선스 | 우리 어디에 |
|---|---|---|---|---|---|
| 1 | orioncactus/pretendard | https://github.com/orioncactus/pretendard | 3.5k | SIL OFL 1.1 | **이미 사용 중** |
| 2 | **resolvetosavelives/healthicons** | https://github.com/resolvetosavelives/healthicons | 858 | MIT/CC0 | **진료과·병원 픽토그램** (성형·산부인과·안과·치과) |
| 3 | lucide-icons/lucide | https://github.com/lucide-icons/lucide | 24.3k | ISC | 콘솔 범용 라인 아이콘 |
| 4 | tabler/tabler-icons | https://github.com/tabler/tabler-icons | 21.6k | MIT | 6,100+ (차트·지도·통계·마케팅) |
| 5 | **dequelabs/axe-core** + abhinaba-ghosh/axe-playwright | https://github.com/dequelabs/axe-core | 7.5k / 232 | MPL 2.0 / MIT | **접근성 자동 검사 — Playwright 즉시 편입** |
| 6 | pa11y-ci | https://github.com/pa11y/pa11y-ci | 629 | LGPL 3.0 | 사이트맵 회귀 |
| 7 | **gka/chroma.js** | https://github.com/gka/chroma.js | 10.6k | BSD/Apache 2.0 | 색 변환 · deltaE · 색각 시뮬 |
| 8 | antiflasher/apcach | https://github.com/antiflasher/apcach | 188 | MIT | APCA 팔레트 자동 생성 |
| 9 | bbc/color-contrast-checker | https://github.com/bbc/color-contrast-checker | 106 | Apache 2.0 | 4색×다크/라이트 |
| 10 | apache/echarts | https://github.com/apache/echarts | 67.2k | Apache 2.0 | 한글 축·다크/라이트 |
| 11 | kuskhan/jetendard · taevel02/yeomil-mono | GitHub | SIL OFL | 서체 | 개발자 콘솔 한글+영문 모노 |

**카드뉴스 즉시 셋**: Pretendard(있음) + healthicons(진료과) + chroma.js/apcach(팔레트).
**접근성 자동 하나**: axe-playwright (우리 Playwright에 즉시). 배포 후 pa11y-ci.
**주의**: SUIT · Gmarket Sans · 배민한나체는 GitHub 아닌 배포 zip.

---

## 6. 개발 규율 · CI · 판 관리 · 서브에이전트

| # | 자료 | 링크 | 별 | 라이선스 | 우리 어디에 |
|---|---|---|---|---|---|
| 1 | disler/claude-code-hooks-mastery | https://github.com/disler/claude-code-hooks-mastery | ~10k | MIT | UV 단일파일 훅 — 웹/원격 세션에서 훅 안 도는 문제 우회 |
| 2 | smtg-ai/claude-squad | https://github.com/smtg-ai/claude-squad | ~7k | AGPL-3.0 | tmux+worktree TUI 오케스트레이션 (외부 러너만) |
| 3 | Anthropic Agent Teams · Subagents | https://code.claude.com/docs/en/agent-teams | 공식 | 공식 | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 방간 직접 통신 |
| 4 | 공식 git worktree parallel sessions | https://code.claude.com/docs/en/worktrees | 공식 | 공식 | `-w` + `.worktreeinclude` 방별 격리 |
| 5 | punkpeye/awesome-mcp-servers | https://github.com/punkpeye/awesome-mcp-servers | ~50k | MIT | MCP 마스터 인덱스 |
| 6 | **changesets/changesets** | https://github.com/changesets/changesets | ~9k | MIT | 판 번호 3중 확인 대체 — PR마다 `.changeset/*.md` → 자동 bump+CHANGELOG (pnpm 표준) |
| 7 | avivsinai/langfuse-mcp | https://github.com/avivsinai/langfuse-mcp | ~1k | MIT | 방간 프롬프트·비용·회귀 로그 (나노바나나 감사) |
| 8 | jqueryscript/awesome-claude-code | https://github.com/jqueryscript/awesome-claude-code | 28k+ | MIT | 훅·슬래시커맨드·에이전트 인덱스 |
| 9 | schemathesis/schemathesis | https://github.com/schemathesis/schemathesis | ~2k | MIT | OpenAPI drift 자동 차단 |
| ✗ | googleapis/release-please | https://github.com/googleapis/release-please | ~5k | Apache-2.0 | pnpm workspace 지원 미성숙 (이슈 #2173/#1587) |

**즉시 참고 셋**: git worktree 공식(#4) + claude-squad(#2) — 방별 격리 근본 해결. disler 훅(#1) — 20건 자동카운트 이식. Langfuse MCP(#7) — 비싼 콜 감사.
**판 관리**: Changesets(#6)만이 실전 후보 — 「판 번호 사람이 세는 게 지겹다」면 도입.
**낫지 않음**: SuperClaude·claude-flow 는 YAML+md 컨벤션. 우리 규율이 더 명확 — 도입 시 흐려짐.

---

## 사장님이 고르실 것 (권장 우선순위)

1. **교통 원 자료 붙이기** (진행 중, 이 판) — 인프라 심고 사장님이 파일 넘겨주시면 실적재
2. **경계·인구 붙이기** (다음 판) — vuski/admdongkor + PublicDataReader (전국 커버·CC BY 4.0·MIT)
3. **콘텐츠 검수 강화** — ko-pii(마스킹) + 심의 가이드 파싱한 금지어 사전
4. **AI 인용 관측 감사** — elmohq/elmo 코드와 우리 로직 대조·감사
5. **접근성 자동 검사** — axe-playwright 우리 CI 편입
6. **판 관리 자동화** — Changesets 도입 (사람이 세는 게 지겨우면)

각 원 자료의 세부 실측은 `/tmp/claude-0/.../scratchpad/inventory-{1..6}-*.md` 에 남아 있음. 필요하면 이 문서 각 섹션에 붙여 확장.
