# 서버에는 있는데 화면에서 못 부르는 것 — 전수 (#65)

**날짜** 2026-08-08 · **대상** `apps/api/openapi.json` 115개 엔드포인트 전부

만들어 놓고 화면에 버튼을 안 단 기능은, 사장님 입장에서는 **없는 기능**이다.
지난 세션에 우연히 3건이 나왔다. 우연에 맡기지 않으려고 전수로 세었다.

---

## 어떻게 셌나

```bash
python3 scripts/ui_gap.py          # 후보 목록
python3 scripts/ui_gap.py --all    # 115개 전부와 판정
```

`openapi.json` 의 경로와 `apps/web/src` 안에 실제로 적힌 경로 문자열을 맞춘다.
경로를 변수로 조립한 것(`` `${baseUrl}/api/reports/${id}/...` ``)도 잡도록
빈칸을 넓게 맞춘다 — **넓게 맞추므로 "없다" 는 쪽이 더 믿을 만하다.**

**[실측]** 스크립트 출력: 115개 중 후보 29개 (화면이 부를 이유가 없는 5개는 스크립트가
미리 제외 — `health`·`metrics`·`DELETE /projects`·`organizations` 2개).

**[실측]** 그 29개를 한 건씩 코드로 확인했다. 아래는 확인 뒤의 판정이다.

---

## A. 진짜 구멍 — 일이 막힌다 (12개 엔드포인트 · 5가지)

### A-1. 이슈를 "해결" 로 옮길 방법이 화면에 없다

```
POST /api/issues/{id}/verification-requests    표적 재검사 요청
POST /api/issues/{id}/verification-results     재측정 결과 반영
POST /api/issues/{id}/assignee                 담당자 지정
```

화면은 `POST /api/issues/{id}/transitions` 만 부른다(`lib/issues.ts`).
그런데 서버 규칙상 **해결 상태로 가는 문은 재측정 결과뿐이다.**

> "해결(VERIFIED_RESOLVED)은 표적 재측정에서 해당 검사가 통과했을 때만 기록됩니다."
> (`apps/api/src/veo/issues/lifecycle.py:304`)

이것은 일부러 그렇게 만든 규칙이다(ADR 0011 · `lifecycle.py:9`). 규칙이 옳다.
**빠진 것은 그 규칙을 밟을 화면이다.** 지금 이슈는 열리고 진행되지만 닫히지 않는다.
담당자 지정도 마찬가지로 서버에만 있다.

### A-2. AI 엔진 열쇠를 화면에서 넣을 수 없다

```
GET    /api/credentials                  연동 상태 (값은 안 돌려준다 — 지문·끝 4자만)
PUT    /api/credentials/{provider}/{field}   저장 (쓰기 전용)
POST   /api/credentials/{provider}/verify    검증
DELETE /api/credentials/{provider}/{field}   비활성화
GET    /api/providers                        어느 제공자가 붙어 있나
```

네 개 다 살아 있다 — `app.py:296` 에서 실제로 마운트한다.
(주의: `credentials/router.py` 첫 줄의 *"deliberately not mounted"* 는 **낡은 설명**이다.
코드가 바뀌고 주석이 안 바뀐 자리다. 고쳐야 한다.)

**이것이 #64(엔진 확대) 를 직접 막고 있다.** 지금 열쇠를 넣으려면 서버 환경변수를
고쳐 재배포해야 한다. 화면이 있으면 사장님이 직접 넣고 그 자리에서 검증할 수 있다.

### A-3. 리포트 본문을 화면에서 읽을 수 없다

```
GET /api/reports/{id}/versions/{n}    경영진·마케팅·개발자 3종 본문
```

화면에 있는 것: 버전 **목록**(`lib/reports.ts:69`), **내보내기**(`report-export/route.ts:50`),
**공유 링크**(`report-share/route.ts:38`). 없는 것: **본문을 화면에서 그대로 보기.**
지금은 파일로 내려받아야만 읽는다.

