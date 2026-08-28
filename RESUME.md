# RESUME — 다음 세션 이어가기 (2026-08-28 · s09 · 미배포 열세 판)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 이번 세션 상세는
> `docs/session-logs/2026-08-28-s09.md`, 현황은 `PROJECT_STATE.md`.

## 지금까지 (핵심만)

`veo-platform` 에 판 넷을 올렸다. **전부 커밋·푸시됐고 아직 배포 안 됐다.**

```
가지  claude/wonderful-einstein-1qiqm5   (veo-platform · desktop-tutorial 둘 다)

e3c08e8  0.3.365  로그인 없는 창구·안내판을 기본으로 닫는다
08545be  0.3.366  등급을 다섯에서 아홉으로 — A+~F (명세 SEO 1.11.0 · GEO 1.5.0)
dd55f6e  0.3.367  크롬 워커 — 페이지를 실제로 그려 본다 (기본 꺼짐)
9ff5ed5  0.3.368  우리 자와 구글 자를 나란히 놓는 도구
```

**사장님이 브라우저로 잡아 주신 것**: 운영 `GET /docs` 가 200 이었다. 공개 진단
화면은 진작 접혀 있었는데 **서버 창구만 붙어 있었다.** 0.3.365 가 닫았다 — 다만
공유 리포트 읽기(`/results/{토큰}`)는 같은 라우터에 있어서 갈라 내어 살렸다.

## 바로 이어갈 작업

1. **배포** — ANSEO 방으로 **이관 완료**(2026-08-28). 런북 `docs/ANSEO-배포-인계.md`
   가 이번 열세 판 기준으로 갱신돼 있다 — ANSEO 방은 그 문서 하나만 읽으면 된다.
   ⚠ 요지: §0 운영 판을 먼저 잰다(git main 은 0.3.364 인데 운영 마지막 실측은
   0.3.355) · §3 워커 이미지가 이번부터 크롬을 싣는다(첫 빌드 주의) · §4 배포 뒤
   확인 셋(/docs 404 · 진단 창구 404 · 공유 링크 생존).
2. **비교표 뽑기** — 바깥이 열린 자리에서:
   `python apps/api/scripts/compare_lab_measurements.py <거래처 주소> --runs 3 --key <PageSpeed 열쇠>`
   이 표가 다음 명세 판(성능 출처 교체)의 **근거**다. 이 방은 프록시가 막아 못 돌린다.
3. 그 표를 보고 **성능 출처를 우리로 옮길지** 정한다(새 명세 판 필요 · ADR 0010).

## 대기/차단 (사용자 액션)

- **배포** — 이 방은 `gh` 없음 · 운영 API curl 403.
- **렌더러 켜기** `VEO_RENDERER_ENABLED=true`(워커) — 크롬 실은 이미지가 나간 뒤.
  켜면 `js_render_parity` 가 판정을 받기 시작하고 **그 항목은 관문이라 곱해진다** —
  자바스크립트로 본문을 그리는 사이트의 점수가 내려갈 수 있다.
- 이월: #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드 ·
  B-16⑶ `VEO_REDIS_URL`(공개 한도 공유 — 창구를 닫았으므로 급하지 않다).

## 사장님 확정 (2026-08-28) — 되묻지 말 것

```
등급        A+ 95↑ · A 90~95 · B+ 85~90 · B 80~85 · C+ 75~80 · C 70~75
            D+ 65~70 · D 60~65 · F 60↓   경계는 「이상~미만」
GEO 경계    SEO 와 동일 — "B 는 어디서나 B"
공개 창구   폐쇄형이다. 로그인 없는 진단 창구·안내판은 닫는다
실험실 성능  점수 밖으로 뺐다 되넣지 않는다. 그 사이 진단 결과를 거래처에 내지 않는다
속도 측정   구글에 세 번 묻는 길은 없다(캐시). 우리가 직접 잰다
```

## 주의·제약 (반드시)

- **말**: 사장님께 나가는 글은 「커밋」과 「배포」 **두 단어만**. 「민다·푸시」 금지.
- **판 번호**: 고르기 전에 `git fetch`. 대장 §2 머리말·배포 대기 표를 함께 고친다
  (`worklist.test.ts` 가 막는다). 대장은 **1200줄 한도**가 있다 — 넘으면 지난
  기록을 `WORKLIST-HISTORY.md` 로 옮긴다(한도를 올리지 않는다).
- **가지**: 두 저장소 모두 `claude/wonderful-einstein-1qiqm5`.
- **비밀키 값·모델 ID**를 커밋/PR/코드/문서/채팅에 넣지 않는다. 트레일러 준수.
- **실측 원칙**: 실측 > 추론 > 날조 금지. 못 잰 값은 `0` 이 아니라 `—`(ADR 0002).
  이번 세션에 내가 이걸 두 번 어겼다(오류 165 · 「여덟」→「열」). **숫자를 낼 때
  그 숫자를 이루는 항목이 어디서 오는지 코드에서 확인한다.**
- **관문을 무력화하지 않는다.** 기준선을 고칠 땐 왜 바뀌었는지 그 자리에 적는다.
- **계약을 다시 뽑는다**: 창구를 더하거나 빼면
  `python apps/api/scripts/export_openapi.py` → `pnpm --filter @veo/api-client generate`.

## 이 방(작업 컨테이너)의 한계 — 실측 2026-08-28

```
gh 없음 · 운영 API curl 403
바깥 네트워크   pagespeedonline.googleapis.com 만 열림(익명이라 429)
                example.com · chamsarang1075.com · venomad.com · google.com  CONNECT 403
docker 있음     다만 워커 이미지 빌드는 디스크 한도를 넘긴다
DB 없음         apps/api/tests 의 DB 시험은 여기서 안 돈다(코드 결함 아님)
개발 환경       python3.12 로 venv (프로젝트가 >=3.12 요구), pip install -e './apps/api[dev]'
                크롬은 /opt/pw-browsers/chromium-1194/chrome-linux/chrome
```

## 참고

- 세션 상세 `docs/session-logs/2026-08-28-s09.md`
- 배포 런북 `docs/ANSEO-배포-인계.md`
- 점수 방법론 `veo-platform/docs/scoring/methodology.md` · 항목 전수
  `docs/scoring/seo-checks-inventory.md`(SEO 59 · GEO 37)
- 내가 틀린 것 `veo-platform/docs/CORRECTIONS.md`(165번이 이번 세션)
