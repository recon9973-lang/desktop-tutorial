# Claude 입문 1시간 강의 — 최종 기획안 (자료수집·검증 완료판)

작성일: 2026-07-14
대상: 비개발자 70% 포함 초보자
분량: 60분 (슬라이드 22장 + 실습 2개)
원칙: **Anthropic/Claude 공식 문서·공식 제품 페이지에서 확인된 내용만 사용.** 미확인 정보는 강의 직전 재확인.

---

## 0. 이 기획안이 초안과 달라진 점 (팩트체크 반영)

두 갈래(제품 페이지 / Claude Code 문서)로 공식 출처를 교차검증했다. 초안의 6개 핵심 주장은 **모두 사실로 확인**되었고, 아래 4가지만 정밀 보정했다.

| 항목 | 초안 표현 | 보정 (공식 기준) |
|---|---|---|
| Constitutional AI | "사람이 유해 답변을 라벨링하는 대신 AI 피드백 사용" | 사람 피드백이 사라지는 게 아니라 **'유용성'은 여전히 사람 피드백(RLHF)**, **'무해성'에서만** 사람 라벨을 원칙 기반 자기수정 + AI 피드백(RLAIF)으로 대체. 2단계: ①자기비평·수정(지도학습) → ②AI 피드백 강화학습. |
| Claude Research | "유료 플랜 제공" | 맞음. 구체화: **Pro·Max·Team·Enterprise**, 웹·데스크톱·모바일에서 사용. **웹 검색이 켜져 있어야** 작동. |
| Claude Design | "PPTX/PDF/HTML 내보내기, 외부앱 연결" | 맞음. 보강: **베타 제품**. Claude Code와 **양방향** 연동(`/design-sync`로 디자인시스템 가져오기 ↔ `/design`으로 작업, "Hand off to Claude Code"로 구현 이관). 내보내기 파트너 예: Canva, Figma류 도구, Vercel 등. |
| Desktop extension vs Remote connector | "데스크톱 확장은 Claude Desktop·Claude Code에서 사용" | 보정: 로컬 파일/로컬DB/OS 접근형 확장의 **1차 기준점은 Claude Desktop 앱**. 원격 세션의 로컬 파일 접근은 **데스크톱 앱이 열려 있을 때만** 동작. "Claude Code에서도 쓴다"는 표현은 약하게. |

**강의 직전 반드시 재확인할 항목(변동성 높음):**
- 최신·권장 모델명 (현재 라인업: Opus 4.8, Sonnet 5, Haiku 4.5, Fable 5) — **모델 ID는 슬라이드에 넣지 말고 등급명만.**
- MCP의 표준 거버넌스 현황(업계 공동 표준으로 확산 중 — 구체적 관리주체·날짜는 공식 페이지에서 확인 후 언급).
- 플랜별 세부 제한, Design 베타 제공 범위, 커넥터별 가능 작업.

---

## 1. 학습 목표 (강의 후 수강자가 설명할 수 있어야 할 것)

1. Claude가 무엇이고 어떤 업무에 쓰이는지
2. Chat · Research · Code · Design의 차이와 사용 시점
3. MCP · Connector · Skill · Plugin의 역할 구분
4. 실무에서 Claude를 적용하는 순서(작은 반복 흐름부터)
5. 안전하게 쓰기 위해 **권한 · 출처 · 검수**에서 확인할 것

**한 줄 프레임:** "Claude는 답변 생성기가 아니라, 도구·파일·앱과 연결되는 **업무 파트너(일 잘하는 신입 동료)**다."

---

## 2. 최종 강의 흐름 & 타임라인 (초안 6장 개선안 반영)

초보자에게 MCP·스킬·플러그인을 너무 일찍 꺼내면 추상적이다. **먼저 "무엇을 할 수 있는가"를 보여주고, 확장 개념(MCP/커넥터/스킬/플러그인)은 후반 15분에 묶어서** 설명한다.

| 구간 | 시간 | 블록 | 슬라이드 |
|---|---|---|---|
| ① 오프닝 | 0–5분 | 챗봇인가 작업공간인가 + 오늘의 지도 | 1–2 |
| ② Claude 이해 | 5–15분 | 모델 제품군, 설계 철학(CAI), 잘하는 일/조심할 일 | 3–4 |
| ③ Chat & Research | 15–27분 | 좋은 질문법, Chat 활용, Research·출처 | 5–7 |
| ④ Code & Design | 27–40분 | 코드 작업, 비개발자 활용, Design, Artifacts | 8–11 |
| ⑤ 연결·확장 | 40–52분 | MCP·Connector·Skill·Plugin·Subagent 비교 | 12–17 |
| ⑥ 실무 적용 | 52–57분 | 직무별 시나리오 3종 | 18–20 |
| ⑦ 안전 & 마무리 | 57–60분 | 안전 체크리스트, 실습, 정리 | 21–22 |

