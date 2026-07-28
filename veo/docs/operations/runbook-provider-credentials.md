# 런북 — 제공자 자격증명 이관과 회전

## 현재 상태 (2026-07-28)

| 제공자 | 상태 | 출처 |
|---|---|---|
| `NAVER_DATALAB` | ENABLED | `your-supplement/.env` 에서 이관 |
| `OPENAI` | ENABLED | **`flowlens/.env.local` 에서 이관 — 임시** |
| `NAVER_SEARCH_AD` | DISABLED_NO_CREDENTIAL | 값이 ERP Vercel 에만 있음 |
| `GOOGLE_SEARCH_CONSOLE` | DISABLED_NO_CREDENTIAL | 동일 |
| `GOOGLE_PAGESPEED` | DISABLED_NO_CREDENTIAL | 미발급 |

확인:  `make providers`  (이름과 상태만 출력, 값은 절대 출력하지 않음)

## 결정 사항 — Phase 4 시작 전에 반드시 처리

현재 `VEO_OPENAI_API_KEY` 는 **FlowLens 프로젝트의 키**다. 지금은 호출하는 코드
경로가 없어서 실제 요청이 0회이고 비용도 0원이지만, Phase 4 의 GEO 실제 관측이
켜지는 순간 FlowLens 와 같은 계정에서 비용이 나가기 시작한다.

**Phase 4 착수 전에 ERP 자격증명으로 교체한다.** 그때 검색광고(검색량·CPC)도 함께
들어오므로 한 번에 정리된다.

미루면 생기는 문제:
- 청구서에서 어느 제품이 얼마 썼는지 나눌 수 없다.
- 키를 회전하면 두 제품이 동시에 멈춘다.
- "언제부터 다른 프로젝트 쿼터를 쓰고 있었는지" 나중에 추적하기 어렵다.

## 절차

ERP 프로젝트 폴더에서:

```bash
npx vercel env pull .env.erp --environment=production
```

VEO 에서 (값은 화면에 출력되지 않는다):

```bash
cd ~/Desktop/desktop-tutorial/veo
infra/scripts/import-provider-credentials.sh ../<ERP폴더>/.env.erp
make providers
```

원본 삭제:

```bash
rm -f ../<ERP폴더>/.env.erp
```

### 이름 매핑

스크립트가 자동으로 바꾼다. VEO 는 같은 '네이버'라도 검색광고(절대 검색량)와
데이터랩(상대 지수)을 다른 데이터로 취급하므로 이름부터 분리한다.

| ERP | VEO |
|---|---|
| `NAVER_AD_API_KEY` | `VEO_NAVER_SEARCHAD_API_KEY` |
| `NAVER_AD_SECRET` | `VEO_NAVER_SEARCHAD_SECRET_KEY` |
| `NAVER_AD_CUSTOMER_ID` | `VEO_NAVER_SEARCHAD_CUSTOMER_ID` |
| `NAVER_CLIENT_ID/SECRET` | `VEO_NAVER_DATALAB_CLIENT_ID/SECRET` |
| `OPENAI_API_KEY` | `VEO_OPENAI_API_KEY` |

## 검색광고 키가 들어온 날 반드시 눈으로 확인할 것

**CTR 단위가 퍼센트인지 비율인지 검증되지 않았다** (`monthlyAvePcCtr`).
100배 틀릴 수 있고 **어떤 테스트도 잡지 못한다.** 실제 응답을 받아 사람이 대조해야
한다. 알려진 키워드 하나로 조회해 CTR 이 `2.3` 인지 `0.023` 인지 확인한다.

서명 규칙(ms 타임스탬프, 쿼리 제외 경로)도 문서 기준으로만 구현됐다. 틀리면 전부
401 → `UNKNOWN` 이 되지, 가짜 숫자가 나오지는 않는다.

## 호출 한도

검색광고 API 는 `CUSTOMER_ID` 단위로 한도가 걸린다. ERP 와 VEO 가 같은 계정을 쓰면
한쪽의 대량 조회가 다른 쪽을 429 로 막는다. 운영 진입 시 계정 분리를 권한다.

## 안전 규칙

- `veo/.env` 는 `.gitignore` 에 있고 권한은 `600` 이다. 커밋 전 항상 확인한다.
- 값을 채팅·터미널·로그에 붙여넣지 않는다. 이관은 스크립트로만 한다.
- 테스트에는 실제 자격증명을 쓰지 않는다. 네트워크가 죽으면 테스트가 거짓으로 실패한다.
- 금고(`veo/credentials/`)에 저장된 자격증명은 **되읽을 수 없다.** 마스터 키를 잃으면
  복구 불가이며, 설계상 평문 사본이 없다.
