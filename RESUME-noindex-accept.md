<!-- 가지: claude/fervent-fermat-ahf55p -->
# RESUME (noindex 인정 방) — 2026-09-24 · 오더 5건 · **낱말 고침 하나 인계 대기**

## 한 줄
사장님 물음 「noindex 를 인정하는 단추」 → ① 연구 보고 → ② «1번부터 4번까지 다 해줘» → 넷 다
ANSEO(`veo-platform`)에 만들어 인계 → ③ «ANSEO 방으로 인계해서 배포해» → **확인해 보니 ANSEO 방이
이미 받아서 냈다.** 이 방이 할 일은 없다.

## 무엇이 나갔나 [실측 2026-09-23 · veo-platform `origin/main` · 배포 오더 기록]
- 이 방 가지 `claude/fervent-fermat-ahf55p`(커밋 `d8ce209a`)를 ANSEO 방이 **`b233fd57`** 로 합쳐
  **0.3.646** 에 실어 냈다(2026-09-22 14:08 KST · 오더 «배포 — 셋 한 판으로 묶어»).
- 그 뒤 판: 0.3.647 · **0.3.648**(noindex 이슈 방 — 이슈 탭에서도 체크 · 인정 주소 표시 · 이슈 자동 닫힘 ·
  `NoindexExclusions` 를 `components/` 로 옮김) · **0.3.649**(ANSEO 방 — 사장님 09-22 화면 지적으로
  「지정」 낱말을 **「감점 해제」** 로 통일: 「고른 N개 감점 해제」·「이 해제로 지금 다시 진단」·「해제 되돌리기」).
- ANSEO 방 실측: 서버·워커·웹 **0.3.649** (2026-09-23 01:12 KST · `docs/STATE.md`). 이 방 사본에서는
  운영 주소가 403 이라 직접 못 쟀다(«—»).
- 넷 다 main 에 살아 있다: 다시 진단 단추 · 걸린 줄 옆 링크(작업 큐·조치 카드·GEO 항목·이슈 탭) ·
  풀기(=해제 되돌리기) · GEO 화면 칸.

## 2026-09-24 · 오더 ④⑤
- ④ «화면 니가 확인해» → 운영은 러너 「도는 판 확인」으로 **0.3.653**(웹·서버·워커) 실측. 화면은 `veo-platform/apps/web/test/smoke/shoot.mjs`
  (가짜 진단 서버 + noindex 4개 표본)로 main 코드를 띄워 찍음 — 넷 다 살아 있음. 찍는 법: `SHOOT_FIXTURE`·`PLAYWRIGHT_MODULE`(playwright 1.56.1 · 브라우저 `/opt/pw-browsers`).
- ⑤ «풀기를 해제 되돌리기로 바꿔» → **가지 `claude/fervent-fermat-ahf55p-wording`** · 커밋 `6b239e7f` · 잠정 판 **0.3.654** · 인계
  `veo-platform/docs/HANDOFF-2026-09-24-noindex-wording-to-anseo.md` · 대장 §2 0.3.654 줄. **배포는 ANSEO 방 몫 — 인계 대기.**

## 이 저장소
- 보고서 `docs/2026-09-21-noindex-인정-연구보고.md` 와 이 인계본은 noindex 이슈 방의 #279 로 main 에
  이미 들어갔다(내용 동일). 이 가지는 main 이 강제 갱신돼 뒤처져 있다 — 합칠 것 없음.

## 다음 오더가 오면
- 이 기능 관련 새 오더는 **noindex 이슈 방**(`RESUME-noindex-issues.md` · 가지 `claude/beautiful-heisenberg-szdc5b`)
  과 겹치지 않게 그쪽 인계본부터 읽는다.
- 화면 낱말은 이제 「감점 해제」다. 「지정」이라 부르지 않는다.
- 「실제 noindex 가 있어야 뺀다」 규칙은 그대로.
