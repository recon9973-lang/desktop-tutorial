# RESUME — 다음 세션 이어가기 (2026-09-06 KST · s19 마감 · 울릉 국지도 90호선 도동항 토지보상 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-06-s19.md`.
> 직전 다른 방: s18 속도·로딩(`-s18.md`) · s17 오류방 · s16/s15 입지 방. 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)
- 브랜치 **`claude/ulleung-bypass-road-analysis-bh7zu4`**, origin 푸시됨. **PR·병합 안 함**(리서치 산출물, 배포 무관)
- 산출물 전부 `docs/research/ulleung-gukjido-90/` — `README.md`(13차 개정), `maps/` 판독도 12장, `data/`, 렌더러 `*.py`
- 제6차 국도·국지도 울릉군 2개 구간(사동~도동, 도동~저동)의 **토지보상 편입 부지를 좌표로 특정**한 방.
  노선 미공표 → 위성·지적편집도·로드뷰·네이버 실측선을 어파인 정합(RMS 2~3.4 m)해 역산
- 마지막 커밋 `fc55219` (13차 개정 — 12차 단면 오류 정정)

## 확정 결론 (다시 계산하지 말 것)
- **A갱구 130.908918, 37.482490** (저동 방면) / **B갱구 130.907939, 37.482038** (사동 방면), 이격 **100.1 m**
- A→B 방위 239.8° vs B터널 축 235.8° → **차이 4.0°**, 두 갱구는 이미 한 선형. 절선각 A 46.7° / B 4.0°
- **도동항은 통과점이 아니라 결절점.** 부두 상부 고가안은 9차에서 폐기(주차 악화·목적 미달).
  채택: **부두 평면 집산로 + A갱구 가설야드의 준공 후 주차장 전용**
- **보상 확률 A > B.** A는 사유지 중심(현금 보상), B는 소공원·해경출장소·항만시설이라 관리전환(무상) 비중 큼
- 편입 등급(갱구 중심 거리): 1등급 0~35 m / 2등급 35~60 m / 3등급 60~90 m / 회랑 100 m×24 m.
  지번 목록은 README 10차 표. 90 m 밖 편입 없음
- **죽도관광 앞 도동길 5.0 m** → 8 m 확폭 필요(888 ㎡)이나 **북동측(갱구측) 나지에서 흡수**.
  → 죽도관광·영일모텔·해산촌·농어민장터 **편입 없음**, 보행교 **무관**. A측 편입은 갱구 원에서 닫힘

## 바로 이어갈 작업
1. **사토장 후보지 좁히기** (TODO #1) — 굴착 후 20만 ㎥, 성토고 10 m면 2만 ㎡. **갱구보다 큰 편입이 될 수 있는
   유일 항목**인데 위치 미정. 울릉공항의 가두봉 절취토 → 사동항 방파제 밖 매립 선례부터 확인
2. **아티팩트 HTML 갱신** (TODO #2) — `ulleung-90-compensation.html`이 7차 시점. 8~13차 정정과 새 판독도 5장 반영.
   사장님께 제안했으나 응답 없어 보류 중이니, 먼저 물어보고 진행
3. 환기구·수직갱 위치(TODO #3), 부두 안벽 여유(TODO #4)

## 대기/차단
- **체크포인트 문서를 main에 커밋하는 건 보류.** 이 세션은 지정 브랜치 외 푸시 금지 제약이 걸려 있어
  `claude/ulleung-bypass-road-analysis-bh7zu4`에만 올렸다. main 반영은 **사장님 승인 후**
- 아티팩트 갱신 여부 — 사장님 응답 대기

## 주의·제약
- 이 방의 브랜치 외로 푸시 금지. PR·배포 대상 아님(리서치 문서)
- **네트워크**: molit·law·gb·ulleung·vworld·nsdi·eum·kras·ngii·data.go.kr·wikipedia·nominatim·overpass **전부 차단**.
  가용은 WebSearch, 네이버 지역검색 MCP, GitHub clone, PyPI뿐
- 사장님 제공 이미지는 **세션 트랜스크립트 JSONL의 base64**에서 복구해 쓴다
  (`/root/.claude/projects/-home-user-desktop-tutorial/<sessionId>.jsonl`, `type=="image"`의 `source.data`)
- **결론을 내라.** 옵션 나열만 하면 지적받는다(이 세션에서 두 번). 틀리면 즉시 정정하고 철회를 명시
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01WLmtZkRJypXJ4dZRWrn4rv`. 모델 ID는 트레일러에만
- 지어낸 수치 금지. 못 잰 값은 «—». 전 항목이 **추정**임을 도판·문서에 명시

## 참고
- 판독도 재현: `docs/research/ulleung-gukjido-90/`의 `overlay.py`·`mark.py`·`optimize.py`·`lcp.py`·
  `config.py`·`config2.py`·`comp.py`·`flow.py`·`sec.py`·`dir.py`. 정합 파라미터는 `data/georef.json`·`geo_15.json`
- 정합식: `px = a + s·lon`, `py = b − s·merY(lat)`, `merY(lat)=degrees(log(tan(π/4+radians(lat)/2)))`
- 한글 렌더는 Pretendard woff2 → ttf 변환본 사용(fontTools + brotli)
