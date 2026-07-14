# GEO 운영 OS — 채널별 실행 플레이북 (업무 템플릿 사양)

> 상위: [`geo-ops-os-design.md`](./geo-ops-os-design.md) · 작성일: 2026-07-14
> 목적: 첨부1(실무 실행 가이드)의 채널별 단계를 **업무 템플릿(checklist-template)**으로 구조화한다. 각 단계는 **자동화 레벨(A/B/C/D)**을 달아, 시스템이 "직접 실행"할지 "안내만" 할지 명확히 한다.
> 원천 데이터: 이 문서가 `content/geo/checklist-templates.json`을 채운다(코드 아닌 데이터로 관리, 설계서 §0-4).
> **불변 규칙**: 채널의 `defaultAutomationLevel` 상한을 초과하는 단계는 만들지 않는다(예: Wikipedia/Reddit 게시는 D=안내만, 자동 실행 원천 차단).

**레벨 범례** — 🟢A 시스템 직접실행 · 🟡B 초안+예약→인간 승인 · 🔵C 초안만→인간 게시 · 🔴D 안내(체크리스트·증빙)만

---

## 1. Wikipedia (channelType `wikipedia` · 상한 C초안/D게시)
ChatGPT 인용 최상위군. **계정 리스크 최고 → 자동 게시 절대 금지.**

| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | 계정 신뢰도(4주 타항목 편집·자동인증 자격) | 🔴 D | 체크리스트·진행일수 카운터만 | 편집 횟수 스크린샷 |
| 2 | 주목성 충족 확인(독립 언론 2건+) | 🔵 C | 언론 기사 자동 수집(Google News RSS→목록) | 출처 URL 목록 |
| 3 | COI(이해충돌) 공개 선언 | 🔴 D | 문구 템플릿 안내 | 사용자토론 페이지 링크 |
| 4 | 초안 작성(NPOV·각주·홍보표현 금지) | 🔵 C | LLM 초안 생성(중립성 가이드 프롬프트) | 샌드박스 링크 |
| 5 | 실제 항목 생성·게시 | 🔴 D | **금지 — 안내만**(사람이 직접) | 게시 diff URL |
| 6 | 월 1회 유지관리 | 🔴 D | 변경 감시(Wikipedia API)→Slack 알림 | 갱신 이력 |

**금지선**: 자동 편집/게시, 홍보성 표현 자동삽입. **KPI**: 항목 생성 여부, 편집 유지율(추세).

---

## 2. Reddit (channelType `reddit` · 상한 C초안/D게시)
Perplexity 인용 1위군. **봇 탐지 → 자동 게시 시 영구정지.**

| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | Karma 육성(4~8주, 전문 댓글) | 🔴 D | Karma 목표 트래커만 | 프로필 karma |
| 2 | 타깃 서브레딧 선정 | 🟢 A | 업종 키워드로 서브레딧 후보 수집 | 서브레딧 목록 |
| 3 | **답변 기회 탐지**(브랜드/키워드 신규글) | 🟢 A | Reddit API 모니터링→Slack 알림 | 알림 로그 |
| 4 | 전문가 답변 초안(공감→해결책→자사 1회) | 🔵 C | LLM 초안 생성(개인화 필수 경고) | 초안 |
| 5 | 실제 게시 | 🔴 D | **금지 — 안내만**(사람이 직접 입력) | 댓글 URL |
| 6 | AMA 기획 | 🔴 D | 절차 체크리스트 | 승인 메시지 |

**금지선**: 자동 게시, 업보트 조작, cross-posting. **KPI**: 답변 수·업보트(수동 기록), Perplexity 인용 여부(실측 연동).

---

## 3. LinkedIn (channelType `linkedin` · 상한 B)
| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | 프로필·기업페이지 최적화(1회) | 🟡 B | 소개문·Specialties 초안 | 완성 스크린샷 |
| 2 | Post 주3~5회(트렌드·데이터·스토리 로테이션) | 🟡 B | 초안 3편 생성→Buffer 예약(승인 후) | 게시 URL |
| 3 | Article 월2~4회(BLUF·H2질문·데이터·800단어+) | 🟡 B | Perplexity 데이터+Claude Article 초안 | 게시 URL |
| 4 | 발행 후 즉시 Post 공유·그룹 공유 | 🔵 C | 요약 댓글 초안 | — |

**금지선**: 자사홍보 편중(교육 80/홍보 20 규칙). **KPI**: 팔로워·Article 조회(LinkedIn Analytics API).

---

## 4. YouTube (channelType `youtube` · 상한 B / 자막 A)
| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | 채널 개설·키워드 설정 | 🔴 D | 체크리스트 | 채널 URL |
| 2 | 스크립트(BLUF·소주제·수치) | 🔵 C | LLM 초안 | 스크립트 |
| 3 | **자막 SRT 생성**(Whisper, 오류율↓) | 🟢 A | 음성→Whisper→SRT→전문용어 치환 | SRT 파일 |
| 4 | 제목/설명/태그 SEO | 🟡 B | 제목5변형+설명+태그 초안 | 업로드 메타 |
| 5 | 업로드·자막 첨부·첫48h 관리 | 🔵 C | 공개 후 배포 링크 초안 | 영상 URL |

**금지선**: 자동 자막 방치(오인용). **KPI**: 조회수·구독자(YouTube Analytics API).

---

