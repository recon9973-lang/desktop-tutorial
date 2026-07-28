# VEO 개발자 체크리스트

## 기능 착수 전

- [ ] 관련 공식 문서와 로컬 스냅샷의 날짜를 확인했다.
- [ ] 데이터 정의, 단위, 분모, 갱신 주기를 계약에 적었다.
- [ ] `pass/warning/fail/not_applicable/unknown` 판정 기준을 정했다.
- [ ] 원자료와 계산 결과를 연결할 evidence ID를 정했다.
- [ ] 정상·오류·결측·부분 성공 fixture를 먼저 만들었다.
- [ ] 외부 API quota, 비용, 자격증명, 약관을 확인했다.

## 구현 중

- [ ] 점수 가중치가 checker 코드가 아닌 versioned spec에 있다.
- [ ] N/A는 분모에서 제외되고 unknown은 confidence를 낮춘다.
- [ ] provider의 원문 값과 VEO 표준 값을 함께 보존한다.
- [ ] raw HTML·answer·citation·API 응답에는 hash와 수집 시각이 있다.
- [ ] 로그와 오류 응답에서 credential·cookie·개인정보를 제거했다.
- [ ] timeout, retry, idempotency, cancellation, partial success를 처리했다.
- [ ] Public과 Console의 권한·quota·데이터 범위가 분리됐다.

## SEO

- [ ] 원본 HTML과 렌더링 DOM을 구분했다.
- [ ] crawl 가능, index 허용, 실제 index 확인을 구분했다.
- [ ] canonical 선언과 다른 신호의 일관성을 검사한다.
- [ ] structured data를 문법·타입·검색 기능·내용 정합성으로 나눴다.
- [ ] Lighthouse lab과 CrUX field data를 섞지 않았다.
- [ ] Google 규칙과 Naver 규칙의 차이를 표시한다.

## GEO

- [ ] Readiness와 Observation이 별도 API·점수·화면이다.
- [ ] JSON-LD 존재 여부가 아니라 entity graph 정합성을 검사한다.
- [ ] prompt set, engine, locale, time, repetition을 저장한다.
- [ ] mention과 citation, citation과 claim support를 구분한다.
- [ ] 경쟁사는 동일 prompt와 조건으로 관측한다.
- [ ] 변동성·표본 부족을 confidence 또는 interval로 보여준다.

## Naver Keyword

- [ ] SearchAd, DataLab, Search API의 의미가 섞이지 않았다.
- [ ] PC/Mobile과 수집 시각·출처가 표시된다.
- [ ] 0, 결측, 억제값, 범위값이 구분된다.
- [ ] 401/403/429/5xx/timeout/schema change를 테스트했다.
- [ ] 기회점수의 구성요소와 버전을 내려받을 수 있다.
- [ ] 근거 없는 ‘실시간 인기검색어’ 표현이 없다.

## 완료 전

- [ ] 단위·계약·통합·보안·접근성 테스트가 통과했다.
- [ ] 화면 숫자를 API 응답과 calculation trace에 대조했다.
- [ ] export 값이 화면·API 값과 일치한다.
- [ ] 다른 조직의 ID로 접근할 수 없다.
- [ ] SSRF 우회 fixture가 모두 차단된다.
- [ ] `TODO`, `FIXME`, placeholder, 하드코딩 점수, 가짜 provider 결과가 없다.
- [ ] 변경 파일, 테스트 명령·결과, 남은 제한을 완료 보고에 적었다.
