# 🩺 의료광고심의 도우미 챗봇 (Medical Ad Review Assistant)

> **VENOM 사이트 부속 독립 모듈** — 의료법·의료광고심의 기준을 근거로, 병원 광고 문구·소재의 심의 통과 가능성을 진단하고 대안을 제시하는 RAG 기반 웹 챗봇.
>
> 이 폴더(`preview/chatbot/`)는 기존 VENOM 사이트와 **별도로 표기·관리되는 챗봇 전용 모듈**입니다.

---

## 목적

- 의료광고 / 의료광고심의 / 의료법 Q&A
- 광고 문구 **자가진단**(위반 소지 하이라이트 + 근거조항 + 안전 대체표현)
- **근거 인용형 답변**(조항·심의사례를 출처와 함께 제시) — 환각 최소화

> ⚠️ **면책**: 본 챗봇은 참고용 사전 진단 도구입니다. 실제 심의 승인·반려는 자율심의기구(대한의사협회 등)의 심의 결과에 따르며, 본 답변이 이를 보장하지 않습니다.

---

## 방식 (확정)

| 항목 | 결정 |
|---|---|
| AI 방식 | **RAG**(검색 증강 생성) — 지식베이스에서 근거를 검색해 LLM이 인용하며 답변 |
| 배포 | **웹 챗봇**(VENOM 사이트 임베드; `/medical-ad-review` 라우트 기반) |
| "무한 반복 학습" | 모델 재학습이 아닌 **자동 평가·개선 루프(LLM-as-Judge)** 로 구현 |

---

## 폴더 구조

```
chatbot/
├── README.md               ← (이 파일) 모듈 개요·별도 표기
├── PLAN.md                 ← 최종 기획서 (아키텍처·로드맵·데이터 전략)
├── data/
│   ├── sources/            원천 자료(승인)
│   │   ├── medical-ad-casebook.md   복지부 사례집 2판(2024.12)
│   │   └── sources.json             소스 레지스트리(출처·라이선스·수집일)
│   └── kb/                 파이프라인 산출물 (build.js output)
│       ├── knowledge-base.json      RAG 청크 + 메타(출처·근거조항·태그)
│       ├── qa-seed.json             핵심 Q&A 시드
│       ├── forbidden-rules.json     금지어·위험어·안전 대체표현(자가진단 룰엔진)
│       ├── retrieval-index.json     키워드 역색인(하이브리드 검색 키워드 축)
│       └── manifest.json            빌드 요약
└── pipeline/
    ├── build.js            원천 → 지식베이스 빌드 (결정론적, 네트워크 불필요)
    └── retrieve.js         키워드 검색 스모크 테스트 / 레퍼런스 구현
```

## 빌드 / 검증

```bash
cd venom-wordpress/preview/chatbot
node pipeline/build.js                       # 지식베이스 재빌드
node pipeline/retrieve.js "전후사진 허용 요건"   # 검색 동작 확인
```

## 현재 상태

- ✅ **Phase 1 — 데이터 파이프라인**: 사례집 → 24 청크(근거조항 31종), Q&A 12, 금지/위험 표현 65개, 안전 대체표현 13, 역색인 899토큰. 키워드 검색 end-to-end 검증 완료.
- ✅ **Phase 3(1차) — 챗봇 API + 웹 데모**: `preview/api/chatbot.js`(RAG 응답·문구 자가진단), `lib/retriever.js`·`lib/rag.js`, `demo.html`(웹 UI). LLM 키 없이도 근거 요약·룰 진단으로 동작(폴백). 오프라인 스모크 테스트 6/6 통과.
- 🟡 **Phase 2(진행) — 검색 고도화·데이터 보강**:
  - ✅ 도메인 동의어 확장(`data/synonyms.json`, 87토큰) → recall 향상(예: "후기"→치료경험담 제2호 매칭)
  - ✅ 임베딩 파이프라인(`pipeline/embed.js`) + 하이브리드 검색 훅(embeddings.json 생성 시 자동 활성)
  - ✅ 조문 수집기(`pipeline/fetch-statutes.js`, law.go.kr DRF API) — 키/허용망 제공 시 즉시 실행. *현 환경은 law.go.kr 접근이 프록시 차단되어 pending 기록.*
  - ⬜ 협회 심의기준·FAQ 수집
- ✅ **Phase 4 — 평가셋·개선 루프**:
  - 질문 10,000개 생성(`pipeline/gen-questions.js`) — 11개 카테고리, 난이도·근거조항 라벨, 홀드아웃 1,000 분리(오더 2번)
  - 평가·개선 루프(`pipeline/eval-loop.js`, 오더 3번: 질문→답변→검토→진단→수정) — **인용 적중률 92.2%** / 문구진단 정합 100%(전체 10,000). 진단→동의어 보강→재평가로 표시광고법 46%→임계 통과 실증.
- ⬜ 남은 작업 — LLM-as-Judge 정답 품질 채점(키 필요), 협회 심의기준·조문 원문 보강(허용망 필요), 사이트 임베드 위젯

### 평가 루프
```bash
node pipeline/gen-questions.js       # 질문 10,000개 생성
node pipeline/eval-loop.js           # 홀드아웃 1,000 평가·진단
node pipeline/eval-loop.js --all     # 전체 10,000 평가 → data/eval/eval-report.json
```

> **하이브리드/조문 활성화**: `OPENAI_API_KEY` 설정 후 `node pipeline/embed.js` → 벡터 검색 자동 on. `LAW_OC=<법령API OC>` 설정 후 `node pipeline/fetch-statutes.js` → 조문 원문 수집(허용망 필요).

## API

```
POST /api/chatbot  { "message": "...", "mode": "qa" | "diagnose" }
  qa       → { answer, sources[], grounded, llm }   근거 인용 답변
  diagnose → { diagnosis:{ pass, forbidden[], risky[], suggestion, replacements[] } }
GET  /api/chatbot  → { kb 통계, llm 연동여부, modes }
```
LLM 자연어 답변 활성화: 환경변수 `OPENAI_API_KEY` 설정(미설정 시 근거 요약 폴백).

### 로컬 검증
```bash
node pipeline/test-api.js     # 핸들러 오프라인 스모크 테스트(6/6)
```

## 재사용 자산 (VENOM 기존 코드)

- `../lib/medical-ad-validator.js` — 금지표현 검증기·자동 대체(자가진단 룰엔진에 통합)
- `../lib/openai-client.js` — LLM 호출 클라이언트
- `../api/store.js`, KV(Upstash) — 세션·로그 저장 패턴