> 장당 평균 2–3분. 실습 포함 시 22장이 1시간에 적정. 시간이 부족하면 18–20번 시나리오 중 청중 직무에 맞는 1개만 남긴다.

---

## 3. 슬라이드별 원고 (제목 · 핵심메시지 · 발표자 노트 · 출처)

### Slide 1 — 제목
- **제목:** Claude 처음 사용자를 위한 1시간 입문
- **부제:** 채팅에서 코드·디자인·MCP·스킬·플러그인까지
- **노트:** 기능 이름을 외우는 강의가 아니라, **언제 어떤 방식으로 쓸지 판단**하는 강의라고 선언.

### Slide 2 — 오늘의 지도 (⭐생태계 다이어그램)
- 중앙: **Claude** / 안쪽 고리: Chat · Research · Code · Design / 바깥 고리: MCP · Connectors · Skills · Plugins
- **노트:** "여섯 개를 분리해서 배우되, 실무에서는 하나의 흐름으로 이어집니다."

### Slide 3 — Claude란 무엇인가
- Anthropic이 만든 **최신 대규모 언어모델 제품군**
- 텍스트·이미지 입력 / 텍스트 출력 / 다국어 / 비전 지원
- 문제해결·글쓰기·학습·코딩·분석·창작에 사용
- **노트:** 현재 라인업(Opus 4.8, Sonnet 5, Haiku 4.5, Fable 5)은 등급명으로만 언급. "모델은 계속 갱신되니 최신 권장 모델을 그때그때 확인" 한마디.
- 출처: platform.claude.com/docs/en/about-claude/models/overview · claude.com/product/overview

### Slide 4 — Claude의 설계 철학: Constitutional AI
- 원칙 목록(헌법) 기반으로 **모델이 스스로 비평·수정**
- **무해성**은 사람 라벨 대신 **AI 피드백(RLAIF)**, **유용성**은 여전히 사람 피드백
- 실무 함의: "유용하지만 **검수 가능한** 동료"
- **노트:** 초보자에겐 "AI가 모르는 것·하면 안 되는 것·확인할 것을 구분하려는 설계"라고 풀이.
- 출처: anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback

### Slide 5 — Chat 기본 사용법 (좋은 질문 5요소)
- **역할 · 목표 · 자료 · 출력형식 · 검수기준**을 함께 준다
- 모호한 질문 < 맥락 있는 요청
- 예시 프롬프트:
  > "비개발자 대상 1시간 Claude 입문 강의를 준비 중이다. 핵심 개념 6개와 실습 2개를 표로 정리하고, 확인이 필요한 최신 정보는 출처와 함께 표시해줘."
- **노트:** 강점은 "한 번에 완성"이 아니라 "대화하며 점점 선명하게".

### Slide 6 — Chat에서 잘 되는 일
- 초안 작성 · 긴 글 요약 · 아이디어 정리 · 비교표 · 학습자료 변환 · 피드백/개선
- **노트:** 결과는 초안이며 **최종 검수는 사람** — 이 문장을 강의 내내 반복.

### Slide 7 — Research는 언제 쓰나
- 최신 정보 / 여러 출처 비교 / 내부자료+웹 결합 / **출처가 필요한 답**
- 방식: 여러 검색을 **순차로 이어가며 다음 조사를 스스로 판단**
- 조건: **유료 플랜(Pro·Max·Team·Enterprise), 웹 검색 ON**. Gmail·Calendar·Docs는 연결돼 있을 때 함께 활용.
- 대비: 일반 채팅(준 정보+지식) vs 웹 검색(최신 확인) vs Research(깊은 조사)
- 출처: support.claude.com/en/articles/11088861-use-research-on-claude

### Slide 8 — Claude Code란 무엇인가
- 코드베이스를 **읽고 · 파일 수정 · 명령 실행 · 개발도구 통합**하는 에이전트형 도구
- 터미널 · IDE · 데스크톱 앱 · 웹(브라우저)에서 사용
- Chat="대화로 답을 받는 곳" ↔ Code="프로젝트 폴더에서 실제 파일을 고치고 검증하는 작업자"
- 출처: code.claude.com/docs/en/overview

### Slide 9 — Claude Code 실제 사용 & 주의
- 예: "이 오류 원인 찾아 고쳐줘" / "인증 모듈 테스트 작성 후 실패 시 수정" / "README를 현재 코드에 맞게 업데이트" / "PR 변경사항 리뷰"
- **비개발자 활용:** 문서 자동화 · 웹페이지 · 자동화 스크립트 · 데이터 처리
- 주의: **변경 전후 비교 · 권한 승인 · 실행/테스트 결과 확인**
- **노트:** 파일 변경·명령 실행이 있으므로 권한 확인이 핵심.

