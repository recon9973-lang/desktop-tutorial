# RESUME (경쟁사·업종 방) — 2026-09-11

> **이 파일은 「경쟁사·업종 방」 것이다.** 루트 `RESUME.md`(진단 오진 방) ·
> `RESUME-aeo-grand.md`(자동 진단 방) · `RESUME-ring-loader.md`(링 로더 방)을 **덮지 않는다.**
> 상세는 `docs/session-logs/2026-09-11-s23.md`. 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

사장님 물음 — *"여긴 병원이 아니라 마케팅인데, 왜 병원이 경쟁사로 나오지?"*

AEO 콘솔 「우리가 빠진 답변엔 누가 나오나」가 **업종을 안 넘겨** `names_in` 이 MEDICAL 로
떨어졌다. 병원 꼬리로만 이름을 뽑으니 마케팅 거래처 화면에 병원 다섯·「센터」 셋이 서고
경쟁 대행사는 0곳이었다. **자료가 그런 게 아니라 체가 병원 모양이었다.**

**고침은 `veo-platform` 가지 `claude/rival-names-by-industry` 에 있다 — 커밋 셋, 미배포.**

```
5b4f09e  업종을 넘긴다(run_rivals·auto_register) + 마케팅·광고 업종 신설(꼬리 12)
4f6ca7a  다음 판을 대장 §4-B 에 적는다 (자료화 + 유추)
176d6d0  비교 대상에서 빼는 단추 (끌 자리가 화면에 없었다)

관문   ci-local 7,423 통과 · 웹 292파일 2,550 통과 · tsc 0 · next build 성공
```

## 바로 이어갈 작업

1. **다음 판 — 업종을 코드에서 자료로 빼고, 기타면 홈페이지에서 읽는다.**
   대장 `docs/WORKLIST.md` **§4-B** 에 순서·경계가 적혀 있다. 사장님 확정 사항:
   ```
   자료화   IndustryProfile 을 YAML 로 · 화면 목록은 서버가 내려준다(GET /industries)
   유추     기타·빈 값이면 brands/discovery.py 가 읽는 홈페이지(schema.org @type·
            제목·본문)로 고른다. 화면이 「추정」이라 말하고 근거를 낸다. 못 읽으면 «—»
   드롭다운  업종을 빼지 않는다 — 유추가 틀렸을 때 고칠 자리
   경계     MEDICAL 은 특별 취급이 남는다(/console/medical 게이트·심평원 카드)
   ```
2. **배포 상태 확인** — 대기 표 두 줄(0.3.564 다른 방 + 이 건)이 나갔는지.
   나갔으면 사장님께 ① 업종을 마케팅·광고로 ② 재진단 ③ 병원 다섯 빼기 를 안내한다.

## 대기/차단

- **배포는 ANSEO 방 몫**(사장님 지시 2026-09-09). 만드는 방은 **검사까지만** 하고 가지를
  넘긴다 — 이 방에서 `make deploy` 를 돌리지 않는다. 승인은 **모아서 한 번에**(2026-09-01).
- **사장님 몫** — 거래처 「베놈」 업종을 📣 마케팅·광고 로 바꿔야 고침이 효력을 낸다.
  지금 값은 「기타」다(2026-09-11 사장님 화면).
- **이 방은 운영을 못 잰다** — 운영 DB·운영 주소 egress 403. 실제 답변 본문 대조,
  도는 판 확인 전부 «—».
- **veo-platform 은 `add_repo` 로 붙인다**(owner `recon9973-lang`) → `/home/user/veo-platform`.
  환경: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install --frozen-lockfile` ·
  `service postgresql start` · `su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""` ·
  `PGPASSWORD=veo PGUSER=root make ci-local`.

## 주의·제약

- **못 재는 자리에서는 가설을 가설이라고만 말한다.** 이번에 「대구병원」이 잘린 말이라는
  가설을 정규식으로 직접 돌려 **실측으로 바꿨다**. 그 전까지는 가설로만 말했다.
- **MEDICAL 쪽 「대구병원마케팅 → 대구병원」 잘림은 안 고쳤다**(대장 §4-A). 이미 잘린
  뒤라 끝으로 못 거르고, 뒤 글자를 보는 규칙은 병원 거래처 **전부**의 이름 뽑기를 바꾼다.
- 대장 규칙: 무엇을 끝내면 그 자리에서 `docs/WORKLIST.md` 를 고친다(`tests/ledger/` 가 막는다).
  줄 상한 1,300(지금 1,255). 새 일감은 대기 표에 **판 번호 없이**(`—`) 쌓는다.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01NDFshUT74yv9JzuQyXmQSk`. 모델 ID 는 트레일러에만.
- 이 저장소(desktop-tutorial)의 가지는 `claude/stoic-fermi-i01mg7` 다. 다른 가지로 밀지 않는다.

## 참고

- 콘솔 코드 자리: `apps/api/src/veo/observations/rivals.py` · `mention_roster.py` ·
  `industries/registry.py` · `competitors/auto_register.py` ·
  `apps/web/src/lib/industries.ts` · `.../console/competitors/BrandForm.tsx`
