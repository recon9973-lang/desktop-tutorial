# 서브에이전트 팀 (Claude + ChatGPT 2인 체제)

> 전 프로젝트에서 재사용하는 6명 서브에이전트. Claude가 만들고 GPT가 감시하는 **어드버서리 팀** 구조.

## 팀 편성

| # | 에이전트 | 주 AI | 역할 | 견제 |
|---|---|---|---|---|
| 1 | `planner` | Claude Sonnet | 기획·명세·PRD | GPT가 놓친 요구사항 지적 |
| 2 | `frontend-dev` | Claude Sonnet | React/Vue/Tailwind/퍼블리싱 | GPT가 접근성·SEO 감시 |
| 3 | `backend-dev` | Claude Sonnet | API·DB·서버 | GPT가 엣지케이스·주입 감시 |
| 4 | `security-auditor` ⚠️ | **GPT-5 주도** + Claude 재검증 | OWASP·해킹·비밀키 (Read-only) | 이중 감사 |
| 5 | `code-reviewer` | **GPT-5** | 코드 리뷰·리팩터·명세 대조 | 개발자와 다른 AI = 진짜 견제 |
| 6 | `researcher` | Claude Haiku + GPT 교차 | 조사·팩트체크·실측 | 삼각 검증 |

## 견제 패턴

- **A. Adversarial Pair**: Claude 작성 → GPT 리뷰 → Claude 수정
- **B. Double Audit**: 보안은 Claude+GPT 병렬 → 교집합=P0
- **C. Fact-Check Triangle**: WebSearch + Claude + GPT 3중 검증

## 파일

```
.claude/agents/          # 서브에이전트 정의 (프로젝트+글로벌 하이브리드)
scripts/ai/
  ask-gpt.sh             # OpenAI API 래퍼
  install-ai-tools.sh    # SessionStart 훅 (컨테이너 리셋 대응)
docs/subagents/
  README.md              # 이 문서
  ORCHESTRATION.md       # 팀장(오케스트레이터) 규칙
```

## 필수 환경변수

- `OPENAI_API_KEY` — Claude Code Web의 **Environment Variables**에 등록.
  - 없으면 GPT 감시자는 자동으로 비활성 (Claude 단독 모드로 폴백, "견제 약함" 표기).

## 설치·재설치

컨테이너 리셋시 SessionStart 훅이 자동 재설치. 수동으로도 가능:
```bash
bash scripts/ai/install-ai-tools.sh
```
