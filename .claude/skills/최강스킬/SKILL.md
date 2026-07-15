---
name: 최강스킬
description: >-
  프로젝트 연속성·토큰 절약 통합 시스템을 현재 저장소에 설치한다. PROJECT_STATE 자동 생성기 + CI,
  세션 자동 체크포인트(20건)·핸드오프(RESUME.md), /compact·/clear 안내 훅, CLAUDE.md 지침을
  한 번에 깔아 "재탐색 낭비 없음 + 세션 무한 연속"을 만든다. "최강스킬", "시스템 설치",
  "이 저장소에도 적용", "프로젝트 세팅", "연속성 시스템", "토큰 절약 시스템"에 반응.
  모든 프로젝트에 동일 규격으로 드롭인하기 위한 설치 스킬.
---

# 최강스킬 — 프로젝트 연속성·토큰 절약 시스템 설치기

이 스킬은 **아래 시스템을 현재(target) 저장소에 설치**한다. 목적: 매 세션 반복되는 재탐색(grep/read 남발)을
없애고, 토큰이 쌓여도 세션을 안전하게 인계해 **끊김 없이 이어가게** 한다.

## 설치되는 구성요소
1. **PROJECT_STATE 자동화** — `scripts/gen-project-state.mjs`(저장소 스캔→`PROJECT_STATE.md`) + `.github/workflows/project-state.yml`(push마다 갱신). 새 세션은 이 1파일로 오리엔테이션.
2. **세션 체크포인트·핸드오프** — `.claude/skills/checkpoint/` 스킬. 20건 도달 시 문서화→TODO→`RESUME.md` 생성·커밋→`/clear` 안내.
3. **자동 감지 훅** — `.claude/hooks/count-prompts.sh`(UserPromptSubmit: 10건 `/compact` 권장·20건 checkpoint), `.claude/hooks/load-resume.sh`(SessionStart: `RESUME.md` 자동 주입). `.claude/settings.json`에 등록.
4. **CLAUDE.md 지침** — 세션 시작 시 `RESUME.md`·`PROJECT_STATE.md` 먼저 읽기 + compact/checkpoint 정책.

## 컨트롤 센터 (정본 위치)
정본 파일은 **`desktop-tutorial`** 저장소에 있다(경로 동일). 세션에 `desktop-tutorial`이 있으면 **거기서 복사**하는 것이 가장 정확하다.

## 설치 절차

### 1. 대상 저장소 확인
현재 작업 중인(설치할) 저장소 루트를 확인한다. `desktop-tutorial` 자체면 이미 설치돼 있으니 최신화만.

### 2. 파일 배치 (desktop-tutorial → 대상 저장소)
`desktop-tutorial`이 로컬에 있으면 아래를 그대로 복사:
```
scripts/gen-project-state.mjs
.github/workflows/project-state.yml
.claude/skills/checkpoint/SKILL.md
.claude/hooks/count-prompts.sh
.claude/hooks/load-resume.sh
.claude/settings.json         # 이미 있으면 hooks 키만 병합(덮어쓰기 금지)
```
`desktop-tutorial`이 없으면: 그 저장소를 참조(add_repo)하거나, 위 파일들을 정본과 동일하게 재작성한다.
`gen-project-state.mjs`는 **무의존·범용**이라 어느 저장소에서도 그대로 동작한다.

### 3. settings.json 병합 (중요)
대상에 `.claude/settings.json`이 이미 있으면 **`hooks` 키만 병합**한다(다른 설정 보존):
```json
{
  "hooks": {
    "UserPromptSubmit": [ { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/count-prompts.sh\"" } ] } ],
    "SessionStart":    [ { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/load-resume.sh\"" } ] } ]
  }
}
```

### 4. CLAUDE.md 지침 추가
대상 저장소의 `CLAUDE.md`(없으면 생성) 최상단에 "세션 시작·인계 시스템" 블록을 추가한다
(RESUME·PROJECT_STATE 먼저 읽기 + /compact·checkpoint 정책). 정본은 `desktop-tutorial/CLAUDE.md` 참조.

### 5. 실행 권한 + 생성 + 커밋
```
chmod +x .claude/hooks/*.sh
node scripts/gen-project-state.mjs         # PROJECT_STATE.md 생성 확인
```
검증(훅 구문 `bash -n`, settings.json JSON 유효) 후, 대상 저장소의 작업 브랜치에 커밋·푸시.
커밋 트레일러 규칙 준수. 비밀키·모델ID 미포함.

### 6. 확인 안내
설치 후 사용자에게:
> ✅ 최강스킬 설치 완료 — PROJECT_STATE 자동화 + 세션 체크포인트/핸드오프 + compact/clear 훅.
> 다음 세션부터 `RESUME.md`·`PROJECT_STATE.md`로 즉시 이어가고, 20건마다 자동 인계됩니다.

## 원칙
- 상태는 **반드시 git**(컨테이너는 세션마다 초기화).
- `/compact`·`/clear`는 슬래시 명령이라 **사용자가 직접 입력** — 시스템은 정확한 타이밍에 안내만.
- `PROJECT_STATE.md`는 자동 생성물 — 직접 수정 금지, 생성기/CI로만 갱신.
- 값·비밀은 어떤 산출물에도 넣지 않는다(env는 이름만).

## 관련 스킬
- `checkpoint` — 실제 인계 실행(이 시스템의 핵심 동작). 최강스킬은 그 설치·배포를 담당.
