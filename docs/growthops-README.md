# VENOM GrowthOps — 운영 가이드

화이트햇 검색 성장 시스템. PBN/링크스팸이 아니라 **콘텐츠 구조·내부링크·성과 측정·적법 아웃리치**로 검색 권위를 복리로 쌓는다. 기획 전문은 [`PLAN-growthops.md`](./PLAN-growthops.md).

## 구성요소

| 구분 | 파일 | 역할 |
|---|---|---|
| M2 엔진 | `lib/internal-linker.js` | 글 간 관련도·내부링크 제안, 고아 글 탐지, 관련글 블록 주입(idempotent) |
| M2 CLI | `scripts/internal-links-report.js` | 읽기전용 리포트 (`node scripts/internal-links-report.js`) |
| M4 로직 | `lib/outreach.js` | 아웃리치 CRM 순수 로직(검증·상태전이·리마인더·집계) |
| M3·M4 API | `api/growthops.js` | 단일 서버리스 함수(`?module=linkhealth|outreach|snapshot`) |
| 저장 헬퍼 | `lib/github-store.js` | `getJsonFile`/`saveJsonFile` 등 범용 JSON 영속화 |
| 콘솔 | `venom-wordpress/preview/growthops.html` | `/growthops.html` 대시보드 |

## API 빠른 참조

```
GET  /api/growthops?module=linkhealth                  # 내부링크 헬스(고아글·평균링크)
GET  /api/growthops?module=outreach&action=list        # 연락처+요약
GET  /api/growthops?module=outreach&action=remind      # 오늘 할 일
POST /api/growthops?module=outreach&action=upsert      # body {contact}    (Bearer ADMIN_SECRET)
POST /api/growthops?module=outreach&action=transition  # body {id,to,note} (Bearer ADMIN_SECRET)
POST /api/growthops?module=outreach&action=delete      # body {id}         (Bearer ADMIN_SECRET)
POST /api/growthops?module=snapshot                    # 일별 스냅샷 저장   (Bearer ADMIN_SECRET)
```
쓰기는 `Authorization: Bearer <ADMIN_SECRET>` 필요(기존 API와 동일 컨벤션). 미설정 환경은 통과.

## 데이터 파일 (GitHub 저장)
- `venom-wordpress/preview/content/outreach.json` — 아웃리치 연락처
- `venom-wordpress/preview/content/seo-snapshots.json` — 일별 SEO 스냅샷(추세)
- `venom-wordpress/preview/content/clusters.json` — (선택) 토픽 클러스터, M1에서 생성

## 테스트
```bash
node scripts/internal-linker.test.js      # 8
node scripts/outreach.test.js             # 9
node scripts/growthops-handler.test.js    # 6
```

## 자동 스냅샷(선택)
`vercel.json`의 cron에 다음을 추가하면 매일 추세가 누적된다(헤더로 `CRON_SECRET`/`ADMIN_SECRET` 전달 필요):
```json
{ "path": "/api/growthops?module=snapshot", "schedule": "10 0 * * *" }
```

## Vercel 함수 한도
Hobby 12개 한도. 현재 `api/`는 `growthops.js` 포함 **12/12**. 추가 함수가 필요하면
`contact.js`를 `store.js`로 흡수하거나 `usage-stats`를 `analytics`로 통합해 슬롯을 확보한다.

## 다음 단계(미구현/후속)
- M1 토픽 클러스터(`lib/topic-cluster.js`) + cron 클러스터 모드
- M2 관련글 블록을 발행 플로우(`publish-post`/`cron`)에서 운영자 승인 시 자동 주입
- M3 Core Web Vitals 추세를 `seo-proxy`의 PSI와 연결
- 관리자(`admin.html`)에서 `/growthops.html`로 가는 내비 링크
