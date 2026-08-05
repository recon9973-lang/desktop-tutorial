# VEOBot — 우리가 남의 서버에 밝히는 신원

`veo.common.security.fetcher` 의 주석이 이 문서를 가리키고 있었는데 문서가 없었다
(2026-08-06 확인). 코드가 가리키는 문서가 없으면 그 주석은 근거가 아니라 장식이다.

## 왜 신원이 문제인가

크롤러는 **남의 서버에 요청을 보낸다.** 그 서버 운영자는 우리를 알아보고 거절할 수
있어야 한다. 그러려면 셋이 맞물려야 한다.

1. User-Agent 가 우리를 밝힌다.
2. robots.txt 매칭에 쓰는 이름이 그 UA 의 토큰과 **같다.**
3. UA 가 가리키는 안내 페이지가 **실제로 있다.**

2026-08-06 실측에서 셋이 전부 어긋나 있었다.

| | 값 |
|---|---|
| 작업의뢰서 §5.2 요구 | `VEOBot/1.0` |
| 실제 UA | `VEO-Bot/1.0` (하이픈) |
| robots 매칭 이름 | `veo-bot` |
| 안내 페이지 | **HTTP 404** |

거래처가 `User-agent: VEOBot` 으로 우리를 막아도 매칭 이름이 달라 **걸리지 않았다.**
남의 서버가 우리를 거절할 방법을 우리가 없애 놓은 상태였다.

## 지금 값 — 단일 원본

| 무엇 | 값 | 원본 |
|---|---|---|
| User-Agent | `VEOBot/1.0 (+https://veo.seokorea.org/bot)` | `common/security/fetcher.py` `DEFAULT_USER_AGENT` |
| From | `bot@seokorea.org` | 같은 파일 `CRAWLER_FROM` |
| robots 매칭 | `veobot` | `seo/parsing/robots.py` `CRAWLER_AGENT_NAME` |
| 안내 페이지 | `/bot` | `apps/web/src/app/(public)/bot/page.tsx` |
| 요청 간격 | 1초 | `settings.crawl_min_interval_seconds` |
| 동시 연결 | 2 | `settings.console_crawl_concurrency` |
| 시간당 요청 | 450 | `settings.console_target_host_limit_per_hour` |
| 연결 / 전체 대기 | 10초 / 30초 | `common/security/limits.py` |
| 문서 크기 | 2MB | 같은 파일 `max_response_bytes` |

## 값을 바꿀 때 함께 바꿔야 하는 것

이 표의 값은 **네 곳에 흩어져 있다** — 엔진 상수, 설정, 안내 페이지, 이 문서.
갈라지면 안내 페이지가 거짓이 되고, 그때부터 운영자는 우리 말을 믿을 이유가 없다.

검사가 지키는 것:

* `apps/api/tests/common/test_bot_identity.py` — UA 토큰과 robots 매칭 이름이 같다.
  타사 봇 이름이 UA 에 들어가지 않는다.
* `apps/web/src/app/(public)/bot/page.test.tsx` — 안내 페이지가 실제 UA·연락처·요청
  정책을 그대로 싣는다.

검사가 없는 것(사람이 챙긴다): 설정값을 바꾸면 안내 페이지의 숫자와 이 표를 함께 고친다.

## 타사 봇 사칭 — 하지 않는다

실측(2026-08-05): 거래처 두 곳이 해외 IP 에 자바스크립트 쿠키 검사를 내보내는데,
**Googlebot User-Agent 로는 면제**됐다(759B → 51,262B). 그 면제는 사이트가 **구글에게**
준 것이다. 우리가 구글인 척하면 사이트 주인을 속이는 것이고, 무엇보다 "잰 것을 그대로
보고한다" 는 이 제품의 근거가 무너진다.

대신 한국 관측점을 거쳐 **우리 이름 그대로** 받는다(`common/security/retry_via_kr.py`).

## 아직 못 지키는 것

작업의뢰서 §5.2 는 **고정 IP + 역방향 DNS** 도 요구한다. 지금 인프라(Railway·Vercel)
에서는 나가는 IP 가 고정되지 않는다 — 2026-08-05 실측에서 API 는 `34.21.188.186`
(싱가포르, GCP), 한국 관측점은 `3.37.129.161`(AWS 서울)이었고 둘 다 우리 소유가 아니다.

서버를 옮길 때 함께 해결한다. 그때까지 운영자는 IP 가 아니라 **User-Agent 로** 우리를
식별해야 하며, 안내 페이지가 그 점을 분명히 한다.
