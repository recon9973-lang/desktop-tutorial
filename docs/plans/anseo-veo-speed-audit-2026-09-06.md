# ANSEO(veo-platform) 속도 병목 전수조사 — Top 10 원문 보존 (2026-09-06 · s19 Explore 에이전트 결과)

> s19 에서 scratchpad 에만 있던 것을 s20 이 저장소로 옮김. 착수 현황은 `RESUME.md` · veo-platform `docs/WORKLIST.md` 대기 표가 최신.


전문은 세션 대화(s19)에 인라인. 여기엔 Top 10 + 착수 순서만.

## 총론
- 프런트 워터폴은 8월에 이미 거의 잡힘(startEarly, React cache, Promise.all, load_only). 런타임 의존성 4개, public/ 없음, 서드파티 스크립트 0.
- 남은 것은 구조: ① API 응답 무압축 ② 서울(Vercel)↔싱가포르(Railway) 왕복 0.28초는 못 줄임 → 횟수/바이트만 ③ 진단이 API 프로세스 안 배경 스레드

## Top 10
| # | 자리 | 현상 | 절감 | 우선 | 처방 |
|---|---|---|---|---|---|
| 1 | apps/api/src/veo/api/app.py:183 | GZipMiddleware 없음, 진단 탭 응답 1,012KB 날것 | ~120KB로 (85~90%) | H | add_middleware(GZipMiddleware, minimum_size=1024) |
| 2 | apps/web/src/app/(console)/layout.tsx:42,53 | requireConsoleSession → getOrganizationIndustry 순차(불필요) | 모든 콘솔 화면 0.28s | H | Promise.all |
| 3 | apps/api/src/veo/jobs/execution.py:226 | 브로커 없어 진단이 API 프로세스 데몬 스레드, uvicorn 단일 프로세스 | 크롤 중 콘솔 지연 제거 | H | Railway Redis + infra/railway/worker.json 기동, run_detached→Celery (사장님 비용 판단) |
| 4 | providers 11곳(observations/providers/base.py:1039 등) | 요청마다 httpx.Client 새로 생성, keep-alive 없음 | 관측 1판 60콜 6~18s | H | 인스턴스 수명 클라이언트 + 공용 팩토리 |
| 5 | apps/api/src/veo/core/settings.py:342-343 | DB 풀 10 vs 동기 라우트 195개가 스레드풀 40에서 | 11번째 동시요청부터 10s 대기 후 실패 | H | 스레드풀 상한을 풀에 맞춤(Neon 112 커넥션 3서비스 공유 제약) |
| 6 | apps/web/src/lib/console-api.ts:223-236 readAllPages | 쪽 넘김 순차 while(최대 25쪽) | 쪽수×0.28s | M | 1쪽 total_items로 2쪽부터 병렬 |
| 7 | apps/web/src/app/layout.tsx:97-102 | Google Fonts 렌더 차단(3패밀리 10웨이트) | 교차출처 왕복 2겹 | M | next/font/google self-host |
| 8 | seo/cooldown.py:79, seo/pages.py:185, seo/regression.py:136·163, competitors/from_scan.py:254 | ScanRun 전 칸 로드(report_snapshot 101kB/행) | regression 저장마다 234kB | H | history.py:782식 load_only |
| 9 | apps/web/src/lib/companies.ts:327-341 | listCompanies = 왕복 3~4회, 서버 렌더에서 조인, 18곳 호출 | 3~4 → 1 | M | GET /api/customers/overview 서버 조인 |
| 10 | router.refresh() 32곳 + force-dynamic 23곳 | 토글 하나에 페이지 전체 재렌더(거래처 상세 3,139줄·API 15+콜) | 토글당 0.8~3s | M | useOptimistic + revalidateTag |

## 그 외
- AI 엔진 타임아웃 180s(observations/providers/base.py:110) × 동시성 4 = 3분 정지 위험
- 관측 러너 head-of-line: runner.py:581-604 fill()이 작은 집합에서 회차당 120s 통대기 (L)
- 부팅 bootstrap_*_from_disk 5회(1.5MB gz 등) → 빈 DB 첫 배포 시 healthcheckTimeout 60s 초과 위험 (M)
- GEO 클라이언트 번들 213KB 소스: PromptSetForm.tsx 73KB → next/dynamic
- Suspense 경계: customers/[customerId]만 12곳, geo/seo/dashboard 0곳
- 캐시 사실상 없음(응답·ETag·Redis는 rate limit 전용). 후보: 조직 업종·엔진 누적·SerpAPI 잔여
- 중복: seo-regular/aeo-regular route ~90% 동일, httpx.Client 11곳, 스케줄러 루프 4곳 동일 골격
- 진단 지배항 = 크롤 페이싱 호스트당 초당 2장(의도된 값, 줄이면 안 됨: 154장 ≥77s)

## 착수 순서
1일차: #1 GZip · #2 layout Promise.all · #8 load_only 5곳 / 2주차: #4 httpx 수명 · #7 next/font · PromptSetForm dynamic / 사장님 결정: #3 Redis+워커 · #5 DB 풀

## 못 잰 것
route별 First Load JS(빌드 필요), 현재 운영 응답시간(8-20 개선 전 값만: 진단 2,974/AEO 4,756ms), Railway 인스턴스 스펙, 워커·Redis 실제 기동 여부, 슬로우 쿼리
