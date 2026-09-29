# RESUME (진단 링 투명 파일 방) — 2026-09-29 · **ANSEO 방에 인계 대기**

<!-- 가지: claude/affectionate-pasteur-3r1867 -->

> **이 방이 고친 것은 ANSEO(veo.seokorea.org)** 다 — 저장소 `veo-platform`(`add_repo` 로 붙임).
> 이 저장소(베놈 사이트)에는 코드 변경이 없다. 이 파일은 방 인계본이다.

## 무엇을 했나

사장님 2026-09-28 «진단 애니매이션이 갑자기 왜 이렇게 나오지? 4각 틀이 보이네?» → 원인은 사이트가
아니라 사장님 브라우저가 링 영상을 합성(섞기·마스크) 없이 바로 얹은 것 [실측: 캡처 귀퉁이 30~32 < 뒤 화면 54].
사장님 «ANSEO 맞아, 투명 파일로 바꿔서 배포해줘» → 링 파일 자체를 투명(VP9+알파 · 포스터 webp)으로.

```
veo-platform 가지  claude/ring-alpha-file   (origin/main f614a10b · 0.3.665 위)
인계 문서          docs/HANDOFF-2026-09-29-ring-alpha-to-anseo.md
대장               docs/WORKLIST.md §2 배포 대기 표에 — 줄(가지 적음)
검사 [실측 09-29]  vitest 342/2,934 통과 · tsc 0 · eslint 0 · next build 성공
```

## 남은 것

- **배포는 ANSEO 방 몫**(사장님 09-20 · 관문 `deploy_room_gate.sh`). 이 방은 `make deploy` 를 돌리지 않았다.
  사장님이 ANSEO 방에 「인계」 한 마디 하시면 그 방이 가지를 합쳐 낸다.
- 배포 뒤 사장님 브라우저에서 진단 한 번 — 네모가 사라졌는지 그 자리에서 난다.
