# VENOM GrowthOps — 운영 가이드

화이트햇 검색 성장 시스템. PBN/링크스팸이 아니라 **콘텐츠 구조·내부링크·성과 측정·적법 아웃리치**로 검색 권위를 복리로 쌓는다. 기획 전문은 [`PLAN-growthops.md`](./PLAN-growthops.md).

## 구성요소

| 구분 | 파일 | 역할 |
|---|---|---|
| M1 엔진 | `lib/topic-cluster.js` | 필러-클러스터 설계, 글↔하위주제 매칭, 다음 빈칸 탐지 |
| M2 엔진 | `lib/internal-linker.js` | 글 간 관련도·내부링크 제안, 고아 글 탐지, 관련글 블록 주입(idempotent) |
| M2 CLI | `scripts/internal-links-report.js` | 읽기전용 리포트 (`node scripts/internal-links-report.js`) |
| M4 로직 | `lib/outreach.js` | 아웃리치 CRM 순수 로직(검증·상태전이·리마인더·집계) |
| 통합 API | `api/growthops.js` | 단일 서버리스 함수(`?module=linkhealth|cluster|outreach|snapshot`) |
| cron 연동 | `api/cron-daily-posts.js` | 클러스터 빈칸 우선 발행(`mode:'cluster'`) + 관련글 자동주입(`autoInternalLinks`) |
| 저장 헬퍼 | `lib/github-store.js` | `getJsonFile`/`saveJsonFile` 등 범용 JSON 영속화 |
| 콘솔 | `venom-wordpress/preview/growthops.html` | `/growthops.html` 대시보드(모니터·클러스터·아웃리치) |

## API 빠른 참조

```
GET  /api/growthops?module=linkhealth                  # 내부링크 헬스(고아글·평균링크)
GET  /api/growthops?module=cluster&action=list         # 클러스터+완성도(발행글 매칭)
POST /api/growthops?module=cluster&action=build        # body {category,region,pillar,size} (Bearer)
POST /api/growthops?module=cluster&action=sync         # 발행글↔하위주제 재매칭        (Bearer)
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

## 테스트 (총 34, 전부 통과)
```bash
node scripts/internal-linker.test.js      # 8
node scripts/outreach.test.js             # 9
node scripts/topic-cluster.test.js        # 8
node scripts/growthops-handler.test.js    # 9
```

## 자동발행 클러스터 모드(M1)
`posting-settings`에서 `mode:'cluster'`(또는 `clusterMode:true`)이면 cron이 무작위 키워드 대신
`clusters.json`의 **빈칸을 우선** 발행하고 채운다. `autoInternalLinks:true`이면 발행 직전
관련글 내부링크 블록(M2)을 운영자 승인형으로 본문에 주입한다.

## 자동 스냅샷(선택)
`vercel.json`의 cron에 다음을 추가하면 매일 추세가 누적된다(헤더로 `CRON_SECRET`/`ADMIN_SECRET` 전달 필요):
```json
{ "path": "/api/growthops?module=snapshot", "schedule": "10 0 * * *" }
```

## Vercel 함수 한도
Hobby 12개 한도. 현재 `api/`는 `growthops.js` 포함 **12/12**. 추가 함수가 필요하면
`contact.js`를 `store.js`로 흡수하거나 `usage-stats`를 `analytics`로 통합해 슬롯을 확보한다.

## 진행 현황
- ✅ M1 토픽 클러스터(`lib/topic-cluster.js`) + cron 클러스터 모드
- ✅ M2 관련글 블록을 cron 발행 시 운영자 옵션(`autoInternalLinks`)으로 자동 주입
- ✅ 관리자(`admin.html`) 사이드바 → `/growthops.html` 내비 링크
- ✅ 콘솔 3탭(SEO 모니터·토픽 클러스터·아웃리치)

## Core Web Vitals (M3)
`PSI_KEY`(Google PageSpeed Insights)와 `GROWTHOPS_MONITOR_URLS`(쉼표구분 URL, 없으면 `SITE_URL`)를
설정하면:
- `GET /api/growthops?module=cwv[&url=...&strategy=mobile|desktop]` 로 즉시 측정
- 일별 스냅샷(`module=snapshot`)에 핵심 URL 최대 3개의 성능·SEO·LCP·CLS가 함께 저장
- 콘솔 SEO 모니터 탭의 "지금 측정(PSI)" 버튼으로 확인
키 미설정 시에도 throw 없이 안전하게 빈 결과를 반환한다.

## 자동발행 옵션 (posting-settings)
관리자 → AI 자동 포스팅 → GrowthOps 옵션에서 토글:
| 설정 키 | 의미 |
|---|---|
| `mode: 'cluster'` | 클러스터 빈칸 우선 발행 |
| `autoInternalLinks: true` | 발행 직전 관련글 블록 자동주입 |
| `clusterAutoExpand: true` | 빈칸 소진 시 다음 필러로 새 클러스터 자동 설계 |
| `clusterPillars: []` | 자동확장 필러 목록(없으면 `keywords` 사용) |

## 다음 단계(후속)
- 콘솔 추세 차트에 CWV(성능 점수) 라인 추가
- 아웃리치 제안 메일 초안 생성(기존 OpenAI 래퍼 재사용)
- Search Console API 연동(실측 인덱싱·노출·클릭)
