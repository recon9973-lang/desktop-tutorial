# ADR 0006 — 모듈형 모놀리스로 시작한다

- 상태: 채택
- 일자: 2026-07-28

## 배경

VEO는 수집, 채점, 외부 API 연동, AI 관측, 보고서 등 성격이 다른 작업을 다룬다.
처음부터 마이크로서비스로 나누면 계약 관리 비용이 제품 가치보다 커진다.

## 결정

- 백엔드는 하나의 배포 단위(`apps/api`)로 시작하되, 도메인 모듈 경계를 코드에서 지킨다:
  `auth`, `organizations`, `customers`, `projects`, `sites`, `crawl`, `seo`, `geo`,
  `keywords`, `competitors`, `scoring`, `observations`, `issues`, `reports`, `usage`,
  `audit`, `common`.
- 한 모듈이 다른 모듈의 테이블을 직접 수정하지 않는다. 서비스 인터페이스를 거친다.
- 순환 의존성을 허용하지 않는다.
- 장시간 작업은 `apps/worker`의 Celery 큐로 분리한다. API 프로세스는 요청만 처리한다.
- 공통 계약(`veo/contracts`), 점수 명세, DB migration, 의존성 잠금 파일은
  통합 담당자만 수정한다.

## 결과

- 나중에 특정 모듈을 분리해야 할 때 경계가 이미 존재한다.
- 대가: 경계를 코드 리뷰로 지켜야 한다. 컴파일러가 강제해주지 않는다.
