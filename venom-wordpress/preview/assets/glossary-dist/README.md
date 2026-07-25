# VENOM 용어사전 배포 키트

SEO·AI·마케팅·개발 **723개 용어**를 타 사이트에 임베드하거나 데이터로 활용하기 위한 배포 파일 모음.

| 파일 | 용도 |
|---|---|
| `glossary-data.json` | **순수 데이터**(723개 용어) — 어떤 프레임워크로든 직접 렌더링 |
| `../glossary.js` | **드롭인 위젯**(검색·초성·카테고리·상세 모달) — 자체 CSS 주입, 의존성 0 |
| `embed-example.html` | 두 방식(위젯 / JSON 직접 렌더)을 보여주는 실행 예제 |

기준 배포 URL(예): `https://venom-new-site.vercel.app/assets/`

---

## 방식 A — 위젯 임베드 (가장 간단)

```html
<div id="glossary-root"></div>
<script src="https://venom-new-site.vercel.app/assets/glossary.js"></script>
<script>Glossary.mount('glossary-root');</script>
```

- 검색·초성(ㄱㄴㄷ)·ABC·카테고리 필터·상세 모달까지 포함.
- **자체 CSS를 주입**하며 host 디자인 토큰(`--p`, `--ink2`, `--border` 등)이 있으면 자동으로 맞추고, 없으면 기본값으로 폴백 → 어떤 사이트든 그대로 동작.
- 전역 API: `Glossary.mount(elementId)`, `Glossary.TERMS`, `Glossary.DICTS`, `Glossary.count`.

## 방식 B — 데이터(JSON)만 사용해 직접 렌더링

```js
const res = await fetch('https://venom-new-site.vercel.app/assets/glossary-dist/glossary-data.json');
const data = await res.json();
data.terms.forEach(t => {
  // t = { ko, en, def, category, dict, abbr, detail, example, related[], sources[] }
});
```

프레임워크(React/Vue/Svelte)·정적 사이트·워드프레스 어디서든 자유롭게 UI를 구성하세요.

---

## 데이터 스키마 (`glossary-data.json`)

```jsonc
{
  "name": "VENOM 용어사전 데이터",
  "version": "1.0.0",
  "counts": { "total": 723, "byDict": { "seo": 230, "ai": 163, "marketing": 166, "dev": 164 } },
  "dicts":      { "seo": { "label": "SEO 용어사전", "abbr": "SEO", "color": "#533afd" }, ... },
  "categories": { "basic": { "label": "기본 용어", "color": "#533afd", "dict": "seo" }, ... },
  "terms": [
    {
      "ko": "SERP",                        // 한글 용어(표시 기준)
      "en": "SERP",                        // 영문
      "def": "검색엔진 결과 페이지…",       // 한 줄 정의
      "category": "basic",                 // categories 키
      "dict": "seo",                       // seo | ai | marketing | dev
      "abbr": null,                        // 약어(있으면)
      "detail": "사용자가 검색어를…",        // 상세 설명(있으면)
      "example": "‘강남 피부과’ 검색 시…",  // 사용 예(있으면)
      "related": ["자연검색", "피쳐드 스니펫"], // 연관 용어
      "sources": [{ "label": "Google Search Central", "url": "https://…" }]
    }
  ]
}
```

### 필드 요약
- **필수**: `ko`, `en`, `def`, `category`, `dict`
- **선택**: `abbr`, `detail`, `example`, `related[]`, `sources[{label,url}]`
- 정렬은 한글 `ko` 기준(`localeCompare('ko')`) 권장.
- `dict`로 4개 사전(SEO/AI/마케팅/개발)을 분리, `category`로 세부 분류(총 37개).

---

## 라이선스·주의
- 출처(`sources`)는 Google Search Central 등 공식 문서 링크 — 재배포 시 함께 표기 권장.
- 데이터는 `glossary.js`의 `TERMS`에서 생성됩니다. 원본이 갱신되면 아래로 재생성:
  ```bash
  node scripts/gen-glossary-data.mjs   # (아래 참고) 또는 dist 재추출 스크립트
  ```
- 갱신 시 `version`을 올리세요.
