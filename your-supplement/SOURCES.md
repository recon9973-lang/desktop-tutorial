# 📚 공인 출처 가이드 (의약품·영양제)

이 서비스의 모든 추천·정보는 **광고성 블로그·커뮤니티가 아닌, 정부기관·공인기관의 1차 출처**를 근거로 한다.
구조화 데이터는 `data/sources.json` (추천 결과의 '근거 보기' 링크에 사용).

## 🇰🇷 국내 공식 사이트

| 사이트 | 운영 | 무엇을 확인 | 특징 |
|--------|------|-------------|------|
| **의약품안전나라** [nedrug.mfds.go.kr](https://nedrug.mfds.go.kr) | 식약처 | 국내 허가 의약품 성분·효능·용법·부작용·임부금기 | `e약은요` = 소비자용 쉬운 요약 |
| **식품안전나라** [foodsafetykorea.go.kr](https://www.foodsafetykorea.go.kr) | 식약처 | 건강기능식품 기능성·권장섭취량·주의사항 | 진짜 '건강기능식품' vs '기타가공품' 구별 |
| **약학정보원** [health.kr](https://www.health.kr) | 대한약사회 | 약 식별(모양·색·기호), 약리작용, 약-약 상호작용 | 약 모양/각인 검색 최적 |

## 🌎 해외 공식 사이트 (직구·심층 분석)

| 사이트 | 운영 | 무엇을 확인 | 특징 |
|--------|------|-------------|------|
| **NIH ODS** [ods.od.nih.gov](https://ods.od.nih.gov) | 미국 국립보건원 | 성분별 근거등급·임상효과·상한섭취량(UL) | 소비자용/전문가용 이원화, 최고 권위 |
| **MedlinePlus** [medlineplus.gov](https://medlineplus.gov) | 미국 국립의학도서관 | 약·영양제 효능·상호작용 위험 | Drugs & Supplements, A-Z 색인 |
| **ConsumerLab** [consumerlab.com](https://www.consumerlab.com) | 민간 독립검사 | 라벨 함량 실측·중금속 검사 | 일부 유료, 순위·경고는 확인 가능 |
| **Labdoor** [labdoor.com](https://labdoor.com) | 민간 독립검사 | 함량 실측·오염도·제품 점수 | 직구족 품질 지표 |

> ⚠️ ConsumerLab·Labdoor는 **효능 근거가 아니라 '제품 품질·함량' 검증**용. 효능 근거는 식약처/NIH ODS 기준.

## 🔎 상황별 추천 검색 경로

```
처방약·약국 일반약        → 약학정보원 또는 의약품안전나라
국내 영양제 허가·부작용    → 식품안전나라
해외 직구 영양제 효능·과다  → NIH ODS
영양제 실제 함량·오염 검증  → ConsumerLab / Labdoor
```

## 서비스 적용
- 추천 카드의 근거등급(⭐⭐⭐ 식약처 / ⭐⭐ NIH·논문)은 위 출처 tier와 연결.
- `data/sources.json`의 `evidence_tier`로 신뢰도를 표기하고, `url`로 '근거 원문 보기' 링크 제공.
- 향후 DUR(약-영양제 병용금기)·낱알식별 기능은 약학정보원·식약처 데이터와 직접 연동.
