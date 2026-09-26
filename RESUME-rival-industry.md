# RESUME (경쟁사·업종 방) — 2026-09-26 · **이 방 일은 끝났다**

> **이 파일은 「경쟁사·업종 방」 것이다.** 루트 `RESUME.md`(진단 오진 방) ·
> `RESUME-aeo-grand.md` · `RESUME-ring-loader.md` 를 **덮지 않는다.**
> 상세는 `docs/session-logs/2026-09-17-s26.md` → `2026-09-16-s25.md` → `2026-09-15-s24.md`.

## 결말 — 넘긴 것 전부 나갔다

```
[실측 2026-09-26 · git · origin/main 6654dcc1 · 판 0.3.657]
0.3.566  나갔다  빠진 답변의 이름을 업종 따라 뽑는다 + 마케팅·광고 업종 + 비교 대상 빼는 단추
0.3.585  나갔다  업종을 코드에서 자료로 + 기타면 홈페이지에서 읽는다(추정·근거)
0.3.595  나갔다  「대구병원마케팅」에서 「대구병원」이 잘리던 것
0.3.603  나갔다  ① 도는 판이 어디 있는지 화면이 말한다  ② 기다림에 끝을 둔다
                 (21ba0f20 이 main 의 조상 · 합친 커밋 4d7e6c99)
```

**대장 대기 표에 이 방 줄은 없다** — 머리말은 「미배포 없음」이고 `job-says-where-it-is`
흔적도 0건이다. 이 방이 만들어 둔 문서 가지 둘은 **더 볼 것 없다(무효)**:

```
claude/worklist-after-0-3-604   나간 줄 넷 빼기 — 다른 방이 그 사이 같은 자리를 정리했다
claude/worklist-drop-shipped-rows  더 오래된 같은 일 — 번호가 배포마다 다시 찍혀 낡았다
```
둘 다 **넘기지 않는다.** 필요하면 최신 main 기준으로 새로 만든다.

## 이 방이 남기는 것 — 아직 안 잡힌 원인 하나

두 판은 **증상을 보이게** 했을 뿐, **왜 재진단이 멈췄는지는 안 고쳤다.**
다시 멈추면 이 순서로 좁힌다.

```
① 링 아래 한 줄을 읽는다 (0.3.603 부터 화면이 스스로 말한다)
     「질문 준비」                 정상 — 돌기 시작했다
     「차례를 기다리는 중입니다」   아무도 안 집어갔다
     「아직 시작하지 못했습니다」   집혔는데 아무도 안 돌린다   ← 브로커 어긋남의 모습
     「내보내지 못했습니다 (n/5)」  다섯 번째에 실패로 끝난다(사람이 다시 누를 수 있다)
② https://veo-platform-production.up.railway.app/api/queue  → workers 가 0 이면
   「보내는 곳에 아무도 없다」가 확정. 코드가 아니라 Railway 설정이다(API·워커가 다른 브로커).
   같은 사고가 운영에서 2026-08-18·08-19·08-20 세 번 났다.
```

## 이 방이 만진 자리 (다음 방이 같은 곳을 건드릴 때)

```
자료   packages/shared-types/industries.json   업종 추가 = 여기 한 칸
서버   industries/{registry,schema,inference}.py · observations/mention_roster.py
       jobs/service.py(begin·stage_at_start) · jobs/release.py(까닭·상한·claim)
화면   lib/industries.ts · competitors/{SiteIdentityPicker,BrandForm}.tsx
       geo/JobWatch.tsx(링 아래 한 줄)
이미지 infra/docker/{api,worker}.Dockerfile — 싣고(COPY) 가리킨다(ENV)
```

## 배운 것 셋 (이 방에서 값을 치른 것)

- **화면 글자는 「서버가 한 말」과 「빈자리」를 갈라 써야 한다.** 「준비」가 그 둘을 뭉개
  9분 30초를 못 가렸다. 새 글자를 넣을 땐 「이것은 누가 말한 것인가」를 먼저 답한다.
- **되돌리기에는 상한을 둔다.** 매 주기 되돌리는 코드는 사고를 숨긴다 — 끝이 없으면
  화면이 영원히 돈다.
- **못 잰 것은 못 쟀다고 적는다.** 이 방은 운영에 못 닿는다(egress 403).

## 제약 (바뀌지 않았다)

- 배포는 **ANSEO 방** 몫. 만드는 방은 **검사까지만**(`make preflight` 는 배경으로 돌린다).
- 판 번호는 미리 물리지 않는다 — 대기 표에 `—` 로 쌓고 머리말에 「번호 미정 N건」.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01NDFshUT74yv9JzuQyXmQSk`.
- 이 저장소(desktop-tutorial)의 가지는 `claude/stoic-fermi-i01mg7`.
