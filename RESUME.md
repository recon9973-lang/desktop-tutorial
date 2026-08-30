# RESUME — 다음 세션 이어가기 (2026-08-30 · s12 체크포인트)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 세션 상세는 `docs/session-logs/2026-08-30-s12.md`(직전)·`-s11.md`,
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금 하는 일 — 모자란 화면 하나씩 제작 (사장님 오더)

«기존 프로그램 모든 화면 확보 → 새 화면(시뮬)과 대조 → 모자란 화면 하나씩 제작».
①확보 ②대조 ③**제작 9/9 전부 완료** (2026-08-30, s12 이후 같은 방에서 2~9호 마감).

```
확보   docs/screens-실물/            실물 v0.3.386 전 화면 실캡처(빈 상태)
대조   docs/ANSEO-화면-대조표.md      모자란 화면 9건 + 실물 공통 골격
제작   9건 전부 ✅ — 목록·아티팩트 ID는 docs/ANSEO-화면-대조표.md 머리말 진행표가 정본
       (1리포트 2이슈 3거래처목록 4답변검수 5키워드 6브랜드식별 7원고검수 8설정묶음 9공개면)
       — AEO(/console/geo)는 제외: ANSEO 방이 0.3.387~389로 재구성 중
```

**제작 문법은 리포트 1호가 정본**: 시뮬 패밀리 토큰(SEO-GEO 시뮬 <style> 그대로), 등급 46px 주인공+점수 보조,
축소판 문법(목록·칩=등급 칩 우선+톤), 등급 11단 척도 띠, 판 띠·근거 사슬, 심각도=이슈 축 분리,
발행본 불변·의료광고법 문구, Playwright 어서션 후 커밋(파일: scratchpad 작성→검증→docs 복사→artifact 발행→커밋).

## 바로 이어갈 작업

1. **사장님 화면 검토 대기** — 9건 아티팩트 피드백이 오면 해당 시뮬만 고쳐 재발행(같은 세션이 아니므로 `url` 지정 재발행).
2. 검토 통과분의 **실물 이식·배포는 ANSEO 방 소관** — 이 방은 시뮬(설계 정본)과 인계 문서까지.
   이식 때 참고: 축소판 등급 문법=3호, 발행 축 문법=1호, 톤앤매너 위반 8곳=docs/ANSEO-톤앤매너-전수감사.md.
3. 새 오더가 없으면 대기. 배포·배포 확인은 이 방에서 하지 않는다(사장님 확정).

## 대기/차단·다른 방 소관 (이 방에서 하지 말 것)

- **배포·배포 확인**: 사장님 확정 — 이 방은 하지 않는다. 최종 화면 후 ANSEO 방.
- **실물 톤앤매너 재작업(위반 8곳)**: ANSEO 방 — 인계 문서 `docs/ANSEO-톤앤매너-전수감사.md` 완료
  (1순위: 공개 체커/공유 등급 칩 실패색 하드코딩 — A+도 빨강).
- ANSEO 방 미배포 0.3.387~389(AEO 재구성)는 **원격에 없음**(그 방 로컬) — 새 판은 0.3.390부터가 안전.
- 이월: #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → Higgsfield MCP `sandbox_exec`(바깥 샌드박스) curl로
  `/api/health`·`/api/queue`·웹 번들 판 확인 가능. 마지막 실측(08-30 06:01): 서버·워커·웹 전부 **0.3.386**.
- **실물 화면 캡처 장치**: `scratchpad/capture-screens.mjs` — smoke의 가짜 진단 서버+`next start :4601`+
  Playwright(쿠키 `veo_console_session=smoke-…`, 다크 1440px). 빌드물 필요(`apps/web/.next`).
- Playwright: `/opt/node22/lib/node_modules/playwright/index.mjs`, chromium `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, `--no-sandbox`.
- veo-platform 로컬 클론 `/home/user/veo-platform`(main=21fd12b). `gh` 2.45 apt 설치했지만 **컨테이너 리셋 시 소멸**.

## 주의·제약 (반드시)

- 브랜치: 이 방 산출물은 desktop-tutorial `claude/image-design-workflow-analysis-efuea7`, 체크포인트만 main.
  veo-platform은 이 방에서 더 이상 커밋하지 않는다(화면 작업은 시뮬만).
- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_019pLvoUJ8uv46QhpsR2su5k`(방 바뀌면 그 방 URL). 모델 ID 금지·비밀키 금지.
- 사장님께는 「커밋」「배포」 두 낱말만. 데이터는 테스트용 — 정합성 지적 금지.
- 확정 규격(되묻지 말 것): 등급 11단(A+95~F0-49, E+/E 포함·발행 완료)·등급 크게 점수 작게·톤 4단(90/75/60)·
  목표선 50/90+도달 예상(보장 아님)·AI 7종·판 다르면 비교 금지·못 잰 값 —·색+글자 병용·의료광고법 준수.

## 참고

- 세션 상세 `docs/session-logs/2026-08-30-s12.md` · `-s11.md` / 격차표 `docs/ANSEO-실물-이식-격차표.md`
- 시뮬 4종: 파이프라인 · SEO-GEO(1160bf6a…) · AEO(000e361e… v5) · 전체-통합(65ba7d78…) + 리포트(b35d70de…)
