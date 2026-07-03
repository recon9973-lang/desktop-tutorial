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
- ⬜ Phase 2 — 조문 전문(law.go.kr)·협회 심의기준·FAQ 보강, 임베딩(`embed.js`) 부착
- ⬜ Phase 3 — 챗봇 API(`preview/api/chatbot.js`) + RAG 응답(근거 인용)
- ⬜ Phase 4 — 웹 위젯 + 문구 자가진단 UI, 평가 루프(10,000 질문)

## 재사용 자산 (VENOM 기존 코드)

- `../lib/medical-ad-validator.js` — 금지표현 검증기·자동 대체(자가진단 룰엔진에 통합)
- `../lib/openai-client.js` — LLM 호출 클라이언트
- `../api/store.js`, KV(Upstash) — 세션·로그 저장 패턴
