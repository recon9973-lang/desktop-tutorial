# 🔌 당신의영양제 — 실제 연결 API 목록

> 배포(Vercel) 환경은 외부망 개방 → 아래 API는 배포 시 실제 동작.
> 상태: ✅연동완료(코드 있음) · 🟡연동예정(코드 스캐폴드/키 필요) · ⬜후보(설계만)
> 키는 전부 **선택** — 없으면 샘플/딥링크로 graceful 동작.

---

## 1. 이미 연동된 API (코드 존재)

| # | API | 용도 | 엔드포인트 | 키(환경변수) | 상태 |
|---|-----|------|-----------|-------------|------|
| 1 | **NIH DSLD** (Dietary Supplement Label Database) | 시판 영양제 **제품 검색**(라벨 20만건+) | `https://api.ods.od.nih.gov/dsld/v9/search-filter?q=&size=` | **불필요(CC0)** | ✅ `/api/products` |
| 2 | **네이버쇼핑 검색** | 성분별 **최저가** | `https://openapi.naver.com/v1/search/shop.json` | `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` | ✅ `/api/offers` |
| 3 | **국립중앙의료원 E-Gen**(공공데이터) | **약국·응급실** 위치 | `http://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyListInfoInqire` (약국) · `.../ErmctInfoInqireService/getEgytListInfoInqire` (응급실) | `DATA_GO_KR_KEY` | ✅ `/api/nearby` |
| 4 | **카카오맵 JS SDK** | 지도 임베드 | `//dapi.kakao.com/v2/maps/sdk.js?appkey=` | `NEXT_PUBLIC_KAKAO_MAP_KEY` | ✅ `KakaoMap.jsx` |

---

## 2. 연동 예정 — 키 활용신청만 하면 되는 국내 공공데이터 (data.go.kr)

| # | API | 용도 | 데이터셋 | 키 | 상태 |
|---|-----|------|---------|----|------|
| 5 | **식약처 건강기능식품 품목정보** | **국내 시판 제품** 검색(제품→성분) | data.go.kr `15056760` | `DATA_GO_KR_KEY`(품목 서비스 활용신청) | 🟡 `/api/products`에 국내 소스로 추가 |
| 6 | **식약처 기능성 원료 인정현황** | 성분 KB **자동 확장**·국내 인정문구(D1·D2) | data.go.kr `15058359` | `DATA_GO_KR_KEY` | 🟡 G3 |
| 7 | **식약처 DUR(의약품안전사용)** | **병용금기/임부·노인주의** 수천종(P5 확장) | data.go.kr `15059486` | `DATA_GO_KR_KEY` | 🟡 DUR 데이터 확장 |
| 8 | **식약처 의약품 낱알식별** | "이 알약 뭐지?" 식별 → DUR 연결 | data.go.kr `15057639` | `DATA_GO_KR_KEY` | ⬜ IDEAS 로드맵 C |
| 9 | **식의약 데이터포털(HID)** | 건기식 영양DB·기능성 raw | `https://data.mfds.go.kr/` | 활용신청 | ⬜ 검수 자동화 |

> ⚠️ data.go.kr는 데이터셋별로 **활용신청**이 따로 필요(키는 동일 계정). nearby에서 쓰는 키와 같은 `DATA_GO_KR_KEY` 계정에 위 서비스들을 추가 신청.

---

## 3. 글로벌 권위 API (성분 근거 보강)

| # | API | 용도 | 엔드포인트 | 키 | 상태 |
|---|-----|------|-----------|----|------|
| 10 | **NIH ODS API** | 성분 fact sheet·근거 | `https://ods.od.nih.gov/api/` | 불필요 | ⬜ 코퍼스 자동화 |
| 11 | **openFDA (CAERS)** | 보충제 **이상사례·부작용 신호** | `https://api.fda.gov/food/event.json` | 불필요(등록 시 rate↑) | ⬜ 안전 보강 |
| 12 | **EFSA** | 건강강조표시 EU 과학평가 | EFSA Developer Portal(키 등록) | 키 | ⬜ 효능주장 대조 |
| 13 | **Health Canada LNHPD** | 캐나다 허가 제품(글로벌 확장) | `https://health-products.canada.ca/api/natural-licences/` | 불필요 | ⬜ 제품 글로벌 확장 |
| 14 | **NCBI E-utilities (PubMed)** | 논문 근거 검색 | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | 불필요(키 시 rate↑) | ⬜ 근거 링크 |

> PDF 발행이라 **API 없는** 권위 출처(인용만): WHO 약용식물 모노그래프 · Codex · EMA HMPC · NCCIH · Cochrane(12개월 후 무료).

---

## 4. 발송/알림

| # | API | 용도 | 키 | 상태 |
|---|-----|------|----|------|
| 15 | **카카오 알림톡** | 추천 결과·복용 알람 발송 | `KAKAO_API_KEY`·`KAKAO_SENDER_KEY`·템플릿ID | 🟡 `server/api/kakao.js` 스캐폴드 |

---

## 5. 우선순위 (연결 권장 순서)

1. **5·6 식약처 품목·원료 API** — "국내 시판 모든 영양제" + 신뢰도(D1·D2) 동시 해결. (키 활용신청)
2. **7 식약처 DUR** — 병용금기 수천종으로 안전 강화.
3. **11 openFDA / 10 NIH ODS** — 안전·근거 자동 보강(키 불필요).
4. **15 카카오 알림톡** — 앱 닫아도 오는 복용 알림(리텐션).

> 1·2·3은 배포 환경에서 바로 호출 가능(이 샌드박스는 외부망 차단이라 호출 불가, 코드만 준비).