### Slide 10 — Claude Design (베타)
- 설명한 아이디어 → 프로토타입·와이어프레임·목업·덱·마케팅 자료 초안
- **PPTX · PDF · HTML** 내보내기 / **Claude Code와 양방향 연동**(디자인→구현)
- **노트:** "예쁘게" 기능이 아니라 초안 생성·흐름 설계·브랜드 반영·출력·도구연결까지. 베타임을 명시.
- 출처: claude.com/product/design

### Slide 11 — Artifacts의 역할
- 대화·세션 결과를 **claude.ai의 라이브 인터랙티브 페이지**로 공유
- 적합: 대시보드 · 비교안 · 조사 타임라인 · PR 설명
- 제약: **백엔드 앱 아님. 하나의 자체 포함 페이지.** ("완전한 웹앱"이라 말하지 않기)
- 출처: code.claude.com/docs/en/artifacts

### Slide 12 — MCP를 아주 쉽게
- AI ↔ 외부 도구·데이터를 잇는 **개방형 표준**
- 서비스마다 따로 연결하던 것을 **하나의 표준 프로토콜**로
- 비유: Claude=똑똑한 사람 / MCP=문서함·업무툴·DB에 들어가는 **출입 규격**
- **노트:** 업계 공동 표준으로 확산 중(구체 거버넌스는 강의 직전 공식 페이지 확인).
- 출처: anthropic.com/news/model-context-protocol · code.claude.com/docs/en/mcp

### Slide 13 — Connectors란
- Claude가 Google Drive · Slack · Linear · GitHub 등 **실제 앱에 접근·검색·작업**
- 예: Drive 파일 검색 · Slack 메시지 전송 · Linear 이슈 생성
- **연결 서비스의 사용자 권한을 그대로 상속** (원래 못 보는 파일은 Claude도 못 봄)
- 출처: support.claude.com/en/articles/11176164-use-connectors...

### Slide 14 — Remote Connector vs Desktop Extension
| 상황 | 선택 |
|---|---|
| 클라우드/SaaS(Slack·Notion·Linear·GitHub) | **Remote connector** (연결 후 여러 표면에서 사용) |
| 로컬 파일·로컬 DB·데스크톱 앱·OS 접근 | **Desktop extension** (기준점=Claude Desktop 앱) |
- **노트:** 원격 세션의 로컬 파일 접근은 데스크톱 앱이 열려 있을 때만.
- 출처: support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors

### Slide 15 — Skills란
- 반복 절차를 **`SKILL.md`**로 만들어 재사용
- 관련될 때 **자동 호출** 또는 **`/skill-name`** 직접 호출
- 예: `/review-pr` · `/deploy-staging` · `/summarize-changes` · `/lesson-plan`
- 출처: code.claude.com/docs/en/skills

### Slide 16 — Plugins란
- **스킬·에이전트·훅·MCP 서버를 묶은** 확장 기능
- 팀 공유 · 버전 관리 · 여러 프로젝트 재사용 · 마켓플레이스 배포
- 충돌 방지용 **namespaced 명령**(`/plugin:skill`)
- 출처: code.claude.com/docs/en/plugins · .../discover-plugins

### Slide 17 — 네 개념 비교 (⭐핵심 표)
| 개념 | 한 줄 정의 | 초보자 비유 | 예시 |
|---|---|---|---|
| **MCP** | AI–도구 연결 표준 | 공용 콘센트 규격 | Drive·Slack·GitHub 연결 기반 |
| **Connector** | 실제 앱 연결 | 로그인된 출입문 | Drive 검색·Slack 전송·Linear 이슈 |
| **Skill** | 반복 절차 지침 | 업무 매뉴얼 | PR 리뷰·배포 체크리스트 |
| **Plugin** | 확장 기능 묶음 | 팀 도구 패키지 | 스킬+에이전트+MCP 묶음 |
- (보너스) **Subagent** = 보조 작업(검색·로그·파일읽기)을 별도 컨텍스트에서 하고 **요약만** 돌려주는 작업자.

### Slide 18 — 시나리오 ①: 기획자·마케터
1. Chat으로 요구사항 정리 → 2. Research로 시장·경쟁 조사 → 3. Design으로 화면/덱 초안 → 4. Connector로 Drive 자료 반영 → 5. Artifact로 비교안 공유

### Slide 19 — 시나리오 ②: 개발팀
1. GitHub/Linear 티켓을 Connector로 불러오기 → 2. Claude Code로 코드베이스 조사 → 3. Subagent로 대규모 검색 분리 → 4. 코드 수정·테스트 → 5. PR 설명·리뷰 체크리스트 생성

