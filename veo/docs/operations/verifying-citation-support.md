# 인용 지원 확인 절차

`CITATION_CAPABLE_MODEL_PREFIXES` 에 모델을 추가하기 전에 **반드시 실제 호출로**
확인한다. 이 문서는 그 방법과, 왜 문서를 믿으면 안 되는지를 남긴다.

## 왜 필요한가

인용 지표는 `citations` 가 비었을 때 두 가지 중 하나를 뜻한다.

| 뜻 | 기록 | 점수에서 |
|---|---|---|
| 찾아봤지만 우리를 인용하지 않았다 | `STRUCTURED` + `citations=()` | 인용률 분모에 들어가고 0회로 센다 |
| 이 응답으로는 출처를 알 수 없다 | `NOT_EXPOSED_BY_PROVIDER` | **분모에서 빠진다** — 측정 불가 |

둘을 섞으면 고객에게 **"AI 가 당신을 한 번도 인용하지 않습니다"** 라고 보고하게 된다.
지어낸 값보다 나쁘다 — 지어낸 줄도 모른다.

그래서 능력은 **선언**한다. 응답 모양으로는 가를 수 없기 때문이다: 인용을 못 돌려주는
모델도 `annotations` 키를 빈 배열로 담아 보내고 `web_search_call` 도 남긴다.

## 문서를 믿으면 안 되는 이유 — 실측 기록

2026-07-30, 같은 질문에 `web_search` 도구를 붙여 호출했다.

| 모델 | `url_citation` | 판정 |
|---|---:|---|
| `gpt-5` | 6개 | 확인됨 |
| `gpt-4o` | 2개 | 확인됨 |
| `gpt-4.1` | 0개 | 못 돌려준다 |
| `gpt-4o-mini` | 0개 | 못 돌려준다 |

`gpt-4.1` 이 못 돌려준다는 것은 문서만 보고는 알 수 없었다. **새 이름이 붙었다고 능력이
따라오지 않고, 버전이 올라갈수록 좋아진다는 가정도 성립하지 않는다.**

## 확인 방법

`veo/apps/api` 에서 아래를 돌린다. 자격증명은 설정에서 읽으며 값을 출력하지 않는다.

```bash
VEO_SCORING_SPECS_DIR="$PWD/../../packages/scoring-specs" PYTHONPATH="$PWD/src" \
  ../../.venv/bin/python -c "
import httpx
from veo.core.settings import get_provider_credentials

MODEL = 'gpt-5'          # ← 확인할 모델 이름만 바꾼다
key = get_provider_credentials().openai_api_key.get_secret_value()
r = httpx.post('https://api.openai.com/v1/responses',
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'model': MODEL,
          'input': '오늘 서울 주요 뉴스를 웹에서 찾아 출처와 함께 알려주세요.',
          'tools': [{'type': 'web_search'}]}, timeout=180)
payload = r.json()
found = [a for o in payload.get('output', []) for c in (o.get('content') or [])
         for a in (c.get('annotations') or []) if a.get('type') == 'url_citation']
print(f'{MODEL}: HTTP {r.status_code}, url_citation {len(found)}개')
"
```

**판정 기준**

- `url_citation` 이 **1개 이상** 나오면 그 모델은 인용을 돌려준다 → 목록에 추가한다.
- **0개**면 추가하지 않는다. 질문을 바꿔 두세 번 더 시도해 보되, 계속 0개면 그 모델로는
  인용 지표를 재지 않는다.

질문은 **인용이 나올 수밖에 없는 것**으로 고른다. 모델이 자기 지식만으로 답할 수 있는
질문이면 인용이 없는 것이 정상이고, 그때의 0개는 능력에 대한 증거가 아니다.

## 추가할 때

`apps/api/src/veo/observations/providers/openai.py` 의
`CITATION_CAPABLE_MODEL_PREFIXES` 에 접두어를 넣고, 위 표에 측정값과 날짜를 남긴다.

접두어 대조는 날짜 변형만 같은 모델로 본다 — `gpt-4o` 는 `gpt-4o-2024-11-20` 을 포함하고
`gpt-4o-mini` 는 **포함하지 않는다**. 그 구분이 이 장치가 존재하는 이유다.

## 다른 제공자

| 제공자 | 판정 방식 |
|---|---|
| OpenAI | 모델 능력 선언 (위) — 응답 모양으로 가를 수 없다 |
| Gemini | 응답의 `groundingMetadata` 유무 |
| Perplexity | 응답의 `citations` 필드 유무 |
| Anthropic | 응답의 `web_search_tool_result` 블록 유무 |

뒤의 셋은 응답이 인용 구조를 담고 있는지로 판정한다. 담고 있지 않으면 그 응답은 출처에
대해 아무 말도 하지 않은 것이고, 그것을 0건으로 옮기면 없는 사실을 만들어 낸다.

**Gemini·Perplexity·Anthropic 은 자격증명이 없어 실측하지 못했다.** 판정 방식은 문서와
응답 스키마에 근거한 것이므로, 자격증명이 들어오면 위 절차로 확인해야 한다.
