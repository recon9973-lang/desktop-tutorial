# RESUME — URL 해시 방 마감 (2026-09-16 · s23)

> **이 방은 닫혔다.** 아래 「넘길 것」 한 건만 남았다. 나머지는 끝났다.
> 지난 회차 `docs/session-logs/2026-09-11-s22.md` · 현황 `PROJECT_STATE.md`.
> 작업 대상은 **`veo-platform`** 이다(`add_repo`, owner `recon9973-lang`).

## ⚠ 넘길 것 — 커밋 셋이 아직 안 나갔다

```
가지   deploy-candidate-claude-seo-paste-verification   (원격에 있음 · e687a46)
상태   [실측 2026-09-16] main 은 0.3.595 · 이 셋은 main 의 조상이 아니다 (0/3)

e687a46  실측 불가침 전수조사 — 고칠 것이 없었다 · 오류 대장 217 은 내 보고가 틀린 것
d17c6af  고객에게 나가는 리포트의 조치 칸이 비어 있었다 — 아무도 그 표를 읽지 않았다
666d57f  SEO 예시도 붙여넣어 돌려 봤다 — 다섯이 걸렸고 하나는 사이트를 망가뜨렸다
```

**대장의 대기 표 세 줄이 이 가지 안에만 있다** — main 의 `docs/WORKLIST.md` 에는 없다.
배포 담당인 **ANSEO 방은 main 만 보면 이 일감을 못 본다.** 그 방에 가지 이름을 알려 줘야 한다.

검증은 끝나 있다 — **시험 7,580건 실패 0 · 오류 0**(postgres 켜고 DB 시험까지 · 건너뜀 56)
· mypy 463파일 무결 · ruff 무결.

## 끝난 일

### 1차 — main 에 들어감 (0.3.564 안에 얹혀 나감 · `claim_version` 은 안 물림)

```
18fb021  변경이력에 GEO 진단 다섯 줄
9fa82c0  오류 대장 202 — 따옴표를 틀리게 찾아 「66판 뒤처짐」을 지어냈다
2ca3f37  SEO 성능 지표 셋이 사업 영향 한 문장을 돌려 썼다 — CLS 자리에 틀린 말
14ca137  조치 예시를 실제로 붙여넣어 돌려 봤다 — 넷이 걸렸다
```

### 2차 — 위 가지에 있음(미배포)

**사장님이 못박은 규칙 셋**이 이 방의 잣대였다.

> ① 진단값은 **실측 그대로**. 못 잰 것은 «—», 추정을 실측인 척하지 않는다.
> ② 조치는 **실제 초보자가 그대로 따라 할 수 있어야** 한다.
> ③ **추측하지 말고 시뮬레이션을 직접 돌려** 정확한 제안을 만든다.

②③ 을 **관문**으로 바꿨다. 「읽어서 그럴듯한 코드」와 「넣으면 판정이 바뀌는 코드」는 다르다.

* `tests/{geo,seo}/test_a_pasted_example_actually_passes.py` — 예시의 자리표시자를 채워
  페이지에 붙이고 **진짜 수집기를 돌려 PASS 가 아니면 실패**시킨다. 더해서 **성한 자리를
  망가뜨리지 않는지**도 본다. 한 장으로 못 재는 검사는 **이유를 30자 이상** 적어야 뺀다.
* `tests/seo/test_remediation_quality.py` · `tests/geo/test_check_matrix.py` — 조치 없음·
  45자 미만·영향/재확인 빔·**코드가 결과물인데 코드 없음**을 막는다.
* `tests/issues/test_the_issue_screen_shows_the_same_code.py` — 이슈 화면이 등록부 코드를
  찾는가(DB 없이 돈다).
* `tests/reports/test_report_from_scan.py` 에 **리포트에 조치가 실리는가** — 실제로 저장된
  진단에서 되살려 본다.

**그 관문들이 잡은 것**(전부 실측):

1. `geo.entity.stable_id_graph` 예시가 정의하지도 않은 이름표를 가리켰다 — 우리 예시가
   우리 검사에 걸렸다.