### Slide 20 — 시나리오 ③: 교육·콘텐츠
1. Chat으로 강의안/캠페인 구조 → 2. Research로 최신 근거 → 3. Design으로 덱·원페이지 초안 → 4. Connector로 내부 문서 반영 → 5. PDF/PPTX 내보내기

### Slide 21 — 안전하게 쓰는 법 (⭐체크리스트)
- 출처 필요한 정보는 **Research/웹 검색으로 확인**
- 연결 권한은 **최소한**으로 허용 (읽기 우선, 쓰기·삭제는 승인형)
- 민감정보 업로드 전 **조직 정책 확인**
- 코드·문서는 **사람이 최종 검수**
- AI 생성물엔 **확인일 + 출처** 표기

### Slide 22 — 마무리 & 실습
- 핵심: Chat=시작점 · Research=근거 · Code/Design=결과물 · MCP/Connector/Skill/Plugin=연결·확장
- 확장 순서 권장: **Chat → Research → Connector → Design/Code → Skill/Plugin**
- "기능을 다 배우지 말고, **내 업무 하나를 골라 작은 반복 흐름**부터."

---

## 4. 실습 2종 (+ 진행자용 정답 키)

**실습 1 — 좋은 프롬프트 만들기 (3분)**
- 나쁜 예: "Claude 강의안 만들어줘."
- 좋은 예: "초보자 대상 · 1시간 · 비개발자 70% · 실습 포함 · 출처 필요 · PPT 목차와 발표자 노트로 작성해줘."
- 채점: 역할/목표/자료/출력형식/검수기준 5요소 포함 여부.

**실습 2 — 개념 분류 (3분)** 아래 요청이 Chat/Research/Code/Design/Connector/Skill/Plugin 중 어디에 가까운가?

| 요청 | 정답 |
|---|---|
| "이 40페이지 PDF를 3문단으로 요약해줘" | Chat |
| "최신 규제 3개를 출처와 함께 비교해줘" | Research |
| "이 저장소 버그를 찾아 고치고 테스트해줘" | Code |
| "제품 소개 피치덱 초안을 만들어줘" | Design |
| "우리 Slack 채널에 요약을 전송해줘" | Connector |
| "매주 하는 배포 점검 절차를 재사용하게 만들어줘" | Skill |
| "팀 전체가 쓸 리뷰 도구 세트를 배포하고 싶어" | Plugin |

---

## 5. 핵심 문장 5개 (마무리/요약 슬라이드용)
1. Claude는 답변 생성기가 아니라 업무 맥락을 함께 다루는 **AI 파트너**다.
2. **Chat**은 시작점, **Research**는 근거, **Code·Design**은 결과물을 만든다.
3. **MCP**=연결 표준, **Connector**=실제 앱 연결, **Skill**=반복 절차, **Plugin**=확장 묶음.
4. Claude가 외부 도구에 연결될수록 **권한 확인과 검수**가 더 중요해진다.
5. 초보자는 기능을 다 배우려 말고 **자기 업무 하나의 작은 반복 흐름**부터 만든다.

---

## 6. 출처 목록 (공식만)
1. Claude 제품 개요 — claude.com/product/overview
2. Models overview — platform.claude.com/docs/en/about-claude/models/overview
3. Constitutional AI — anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback
4. Use research on Claude — support.claude.com/en/articles/11088861-use-research-on-claude
5. Claude Code Overview — code.claude.com/docs/en/overview
6. Claude Design — claude.com/product/design
7. Artifacts — code.claude.com/docs/en/artifacts
8. Introducing MCP — anthropic.com/news/model-context-protocol
9. Claude Code MCP — code.claude.com/docs/en/mcp
10. Use connectors — support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
11. Custom connectors (remote MCP) — support.claude.com/en/articles/11175166...
12. Desktop vs web connectors — support.claude.com/en/articles/11725091...
13. Skills — code.claude.com/docs/en/skills
14. Discover plugins — code.claude.com/docs/en/discover-plugins
15. Create plugins — code.claude.com/docs/en/plugins
16. Subagents — code.claude.com/docs/en/sub-agents

---

## 7. 환각 방지 메모
- 본 기획안은 2026-07-14 기준 공식 문서·제품 페이지 교차검증 결과다.
- **가격·플랜별 제한·모델명·베타 범위·MCP 거버넌스**는 강의 직전 공식 페이지에서 재확인.
- 금지 표현: "Claude가 모든 외부 앱에서 모든 작업을 할 수 있다" / "Artifacts는 완전한 웹앱이다".
- Claude Design은 **베타 제품**으로 설명.
- 실제 통계·인용을 지어내지 않는다. 슬라이드에 **모델 ID는 넣지 않고 등급명만** 사용.
