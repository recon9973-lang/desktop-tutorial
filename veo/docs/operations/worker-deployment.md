# 워커 배포 — 재배포에도 진단이 살아남게

기획서 E5.

## 지금 무엇이 문제인가

진단은 **API 프로세스 안의 배경 스레드**에서 돈다. 데몬 스레드라서, API 를 재배포하면
그때 돌던 진단은 그대로 죽는다. 그 잡은 `RUNNING` 인 채 남고, 20분이 지나야
`is_stale` 이 참이 되어 화면이 "끝났는지 저희도 알지 못합니다" 라고 말한다.

거래처 사이트 200장을 크롤하던 중이었다면 그 시간이 통째로 날아간다. 그리고 우리는
남의 서버를 200번 두드려 놓고 아무것도 얻지 못한 것이다.

워커를 띄우면 진단이 워커에서 돈다. 브로커에 남은 메시지는 워커가 다시 떠서 집어간다
(`task_acks_late` + `task_reject_on_worker_lost`). API 재배포는 진단에 영향을 주지
않는다.

## 켜기 전에 알아 둘 것 — **순서가 중요하다**

> **워커보다 먼저 브로커 주소를 켜면 안 된다.**
>
> `VEO_CELERY_BROKER_URL`(또는 `VEO_REDIS_URL`)이 채워지는 순간 API 는 진단을 큐로
> 보낸다. 그런데 듣는 워커가 없으면 그 잡은 아무도 집어가지 않은 채 `QUEUED` 로
> 남는다. **지금보다 나쁘다** — 지금은 최소한 돌기는 한다.

그래서 아래 순서를 지킨다.

## 절차 (Railway)

### 1. Redis 를 만든다

Railway 프로젝트에서 `New` → `Database` → `Redis`.

만들면 `REDIS_URL` 변수가 그 서비스에 생긴다. 이 값을 아직 **API 에 넣지 않는다.**

### 2. 워커 서비스를 만든다

`New` → `GitHub Repo` → 이 저장소(API 와 같은 저장소).

서비스 설정에서:

| 항목 | 값 |
|---|---|
| Config-as-code file path | `infra/railway/worker.json` |
| Health check | 없음 (워커는 HTTP 를 듣지 않는다) |

### 3. 워커에 환경변수를 넣는다

API 서비스와 **같은 값**이어야 하는 것들이다. 다르면 워커가 다른 DB 를 보거나 다른
채점 명세로 채점한다.

| 변수 | 값 |
|---|---|
| `VEO_DATABASE_URL` | API 와 동일 |
| `VEO_CELERY_BROKER_URL` | 1번에서 만든 Redis 의 `REDIS_URL` |
| `VEO_REDIS_URL` | 같은 값 (레이트리미터도 이걸 쓴다) |
| `VEO_SCORING_SPECS_DIR` | `/app/packages/scoring-specs` (이미지 기본값) |
| 그 밖의 자격증명·설정 | API 서비스와 동일하게 복사 |

### 4. 워커가 실제로 듣고 있는지 확인한다

로그에 이 줄이 **없어야** 한다:

```
VEO_BROKER_URL is not set. Running Celery in EAGER mode
```

이 줄이 보이면 워커는 떠 있지만 **아무 큐도 듣지 않는다.** 3번의 브로커 주소를 다시
확인한다.

정상이면 로그에 `celery@veo-worker ready.` 와 듣는 큐 목록
(`crawl`, `seo`, `geo`, `keyword`, `report`, `dead_letter`)이 나온다.

### 5. 그다음에 API 에 브로커 주소를 넣는다

API 서비스에 `VEO_CELERY_BROKER_URL` 을 같은 값으로 넣는다. 여기서부터 진단이 큐로 간다.

### 6. 확인

콘솔에서 진단을 한 번 돌린다. API 로그에 이 줄이 나와야 한다:

```
job <id> queued on seo
```

`could not enqueue job ...; running in-process instead` 가 나오면 API 가 브로커에 못
붙은 것이다 — 이때도 진단은 **예전 방식으로 돈다.** 조용히 실패하지는 않지만, 워커를
띄운 보람은 없으므로 주소를 다시 확인한다.

## 되돌리기

API 서비스에서 `VEO_CELERY_BROKER_URL` 과 `VEO_REDIS_URL` 을 비우면 즉시 예전 방식
(배경 스레드)으로 돌아간다. 코드 배포가 필요 없다.

되돌린 뒤 큐에 남아 있는 메시지는 워커가 살아 있는 한 계속 처리된다. 워커까지 내리면
그 메시지들은 브로커에 남고, 그 잡들은 20분 뒤 "알 수 없음" 으로 표시된다.

## 아직 워커에서 돌지 않는 것

큐로 보내는 것은 **SEO 진단 하나뿐**이다(`veo.jobs.dispatch.QUEUEABLE`). GEO 관측·
키워드 조회·리포트 내보내기는 태스크 이름과 큐가 표에 있지만, 워커 쪽 본문이 아직
Phase 0 의 뼈대라 `NotImplementedError` 를 던진다. 이름이 있다는 것과 받는 사람이
있다는 것은 다른 이야기다(0-E).
