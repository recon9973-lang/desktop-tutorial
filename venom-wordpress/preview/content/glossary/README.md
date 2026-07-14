# 용어사전 원본 데이터 (백업)

사이트 용어사전(`assets/glossary.js`)에 통합된 **검증본 CSV 원본**의 보관본입니다.
글로서리 데이터를 다시 생성·검증하거나 출처를 추적할 때 이 원본을 기준으로 삼습니다.

| 파일 | 항목 | 통합 대상 | 비고 |
|---|---|---|---|
| `ai_glossary_advanced_150.csv` | 150 | AI 용어사전 | 중복 12 대체·고유 13 보존 → AI 163개 (#158) |
| `seo_aeo_geo_glossary_advanced_150.csv` | 150 | SEO 용어사전 | 중복 31 대체·고유 66 보존 → SEO 216개 (#159) |

## 컬럼
`id, category, badge_label, korean_term, english_term, acronym, short_definition,
detailed_definition, example, related_terms, source_1_name, source_1_url,
source_2_name, source_2_url, verification_note, confidence, audit_status`

- 카드 요약: `short_definition` · 모달 상세: `detailed_definition`·`example`·`related_terms`·출처 2개
- 전 항목 `audit_status=verified` (신뢰도 high 위주)

## 렌더 데이터로 반영하는 법
`assets/glossary.js`의 `TERMS` 배열이 실사용 데이터입니다. CSV → JS 변환은
카테고리 매핑(badge/category → cat 키)과 이스케이프 처리가 필요하므로,
원본을 수정했으면 동일 매핑 규칙으로 `TERMS`의 해당 사전 블록을 재생성하세요.
사전별 카테고리: AI(ai_basic·ai_geo·ai_tech·ai_risk·ai_gov·ai_metric),
SEO(basic·engine·keyword·technical·link·optimize + seo_geo·seo_aeo·seo_local·seo_metric·seo_risk).
