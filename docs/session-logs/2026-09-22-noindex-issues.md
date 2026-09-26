# 2026-09-22 — noindex 이슈 방 (가지 `claude/beautiful-heisenberg-szdc5b`)

## 오더
1. «ANSEO noindex 처리 관련해서 조치 사항 점검해줘»
2. «noindex 는 예전처럼 표시하고 별도로 체크하면 noindex 처리가 정상으로 되도록 … 일괄 빼버리면 noindex 처리를 하지 않아야 할
   콘텍츠가 noindex 된 상황 확인이 안 되잖아. 이슈 탭에 아직 noindex 가 있어. 나머지 항목도 점검에서 나온 것 처리도 해.»

## 어느 사이트인가
ANSEO(veo.seokorea.org · `veo-platform`). 이 저장소 코드는 안 건드렸다(문서만).

## 점검 (코드로 확인 · 운영 화면은 못 봄)
- 0.3.646(2026-09-22 14:22 KST 러너 실측 · 웹·서버·워커)에 noindex 인정 보강 4건이 실려 나가 있었다 — **결과 화면에만**.
- 이슈 탭에 noindex 가 남는 까닭 둘: ① 이슈 목록·상세에 지정 자리 없음 ② 지정 → 재진단해도 이슈는 안 닫힘 —
  닫는 길은 표적 진단 확인 하나(`issues/lifecycle.py`), 인정 주소는 `evaluated_urls` 에서 빠져 `derive_outcome` 이
  「재지 않았다 → 판정 불가」(`issues/verification.py:184`). GEO 는 주소별 해당 없음 → 판정 불가.
- 부수: noindex 인정 방의 연구보고서·인계본이 그 방 가지(`claude/fervent-fermat-ahf55p`)에만 있고 main 에 없었다.
- 옛 남은 것: GEO 1.9.0 관문(noindex 95.062 → 0.000)이 실제 거래처 화면에서 찍히는지 미확인(검수 방 s24~).

## 한 것
- `veo-platform` 가지 `claude/noindex-accept-in-issues` · 판 0.3.647(잠정) · 인계 `docs/HANDOFF-2026-09-22-noindex-issues-to-anseo.md`.
  내용·관문은 그 문서와 `RESUME-noindex-issues.md`.
- 이 저장소: 인정 방 커밋 둘(a798d0e · a6e6740)을 cherry-pick 해 main 에 실음 · 이 기록 · 이 방 인계본.

## 틀린 것 / 조심한 것
- 첫 답에서 「기능이 배포돼 있다 · 지정 안 해서 그렇게 보인다」까지만 말했다. 사장님이 다시 짚어 주셔서 이슈 탭의 구조적 구멍(②)을
  찾았다 — 「배포됐다」와 「사장님 화면에서 동작한다」는 다른 문장이다. 처음부터 이슈 탭의 닫힘 경로까지 읽었어야 했다.
- 이 컨테이너는 운영 주소에 못 닿는다(403). 화면 값은 전부 «—». 관문은 코드·시험으로만 잰 것이다.
