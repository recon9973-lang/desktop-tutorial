# RESUME — 다음 세션 이어가기 (2026-09-16 · s23 · 진단 조치문 전수조사)

> 새 세션은 이 파일을 **먼저** 읽는다. 지난 회차는 `docs/session-logs/2026-09-11-s22.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.
> **작업 대상은 `veo-platform`** 이다(`add_repo` 로 붙인다, owner `recon9973-lang`).

## 끝난 일 — 전부 main 에 들어갔다 [실측 2026-09-16]

s22 의 「바로 이어갈 작업」 셋 중 ①은 끝났다. **네 커밋 모두 main 에 있다**
(`git merge-base --is-ancestor` 로 확인). main 은 그 뒤 다른 방들이 올려 **0.3.593**.
내가 세운 관문 파일 둘도 main 에 살아 있고, 지금 main 에서 **34건 전부 초록**이다.

```
18fb021  변경이력에 GEO 진단 다섯 줄
9fa82c0  오류 대장 202 — 따옴표를 틀리게 찾아 「66판 뒤처짐」을 지어냈다
2ca3f37  SEO 성능 지표 셋이 사업 영향 한 문장을 돌려 썼다 — CLS 자리에 틀린 말
14ca137  조치 예시를 실제로 붙여넣어 돌려 봤다 — 넷이 걸렸다
```

### 사장님이 못박은 두 규칙(2026-09-11) — 이 방의 잣대다

> ① 진단값은 **실측 그대로**. 못 잰 것은 «—», 추정을 실측인 척하지 않는다.
> ② 조치는 **실제 초보자가 그대로 따라 할 수 있어야** 한다.
> ③ (같은 날 추가) *"추측하지말고 시뮬레이션 직접 돌려서 정확한 제안을 만들어야 해."*

②③ 을 관문으로 바꿨다.

* `tests/seo/test_remediation_quality.py` — 깎였는데 조치 없음·45자 미만·영향/재확인 빔·
  지표끼리 같은 문장 돌려쓰기·**코드가 결과물인데 코드 없음**을 막는다(SEO 32항목 검사).
* `tests/geo/test_check_matrix.py` 에 같은 「코드 결과물」 관문 추가(GEO 16항목).
* `tests/geo/test_a_pasted_example_actually_passes.py` — **예시를 붙여넣어 진짜 수집기를
  돌리고 PASS 가 아니면 실패**시킨다. 자리표시자는 시험이 채운다(예시에 지어낸 사실을
  박지 않기 위해서다). 한 장으로 못 재는 검사는 **이유를 30자 이상** 적어야 뺄 수 있다.

### 그 시뮬레이션이 첫 실행에서 잡은 것 넷

1. `geo.entity.stable_id_graph` 예시가 `https://도메인/#website` 를 가리키며 그 이름표를
   **정의하지 않았다** — 우리 예시가 우리 검사에 걸렸다. WebSite 덩어리를 넣었다.
2. `geo.evidence.publisher_identified` 는 **예시가 옳고 수집기가 틀렸다.**
   `build_entity_graph` 가 최상위만 노드로 만들어 **중첩 `publisher` 를 못 봤다** —
   상호·전화·주소가 다 적힌 페이지가 「발행 주체도 연락 경로도 확인되지 않습니다」로
   나갔다. **사장님이 짚으신 `@id` 오판과 같은 뿌리**(한 겹만 읽음).
   `EntityNode.nested_organization()` 을 두고 `primary_organization()` 이
   `publisher·provider·sourceOrganization` 을 훑는다. **말뭉치 판정은 하나도 안 바뀌었다.**
3. `geo.entity.disambiguation_signals` 는 **조치 문장과 예시가 딴소리**였다. 판정은
   `visible_text` 의 지역·개원 연도·등록번호·전화와 `sameAs` 를 읽는데 예시는
   `areaServed`·`foundingDate` 만 보여 줬다 — 붙여넣어도 판정이 안 움직인다.
4. `geo.sd.matches_visible_content` 예시의 화면 쪽에 `addressLocality` 가 없었다.