### A-4. 경쟁사 비교 결과를 볼 화면이 없다

```
GET  /api/competitors/comparisons
POST /api/competitors/comparisons
GET  /api/competitors/comparisons/{id}
```

`console/competitors/` 화면은 **브랜드 선언**(자사·비교 대상)까지만 한다.
같은 조건에서 잰 비교(ADR 0010)를 만들고 읽는 세 엔드포인트는 아무도 안 부른다.

### A-5. 무료 진단에 상담 요청 폼이 없다

```
POST /public/v1/leads    무료 진단 상담 요청 접수
```

무료 진단(SEO·GEO·키워드)은 화면이 있고 결과 공유 링크도 있다. 그런데 **"상담
받겠다" 를 누를 자리가 없다.** 접수 창구는 서버에 이미 서 있다.

---

## B. 만들다 만 것 — 급하지 않지만 반쪽이다 (15개 · 8가지)

| 무엇 | 엔드포인트 | 지금 상태 |
|---|---|---|
| 키워드 목록 저장·재사용 | `/api/keywords/lists` 5개 (조회·생성·상세·교체·삭제) | 매번 손으로 다시 넣는다 |
| 지난 키워드 조회 다시 열기 | `GET /api/keywords/lookups/{id}` | 최근 목록은 보이는데 열리지 않는다 |
| 키워드 결과 CSV·XLSX | `GET .../lookups/{id}/export` | 내보내기 버튼 없음 |
| 연관 키워드 | `GET .../lookups/{id}/related` | 서버만 안다 |
| 프로젝트 수정 | `GET`·`PATCH /api/projects/{id}` | **만들면 못 고친다** — v0.3.69 브랜드와 같은 모양 |
| 진단 원자료 보기 | `GET /api/seo/scans/{id}/captures` | 판정만 보이고 근거 응답은 못 본다 |
| 점수 재현 | `POST /api/scoring/evaluate` | "이 점수가 왜 나왔나" 를 화면에서 못 돌린다 |
| GEO 채점 명세 | `GET /api/geo/readiness/spec` | SEO 는 `/api/seo/checks` 로 화면에 있는데 GEO 만 없다 |
| 프롬프트 집합 하나 열람 | `GET /api/observations/prompt-sets/{id}` | 목록만 보인다 |

---

## C. 안 불러도 정상 (7개)

| 엔드포인트 | 왜 정상인가 |
|---|---|
| `GET /api/health` · `GET /api/metrics` | 감시·수집용. 화면이 쓸 일이 없다 |
| `DELETE /api/projects/{id}` | "지원하지 않는다" 고 스스로 답하는 자리 |
| `GET /api/organizations/current` · `/{id}` | `/api/auth/me` 가 `organization` 을 함께 준다 (`MePayload`) |
| `POST /api/geo/readiness/analyses` · `/scans` | SEO 진단이 돌 때 GEO 를 **동반으로** 남긴다 (`geo/companion.py:109`). 따로 부를 필요가 없다 |

`geo/readiness/scans` 는 "GEO 만 따로 다시 재기" 를 못 한다는 뜻이기도 하다.
지금은 SEO 를 같이 돌려야 한다. 급한 구멍은 아니라 여기 둔다.

---

## 이 조사가 다음에도 되게 하려면

`scripts/ui_gap.py` 를 남겼다. 새 엔드포인트를 만들고 화면을 안 붙이면 후보 수가
늘어난다. 아직 CI 관문에는 넣지 않았다 — 관문으로 만들지는 사장님 판단이다.
(넣는다면 "후보 수가 지금보다 늘면 실패" 형태가 맞다.)

---

## 딸린 수정거리 하나

`apps/api/src/veo/credentials/router.py:3` 의 *"This router is deliberately not
mounted."* 는 사실과 다르다 — `api/app.py:296` 이 마운트한다. 설명이 코드보다
낡았다. A-2 를 할 때 같이 고친다.