2. `geo.evidence.publisher_identified` 는 **예시가 옳고 수집기가 틀렸다.** 중첩 `publisher`
   를 못 봐서, 상호·전화·주소가 다 적힌 페이지를 「발행 주체 없음」으로 깎았다.
   **사장님이 짚으신 `@id` 오판과 같은 뿌리**(한 겹만 읽음).
3. `geo.entity.disambiguation_signals` 는 **조치 문장과 예시가 딴소리**였다 — 붙여넣어도
   판정이 안 움직였다.
4. `seo.robots.meta_indexable` 예시는 코드 줄이 **「지울 줄」 하나뿐**이라, 복사해 넣으면
   `noindex` 가 박혀 **사이트가 색인에서 빠졌다.**
5. `seo.onpage.meta_description_quality` 예시가 우리 검사에 걸렸다(폭 61 · 최소 80).
6. `seo.onpage.title_present_and_unique` 에 `<title>` 이 두 줄이라 한 페이지에 넣으면
   「title 은 하나」 검사가 깨졌다.
7. **고객 리포트의 조치 칸이 통째로 비어 있었다.** 진단을 저장하는 길이 조치 문구를
   아예 저장하지 않았고, 리포트는 「`fix_recommendations` 소관」이라 주석만 적어 둔 채
   그 표를 읽지 않았다. 이제 잴 때 남기고 리포트가 읽는다.

**실측 불가침(①)은 전수조사 결과 고칠 것이 없었다.** 묶음마다 이름이 다른 전용 장치가
이미 있다 — `MeasuredValue`(reports) · `ObservedRate`(observations) · 값마다 품질 칸
(keywords) · `available=False`(location). **앞서 「여덟 묶음에 관문이 없다」고 보고한 것은
시험 파일 이름만 보고 한 어림이었고 틀렸다 — 오류 대장 217 에 적었다.**

## 아직 못 푼 것 — 사장님 몫

**venomad 재진단.** [실측 2026-09-16] `www.venomad.com` 은 이 환경에서 egress 차단
(`CONNECT tunnel failed, 403`)이라 **못 돌린다.** 지어내지 않는다.

사장님이 콘솔에서 한 번 돌리시면 처음 물으신 **「#이 들어간 주소」** 건이 끝난다 —
「구조화 데이터의 @id가 엔터티 간에 연결되는가」가 통과로 바뀌는지 보면 된다.
**이번에 고친 중첩 `publisher` 건도 venomad 에 걸렸을 가능성이 크다.**

원본만 있으면 코드로 바로 확인할 수 있다(맥 터미널 한 줄):

```
curl -sL https://www.venomad.com/ | python3 -c "import sys,re;print(chr(10).join(re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>',sys.stdin.read(),re.S|re.I)))" > ~/Desktop/venomad-jsonld.txt; wc -c ~/Desktop/venomad-jsonld.txt
```

## 다음 방이 알아야 할 것

- **배포 담당은 ANSEO 방이다.** 만드는 방은 **검사까지만** 하고 가지 이름을 대기 표에 적는다.
- **이 방은 `make deploy` 가 막힌다**(자동 승인기). `git reset --hard` 도 막힌다 —
  `git checkout -b <새이름> origin/main` 으로 새 가지를 떠서 본다.
- **시험 결과를 종료값으로 읽지 않는다.** `-q` 로 파일에 흘리면 요약 줄이 안 남는다 —
  `--junitxml` 로 받아 숫자로 읽는다(오류 대장 195).
- **예시 코드에 지어낸 사실 금지** — 금액·기간·주소·전화·기관명은 `[ ]` 로 비운다.
  「오류 로그**부터**」 같은 말도 기관명 패턴(`…부`)에 걸린다.
- **`ruff format` 은 CI 가 안 돌린다**(`ruff check` 만). 형식만 고쳐 큰 diff 를 만들지 않는다.
- 대장(`docs/WORKLIST.md`)은 여러 방이 같이 쓴다. **다른 방 줄은 건드리지 않는다.**
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` + `Claude-Session:`.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—». 의료광고법 준수.
