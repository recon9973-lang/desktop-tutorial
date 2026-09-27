# 2026-09-27 — 점수 추이 방 (가지 `claude/beautiful-heisenberg-szdc5b` · noindex 이슈 방을 닫은 뒤 같은 가지에서)

## 오더
«이 부분 그래프로 보기에 표현이 많이 안 되는 것 같아. 주식 차트처럼 일간 주간 월간 같이 볼 수 있도록 변경해줘» ·
«진단하고 GEO 파트야» (캡처: 거래처 진단 탭 · GEO · 「누적 진단」 그래프 · 9/11 이 다섯 번 선 가로축)

## 어느 사이트인가
ANSEO(veo.seokorea.org · `veo-platform`). 이 저장소 코드는 안 건드렸다(문서만).

## 찾은 것
- 그 그래프는 공용 `TrendChart`(packages/ui)를 거래처 진단 탭 `historyBand` 와 SEO 화면 `SummaryRail` 두 자리가 쓴다. 회차마다 점 하나 ·
  가로 간격 균등 · 거래처 판은 최근 12 회차(`HISTORY_LIMIT`)라 하루 다섯 회차가 그림의 반을 차지했다.
- 겹침 관문(`no-duplicate-charts.test.ts`)이 `{trendAbove ? null : <TrendChart` 를 글자로 본다 — 감싸개로 바꾸면 그 줄을 함께 고쳐야 한다.

## 한 것
- `veo-platform` 가지 `claude/score-chart-timeframes` · 판 0.3.663(잠정) · 인계 `docs/HANDOFF-2026-09-27-score-timeline-to-anseo.md`.
  묶는 규칙(마지막 회차 = 종가 · 최저~최고 = 심지 · 빈 기간 건너뜀 · 명세 끊김 유지 · 서울 날짜 · 월요일 주) · 단추 부품 · 차트 `range`/`title`.
- 이 저장소: 이 기록 · `RESUME-score-chart.md`(가지 표시 이어받음 · 닫힌 noindex 이슈 방 인계본의 표시는 뗐다).

## 조심한 것
- 평균으로 묶지 않았다 — 평균은 잰 값이 아니다(제1 원칙). 주식 차트의 종가·심지 규칙을 그대로 옮겼다.
- 실제 화면은 못 봤다(운영 egress 403 · 로그인 없음). DOM 시험으로만 잰 것이라 인계 문서에 적었다.