## 바로 이어갈 작업 — 순서대로

1. **SEO 예시도 「붙여넣으면 통과하는가」를 잰다** ← 제일 크다.
   시뮬레이션 관문을 **GEO 에만** 세웠다. SEO 는 예시가 *있는지*만 보고 *먹히는지*는 안 본다.
   [실측 2026-09-16] 코드 예시가 있는 SEO 검사 33 · 그중 **붙여넣어 재볼 수 있는 마크업 27** ·
   서버 설정 6(한 장으론 못 잼). **GEO 는 13개 재서 넷이 걸렸다** — 같은 비율이면 SEO 에도
   여섯 안팎이 「넣어도 안 바뀌는」 예시일 수 있다. 사장님이 그대로 적용하실 자료다.
2. **실측 불가침 전수조사.** 이름으로 찾은 관문은 `seo·geo·scoring·budget·release` 에만 있다.
   숫자를 화면에 내면서 그 관문이 안 보이는 묶음: **observations(AI 답변 관측) · keywords ·
   competitors · location(상권) · medical/hira · content · issues · reports**.
   다른 이름으로 있을 수 있으니 **확인이 곧 이 작업**이다.
3. **판 번호 정리** — 따로 돌 일이 아니다. 다음 판을 물릴 때 함께 센다.

## 막힌 것

- **venomad 재진단을 이 방에서 못 돌린다.** [실측 2026-09-16] `www.venomad.com` 은
  여전히 egress 차단(`CONNECT tunnel failed, 403`). Railway·GitHub Actions 로그도 같다.
  **사장님이 콘솔에서 돌리셔야 한다.** 지어내지 않는다 — 못 돌렸으면 못 돌렸다고 적는다.
- 그 대신 요청해 둔 것: 맥 바탕화면의 **`venomad-jsonld.txt`(3,412바이트)**. 이 파일만 오면
  고친 코드를 그 원본에 직접 돌려 `@id` 건을 끝낼 수 있다. 5일째 안 왔다.
  받는 명령은 이 한 줄이다(줄바꿈 없이):
  ```
  curl -sL https://www.venomad.com/ | python3 -c "import sys,re;print(chr(10).join(re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>',sys.stdin.read(),re.S|re.I)))" > ~/Desktop/venomad-jsonld.txt; wc -c ~/Desktop/venomad-jsonld.txt
  ```
- **이 방은 `make deploy` 가 막힌다**(자동 승인기). 우회는 ① 후보 가지에 올려 CI 채점 →
  ② 초록이면 사장님이 한 줄로 main 에 올린다. `claim_version` 이 빠지는 경로다(오류 대장 201).
- **`git reset --hard` 가 막힌다**(자동 승인기 · 되돌릴 수 없는 삭제). 대신
  `git checkout -b <새이름> origin/main` 으로 새 가지를 떠서 본다.

## 주의·제약

- **CI·시험 결과를 종료값으로 읽지 않는다.** `-q` 로 파일에 흘리면 요약 줄이 안 남는다 —
  `--junitxml` 로 받아 `tests/failures/errors` 를 숫자로 읽는다(오류 대장 195의 재발 방지).
- 예시 코드에 **지어낸 사실 금지** — 금액·기간·주소·전화·기관명은 `[ ]` 로 비운다.
  관문이 잡는다(`tests/geo/test_fix_examples.py`). 「오류 로그**부터**」 같은 말도
  기관명 패턴(`…부`)에 걸리니 문구를 바꾼다.
- **`ruff format` 은 CI 가 안 돌린다**(`ruff check` 만). 이미 형식이 어긋난 파일을
  형식만 고쳐 큰 diff 를 만들지 않는다.
- 대장(`docs/WORKLIST.md`)은 **여러 방이 같이 쓴다.** 다른 방 줄은 건드리지 않는다.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: …`. **모델 ID 는 트레일러에만.**
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—», 의료광고법 준수.
- **사장님 작업 방식** — 짧게, 실행할 것 하나만. 터미널에 붙여넣을 것은 **한 줄**로 준다.