## 5. GitHub (channelType `github` · 상한 B) · Stack Overflow (`stackoverflow` · 상한 C)
| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| G1 | 조직·저장소·README(구조화) | 🟡 B | README 초안·자동갱신 PR(기존 GrowthOps) | PR URL |
| G2 | GitHub Pages 문서 사이트 | 🟡 B | docs 마크다운 초안 | 사이트 URL |
| S1 | 평판 쌓기·전문답변(코드검증) | 🔵 C | 답변 초안(코드 로컬검증 경고) | 답변 URL |

**금지선**: SO는 AI 무편집 답변 게시 정책 위반 → C 상한. **KPI**: Star 수, SO 평판(수동).

---

## 6. arXiv / 학술 (channelType `arxiv` · 상한 D)
| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | Endorsement 확보 | 🔴 D | 안내만 | 이메일 |
| 2 | LaTeX 리포트(초록·방법·결과) | 🔵 C | 형식 교정·참고문헌 통일 보조 | .tex |
| 3 | 제출 | 🔴 D | **금지 — 인간필수**(학술윤리) | 제출 ID |

**금지선**: AI 생성 논문 전체 제출(계정 정지). **대안**: 추천인 없으면 ResearchGate/SSRN 안내.

---

## 7. PR / 보도자료 (channelType `pr_global`·`pr_kr` · 상한 B초안/D배포)
| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | AP스타일 초안(헤드라인·5W1H 리드·수치 서두) | 🟡 B | Claude 초안 | 초안 |
| 2 | CEO 인용문·수치 검증 | 🔴 D | **인간 확인**(법적 책임) | 승인 기록 |
| 3 | 배포(지역·시간·카테고리) | 🔴 D | 안내만(사람이 제출) | 배포 확인 |
| 4 | 배포 후 미디어 모니터링 | 🟢 A | Google Alerts RSS→픽업 감지→알림 | 픽업 목록 |

**금지선**: 허위수치·주관적 최상급 자동생성. **KPI**: 미디어 픽업·백링크 수.

---

## 8. Google SEO·Gemini·기술위생 (channelType `gsc`·`schema`·`llms_txt` · 상한 A)
| # | 단계 | 레벨 | 시스템 동작 | 증빙 |
|---|---|---|---|---|
| 1 | GSC 등록·sitemap 제출 | 🔴 D→🟢 A | 등록 안내→이후 색인상태 자동수집 | GSC 스크린샷 |
| 2 | 색인 요청 | 🟡 B | sitemap+GSC 제출 흐름(**Indexing API 미사용**) | 색인 상태 |
| 3 | FAQPage/Article Schema | 🟢 A | 자동 삽입·GitHub Actions 검증 | validator 결과 |
| 4 | llms.txt 유지 | 🟢 A | sitemap 파싱→자동 갱신·커밋 | 파일 diff |

**주의(정직성)**: Schema·llms.txt는 **위생 항목**으로만 — "인용 2~3배/리프트" 약속 금지(리서치 반증). **KPI**: 색인 페이지수·클릭·노출·순위(GSC API).

---

## 9. 한국 UGC (channelType `naver_blog`·`naver_cafe`·`naver_kin`·`naver_brunch`·`naver_place`)
첨부4 핵심: **Naver AI Tab/Briefing은 카페·블로그·지식iN에서 답변 생성** → 글로벌 채널과 소스풀이 다름. 별도 트랙.

| channelType | 단계 | 레벨 | 시스템 동작 |
|---|---|---|---|
| `naver_blog` | 전문 롱폼·키워드·정기 | 🟡 B | 초안+발행 안내 |
| `naver_cafe` | 커뮤니티 전문 답변 | 🔵 C | 초안만, 인간 게시 |
| `naver_kin`(지식인) | 전문가 답변·출처명시 | 🔵 C | 초안만, 인간 게시 |
| `naver_brunch` | 심층 아티클 | 🟡 B | 초안+발행 안내 |
| `naver_place` | 지역정보 정합성·리뷰 | 🟡 B | 정보 점검 체크리스트 |

**모니터링**: Naver Search/DataLab Open API(이 세션 MCP 연결)로 SERP 순위·트렌드 우회 수집. Search Advisor 성과지표는 수동 보완.

---

## 10. 채널→AI 매핑 요약 (첨부1·4 통합)
| 채널 | ChatGPT | Gemini | Claude | Perplexity | Naver AI |
|---|---|---|---|---|---|
| Wikipedia | ★필수 | 중 | 상 | 미인용 | — |
| Reddit | 상 | 하 | 중 | ★1위 | — |
| LinkedIn | 중 | 중 | 하 | 중 | — |
| YouTube | 하 | ★상 | 하 | ★2위 | — |
| GitHub/SO | 중 | 하 | ★상 | 상(기술) | — |
| arXiv | 상 | 상 | ★필수 | 학술모드 | — |
| PR/언론 | ★상 | ★상 | 중 | 상 | — |
| GSC/SEO | (Bing) | ★=검색순위 | Web도구 | 상 | — |
| Naver 카페/블로그/지식인 | 추정 | — | — | 크롤링 | ★필수 |

> 이 매핑은 **채널 우선순위 힌트**일 뿐 인용 확률 보장 아님(리서치: 점유율 수치는 주 단위 붕괴). 실제 판단은 거래처별 실측(SOV 추세)으로.

---

*이 문서의 각 표는 `content/geo/checklist-templates.json`의 1 템플릿에 대응한다. 구현 시 이 JSON을 시드로 로드하고, 거래처 온보딩에서 업종 프리셋(설계서 §12 업종별)에 따라 필요한 템플릿만 Task로 인스턴스화한다.*
