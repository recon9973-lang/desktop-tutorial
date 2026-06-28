# "당신의 영양제" — 데이터 모델 (v0.1)

객관적 근거 기반 개인 맞춤 영양제 추천 서비스의 데이터 백본.

## 설계 원칙
- **근거 ≠ 후기**: 추천 점수는 검증된 근거(식약처/논문)로만 계산. 사용자 별점·의견은 별도 레이어(`reviews`)에 두고 참고용으로만 표시.
- **추적 가능성**: 모든 추천은 출처(MFDS 고시 / NIH ODS / 논문 PMID)를 동반.
- **빼는 추천**: 복용약·알레르기 기반 제외도 적극 제시.

---

## 시드 데이터 (정적, 운영자 검수)
| 파일 | 엔티티 | 내용 |
|------|--------|------|
| `ingredients.json` | 성분 마스터 | 기능성·근거등급·용량·**복용기간타입(🟢🟡🔴)**·주의·약물플래그 |
| `concerns.json` | 고민↔성분 | 10개 대표 고민별 추천 성분(우선순위) |
| `interactions.json` | 상호작용 | 시너지 / 길항(시간차) / **의약품 경고** |
| `recommendation_rules.json` | 추천규칙 | 점수 공식·가중치·제외규칙·복용기간정책 |

---

## 동적 데이터 (사용자별, DB)

### 1. user — 사용자
```json
{
  "id": "u_123",
  "channel": { "kakao_id": "...", "consent_push": true },
  "profile": { "age": 34, "sex": "F" },
  "medications": ["warfarin"],
  "allergies": ["milk"],
  "concerns": ["fatigue", "eye"]
}
```

### 2. recommendation — 추천 결과(스냅샷)
```json
{
  "id": "rec_456", "user_id": "u_123", "created_at": "2026-06-28T09:00:00Z",
  "items": [
    { "ingredient_id": "omega3", "score": 0.92, "evidence_level": 3,
      "duration_type": "continuous", "warnings": ["warfarin"],
      "best_offer_id": "off_a1" }
  ],
  "schedule": { "morning": ["vitamin_d"], "evening": ["omega3"] },
  "not_recommended": [{ "ingredient_id": "red_yeast_rice", "reason": "스타틴 복용 중 병용 금지" }]
}
```

### 3. review — 사용자 별점·의견 ⭐ (근거와 분리)
> 점수 계산에 **미반영**. 성분/제품 상세에서 "참고 정보"로만 노출.
```json
{
  "id": "rv_1", "user_id": "u_123",
  "target": { "type": "ingredient", "id": "omega3" },
  "rating": 4,
  "comment": "2주 먹으니 트림 줄고 괜찮아요",
  "created_at": "2026-06-28T10:00:00Z",
  "helpful_count": 3,
  "is_objective_source": false
}
```

### 4. price_offer — 최저가 구매처 💰
> 핵심: **유효성분 함량당 단가**로 비교(용량 제각각이라 단순 가격은 무의미).
```json
{
  "id": "off_a1", "ingredient_id": "omega3",
  "product_name": "○○ 알티지 오메가3 1000mg",
  "vendor": "naver_shopping",
  "url": "https://...",
  "price": 21900,
  "count": 90,
  "active_mg_per_unit": 1000,
  "price_per_active_mg": 0.243,
  "updated_at": "2026-06-28T08:00:00Z",
  "source": "naver_shopping_api"
}
```
- 수집: **네이버쇼핑 API 우선**(제휴/공식). 크롤링 차단 사이트는 지양.
- 랭킹 키: `price_per_active_mg` 오름차순 → "가성비 랭킹".

### 5. my_supplement — 내 영양제 등록 📦
```json
{
  "id": "my_1", "user_id": "u_123",
  "ingredient_id": "omega3",
  "product_name": "○○ 오메가3",
  "started_at": "2026-06-01",
  "from_recommendation": "rec_456",
  "duration_type": "continuous",
  "review_due_at": null
}
```
- 등록 시 `interactions.json`로 **내 조합 충돌 자동 점검**(예: 칼슘+철분 시간차 안내).
- `duration_type`이 monitor/cyclic이면 `recommendation_rules.duration_policy`로 **점검 알림** 자동 예약.

### 6. intake_schedule — 섭취 시간·알람 ⏰
```json
{
  "id": "sch_1", "user_id": "u_123", "my_supplement_id": "my_1",
  "times": ["08:00", "20:00"],
  "days": ["mon","tue","wed","thu","fri","sat","sun"],
  "channel": "kakao",
  "active": true,
  "next_fire_at": "2026-06-29T08:00:00Z"
}
```
- 알람 채널: **카카오 알림톡** 또는 앱 푸시(둘 다 지원).
- 스케줄러가 `next_fire_at` 도래 시 발송 → `notification` 생성.

### 7. kakao_message — 카카오톡 전송 페이로드 💬
> 추천 결과 전송 + 복용 알람, 두 용도.
```json
{
  "id": "msg_1", "user_id": "u_123",
  "type": "recommendation",            // 또는 "intake_reminder"
  "template": "your_supplement_result",
  "payload": {
    "title": "🧬 OO님의 영양제",
    "items": ["오메가3(중성지방·근거⭐⭐⭐)", "비타민D(뼈·근거⭐⭐⭐)"],
    "schedule": "아침: 비타민D / 저녁: 오메가3",
    "best_price": "오메가3 최저가 21,900원(네이버쇼핑)",
    "link": "https://app/rec/rec_456"
  },
  "status": "queued"
}
```
- 구현: 카카오 비즈니스 채널 + **알림톡(정보성)** / 친구톡. 발송 전 사용자 채널 동의(`consent_push`) 필수.
- 정보성 메시지로 설계해 광고성 규제 회피.

---

## 데이터 흐름 요약
```
설문(concerns/medications/allergies)
   ↓  recommendation_rules + ingredients + interactions
추천 결과(recommendation) ──→ price_offer 결합(최저가)
   ↓                              ↓
카카오 전송(kakao_message)     내 영양제 등록(my_supplement)
   ↓                              ↓
                          섭취 알람(intake_schedule) → 카카오/푸시
별점·의견(review) … 근거와 분리된 참고 레이어
```
