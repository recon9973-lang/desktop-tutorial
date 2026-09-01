# 춘천 그랜드연합의원 — 홈페이지 구조 검토 및 제안 (SEO · GEO · AEO)

> 실측일 2026-09-01. 모든 수치는 외부에서 실제 요청해 받은 응답 기준이며, 출처가 검색엔진 색인인 항목은 그렇게 표기했다.
> 용어: 이 문서에서 **GEO**는 두 축으로 나눠 다룬다 — ① 생성형 엔진 최적화(Generative Engine Optimization), ② 지역(Local/지도·플레이스). 병원은 둘 다 필수라 분리해 적었다.

---

## 0. 한 줄 결론

구조 자체(과별 분리)는 틀리지 않았다. **문제는 구조가 아니라 ① grand1의 크롤 가능성 붕괴, ② 피부과 콘텐츠의 이중 존재, ③ 네이버 플레이스 링크 전량 오연결** 세 가지다. 도메인을 합치는 일보다 이 셋을 먼저 처리해야 하고, 셋 다 처리 난이도는 낮다.

---

## 1. 현재 구조 지도 (실측)

### grand1.co.kr — 서버 183.111.182.209 (nginx), 그누보드 계열
| 경로 | 실제 주체 | 상호 | 층 |
|---|---|---|---|
| `/` | 통합 랜딩 | 그랜드메디컬타워(4개 과 안내) | — |
| `/orthopedics/` | 정형외과 | 그랜드연합의원 | 5F |
| `/ophthalmology/` | 안과 | 그랜드우리안과의원 | 2F |
| `/pediatrics/` | **내과** | 그랜드배내과의원 | 3F |
| `/skin/` | **피부과 (구 사이트, 현재도 가동·색인 중)** | 그랜드아름다운의원 | 4F |

- 하위 페이지 패턴: `/{과}/content/{slug}`, 게시판 `/{과}/core/board.php?bo_table=notice&wr_id=84`
- 루트 title = `그랜드 연합의원, 춘천피부과, 춘천정형외과, 춘천내과, 춘천안과` — **`/skin/`의 title이 이와 완전히 동일**(네이버 색인 기준)

### grand4.co.kr — 서버 211.251.237.177, 브레인메디(brainmedi.co.kr) 임대형 솔루션
- `www.grand4.co.kr` (PC) + `m.grand4.co.kr` (모바일) 분리형, 모바일 UA는 m으로 자동 전환
- 콘텐츠: 병원소개 / 의료진 / 오시는길 / 둘러보기 / 시술안내 / 이달의 혜택 / 상담예약 / 장비소개 / 비급여
- sitemap.xml 등재 URL **35개**

### 법인 구조상의 사실
네이버 플레이스에는 **한 건물에 4개의 독립 업체**로 등록돼 있다 — 그랜드연합의원(정형외과·5F), 그랜드우리안과의원(2F), 그랜드배내과의원(3F), 그랜드아름다운의원(피부과·4F). 즉 "한 병원의 4개 과"가 아니라 **상호가 각기 다른 4개 의료기관이 한 타워에 모인 형태**다. 이 사실이 구조 판단의 전제다.

---

## 2. 치명적 이슈 (P0) — 순서대로 이것부터

### P0-1. grand1.co.kr에 HTTPS가 없다 (확정)
443 포트의 인증서가 **자체서명(self-signed)**이다.

```
subject = C=GB, ST=Berkshire, L=Newbury, O=My Company Ltd
issuer  = (동일, 자체서명)
notBefore = 2017-04-13   notAfter = 2117-03-20
```

`O=My Company Ltd`는 OpenSSL 기본 예시값이다. 즉 **인증서를 발급받은 적이 없다.** 브라우저는 경고 페이지를 띄우고, 실제 사이트 링크는 전부 `http://`로 유통된다. 온라인 상담·예약 폼에서 환자 개인정보를 평문으로 받고 있다는 뜻이기도 하다. 사내 진단 기준에서 HTTPS는 기술·크롤링 30점 중 6점 항목이며, 신뢰 문제는 점수보다 크다.

### P0-2. grand1이 크롤러에게 내용을 안 준다 (개연성 높음 — GSC로 확정 필요)
실측:

| 요청 | 응답 |
|---|---|
| 일반 브라우저 UA로 `http://grand1.co.kr/` | 200, **759바이트** — 본문 없음, JS 봇 차단 챌린지 페이지 |
| 챌린지가 부르는 `/cupid.js` | **404 Not Found** |
| `/robots.txt`, `/sitemap.xml` | 동일한 챌린지 페이지 (규칙 파일을 읽을 수 없음) |
| Googlebot UA · Yeti UA | **403** |
| 구글 검색 색인 | 제목 `Grand1`, **설명 없음** |
| 네이버 검색 색인 | 정상 — 과별 페이지 다수, 제목·본문 요약 모두 정상 |

읽는 법: 차단은 IP/UA 조건부로 보인다. 네이버(Yeti)는 실제로 잘 긁고 있고, 구글은 색인은 있으나 내용이 비어 있다. 봇 UA에 403을 주는 건 위장 봇 차단 로직이 정상 IP 검증에 실패했을 때의 전형적 반응이라 **진짜 Googlebot은 통과할 수도 있다.** 다만 확실한 것 세 가지는 남는다.

1. `/cupid.js`가 404라 **챌린지는 어떤 클라이언트도 통과할 수 없다** — 이 경로로 들어온 방문자·크롤러는 무한 루프다.
2. **robots.txt와 sitemap.xml을 읽을 수 없다.** 크롤 규칙과 URL 목록을 검색엔진에 못 주고 있다.
3. 구글 결과의 제목/설명 부재는 "콘텐츠를 못 받았다"는 증상과 일치한다.

> 진단 도구로 grand1을 채점하려 해도 원본 HTML을 못 받아 **측정 자체가 불가능**하다. 크롤러도 같은 조건이다. 이게 이 사이트의 상태를 가장 잘 요약한다.
> **확정 방법**: Google Search Console → 설정 → 크롤링 통계 / URL 검사의 "실제 URL 테스트". 네이버 서치어드바이저 → 수집 진단. 두 콘솔에 도메인을 등록하면 추측 없이 끝난다.

### P0-3. 피부과가 두 도메인에 동시에 살아 있다 (확정)
`grand1.co.kr/skin/`의 구 피부과 사이트가 **폐쇄되지 않았고, 지금도 색인돼 있다.** 네이버 웹문서에서 확인된 것만:

- `/skin/content/beauty_filler` (턱끝필러), `/skin/content/beauty_botox` (보톡스)
- `/skin/content/introduce` (병원소개), `/skin/content/obesity_hpl`
- `/skin/core/board.php?bo_table=new_event&sca=보톡스/윤곽주사` (시술＆가격)
- `/skin/core/board.php?bo_table=counsel&page=2` (온라인상담 — 환자 문의가 계속 쌓이는 중)
- `/skin/content/index.php?co_id=price&device=mobile` (가격, 모바일 파라미터판)

문제의 크기: "춘천피부과 … 필러 보톡스"로 검색했을 때 **상위에 뜨는 건 신규 grand4가 아니라 구 사이트 `grand1.co.kr/skin/`이다.** 같은 병원의 같은 시술 페이지가 두 벌 존재하니 링크·클릭·인용이 갈리고, 오래된 쪽이 이긴다. 게다가 구 사이트 상담 게시판이 살아 있어 **환자가 아무도 안 보는 창구에 글을 남기고 있을 가능성**이 있다.

### P0-4. 네이버 플레이스 4곳의 홈페이지 링크가 전부 틀렸다 (확정)
| 플레이스 | 등록된 링크 | 맞는 링크 |
|---|---|---|
| 그랜드연합의원(정형외과) | `http://grand1.co.kr/` | `/orthopedics/` |
| 그랜드배내과의원(내과) | `http://grand1.co.kr/` | `/pediatrics/` |
| 그랜드우리안과의원(안과) | `blog.naver.com/grandwoorieyesclnic` | `/ophthalmology/` (블로그는 별도 필드) |
| 그랜드아름다운의원(피부과) | `http://www.grand1.co.kr/` | **`https://www.grand4.co.kr/`** |

지역 검색에서 가장 강한 신호원(플레이스)이 넷 다 잘못된 목적지를 가리킨다. 특히 피부과는 **새로 만든 사이트로 향하는 신호가 0**이고, 대신 폐기했어야 할 구 사이트에 신호를 몰아주고 있다. P0-3과 겹쳐 최악의 조합이다. 이건 관리자 페이지에서 30분이면 고친다.

---

## 3. 구조·기술 검토 (SEO)

### 3-1. URL 체계 — 일관성이 없다
```
/orthopedics/   정형외과   ← 의학 용어
/ophthalmology/ 안과       ← 의학 용어
/pediatrics/    내과       ← 소아청소년과를 뜻하는 단어인데 내과가 들어있다 (의미 충돌)
/skin/          피부과     ← 일반 명사
grand4.co.kr    피부과     ← 별도 도메인
```
`/pediatrics/`(소아과)에 그랜드**배내과**가 들어 있는 건 사람에게도 크롤러에게도 오해를 만든다. 다만 URL 단어가 순위에 미치는 영향은 크지 않으므로(사내 가이드도 동일 입장), **급하지 않되 개편 시 반드시 함께 정리**할 항목이다.

### 3-2. 중복 URL
- grand1: `www` / non-www 둘 다 200, 정규화 여부 확인 불가(챌린지). 네이버 색인에 두 형태가 섞여 있다.
- grand1: 구 피부과의 `?device=mobile` 파라미터 URL이 별도 색인됨.
- grand4: `/` 와 `/index.php` 가 각각 구글에 색인. 다만 `/index.php`의 canonical이 `https://www.grand4.co.kr`로 지정돼 있어 **처리는 정상**.
- grand4의 PC/모바일 분리(m-dot)는 `rel=alternate`(PC→m) + `canonical`(m→PC)이 **정상 페어링**돼 있다. 낡은 방식이지만 구현은 규격대로다. 즉시 손댈 필요는 없고, 솔루션 교체 시 반응형으로 가면 된다.

### 3-3. grand4 페이지별 메타 — 전 페이지가 똑같다 (9개 페이지 실측)
| 페이지 | title | meta description | canonical | H1 |
|---|---|---|---|---|
| `/` | 그랜드아름다운의원 | 춘천 피부과 그랜드… | 자기 URL | **비어 있음** |
| `/about/about.php` | 〃 (동일) | 〃 (동일) | 자기 URL | **비어 있음** |
| `/about/doctor.php` | 〃 | 〃 | 자기 URL | **비어 있음** |
| `/about/map.php` | 〃 | 〃 | 자기 URL | **비어 있음** |
| `/about/device.php` | 〃 | 〃 | 자기 URL | **비어 있음** |
| `/board/noticeThum.php` | 〃 | 〃 | 자기 URL | **비어 있음** |
| `/clinicPrice/eventListLeft.php` | 〃 | 〃 | 자기 URL | **비어 있음** |
| `/clinicPrice/clinicView.php?i=9461` | 〃 | 〃 | 자기 URL | **비어 있음** |
| `/about/uninsured.php` | 〃 | 〃 | 자기 URL | **비어 있음** |

canonical은 잘 돼 있다. 그런데 **title·description이 9개 페이지 전부 동일**하고 **H1은 태그만 있고 내용이 없다**. 검색결과에서 "의료진 소개"와 "오시는길"과 "비급여 안내"가 전부 같은 제목·같은 설명으로 뜬다는 뜻이다. 클릭률과 페이지별 주제 인식이 동시에 무너진다. 사내 기준에서 title 8점 + description 8점 + H1 6점 = **22점이 걸린 자리**다.

### 3-4. grand4 기타 실측
| 항목 | 실측 | 판정 |
|---|---|---|
| HTTPS | 적용, apex→www 301 | ✅ |
| robots.txt | 존재, Sitemap 선언, AI 크롤러 다수 명시 허용 | ✅ (아래 4-2 참조) |
| sitemap.xml | 35 URL. **시술 상세(`clinicView.php?i=…`) 전량 누락** | ⚠️ |
| lang / favicon / OG | `lang="ko"`, 파비콘 O, og:title·description O | ✅ |
| 구조화 데이터 | JSON-LD **1개, `@type: Organization`** | ⚠️ 아래 4-3 |
| viewport | PC판 **없음**, 모바일판 있음 | ⚠️ |
| 이미지 | 메인 59장 중 alt 있는 것 41장 (**약 30% 누락**) | ⚠️ |
| 본문 텍스트량 | 메인 약 2,520자 — 그중 상당량이 네비게이션 중복 | ⚠️ |
| 시술 상세 URL | `clinicView.php?i=9461&cate=1989&word=&sort=0` (빈 파라미터 포함) | ⚠️ |
| 분석 도구 | GA 계열 설치됨, 네이버 애널리틱스 없음 | ⚠️ |
| 비급여 고지 | `/about/uninsured.php` 존재 (의료법 제45조 근거 명시) | ✅ |

**핵심 약점은 "글이 이미지 안에 있다"**는 점이다. 메인의 카피("110평 규모·총 60대 레이저", 장비 설명 등)는 텍스트로 잡히지만, 시술 상세 페이지들은 이미지 중심일 가능성이 크고 alt 누락 30%가 이를 뒷받침한다. 검색엔진도 AI도 이미지 안의 글자는 근거로 쓰지 못한다.

### 3-5. 사내 진단 기준(90점 만점) 대비 개략
- **grand4**: 약 70점대 초중반 추정 — 기술 항목은 대부분 통과, **콘텐츠·메타(38점)에서 대량 실점**(title/description 중복, H1 공란, alt 누락, 파라미터 URL).
- **grand1**: **측정 불가**. 원본 HTML을 받을 수 없다.
- 정본 점수는 진단센터 도구로 실측 권장(위 수치는 수동 파싱 기반 추정치).

---

## 4. GEO ① 생성형 엔진 최적화 · AEO

### 4-1. 지금 AI는 이 병원을 어디서 배우고 있나
"춘천 피부과", "춘천 정형외과 도수치료"를 실제로 검색해 본 결과, 상위를 점유한 건 병원 자체 사이트가 아니라 **모두닥·굿닥·똑닥·나우닥·캐시닥 같은 의료 플랫폼**이었다. 그랜드 4개 원 모두 이 플랫폼들에 등록돼 있다. 즉 **AI 답변 엔진이 "춘천 그랜드연합의원"을 설명할 때 인용하는 1차 소스는 병원 홈페이지가 아니라 이 플랫폼들**이다.

실제로 플랫폼마다 진료과 표기가 제각각이다 — 굿닥 `61985`는 내과·정형외과·마취통증의학과·소아청소년과·안과·이비인후과·피부과, 굿닥 `61986`은 여기에 신경외과·성형외과·가정의학과까지, 똑닥은 정형외과 단일, 주소도 "3층" / "4~6층"으로 갈린다. **AI가 이 병원을 잘못 설명한다면 원인은 여기다.**

### 4-2. 크롤러 접근 — 두 도메인이 정반대다
grand4의 robots.txt는 오히려 모범적이다. GPTBot · OAI-SearchBot · SearchGPT · ChatGPT-User · ClaudeBot · Google-Extended · Applebot · PerplexityBot · Grok · Qwen까지 명시적으로 `Allow`하고, 저품질 크롤러는 차단한다. 실제로 Googlebot·GPTBot UA로 요청해도 정상 응답(78KB)을 준다. **AEO 관점에서 grand4는 문을 열어둔 상태다.**

반대로 grand1은 robots.txt 자체를 읽을 수 없고 일반 요청에도 759바이트 챌린지만 준다. **AI 엔진에 정형외과·안과·내과는 사실상 존재하지 않는 사이트다.** 결과적으로 4개 과 중 피부과 하나만 AI가 읽을 수 있다.

### 4-3. 구조화 데이터가 병원 정보를 담고 있지 않다
grand4의 JSON-LD 전문:
```json
{ "@context":"http://schema.org", "@type":"Organization",
  "name":"그랜드아름다운의원",
  "description":"춘천 피부과 그랜드아름다운의원, 필러, 보톡스, …",
  "url":"https://www.grand4.co.kr",
  "address":{ "@type":"PostalAddress", "addressCountry":"KR" },
  "sameAs":[ ] }
```
- `@type`이 `Organization` — 의료기관이면 `MedicalClinic`(또는 `MedicalBusiness`)이어야 한다.
- `address`에 **국가만 있고 주소가 없다.** 정작 `/about/map.php`에는 "강원특별자치도 춘천시 중앙로 68 4층"이 텍스트로 잘 적혀 있다. 있는 정보를 구조화하지 않았을 뿐이다.
- `telephone`(1899-5109), `openingHoursSpecification`(평일 10:00–20:00 / 토 09:00–15:00 / 일·공휴일 휴무 / 점심 13:00–14:00), `geo`, `medicalSpecialty` 전부 없음.
- `sameAs`가 **빈 배열** — 네이버 플레이스도, 운영 중인 블로그(`blog.naver.com/kikfjifimv`)도 연결 안 됨.
- 의료진 3명(신정은·김희성·박하훈 원장)의 학력·학회 이력이 `/about/doctor.php`에 텍스트로 있는데 `Physician` 스키마가 없다. **E-E-A-T 근거를 그냥 버리고 있다.**

### 4-4. 질문형 콘텐츠가 없다
"춘천에서 백내장 수술 어디서 하나", "그랜드연합의원 주차 되나", "토요일 진료하나", "도수치료 가격" — AI가 답할 때 필요한 형태(질문 → 짧은 직답 → 근거)의 블록이 어느 사이트에도 없다. 진료시간·주차 정보는 문장으로는 있지만 `FAQPage` 구조가 아니다. 비급여 페이지(`/about/uninsured.php`)는 법정 고지물이지만 **동시에 최고의 AEO 자산**이다 — 가격 질문에 답할 수 있는 유일한 1차 근거인데 지금은 구조화도, sitemap 등재도 안 돼 있다.

---

## 5. GEO ② 지역 검색 (Local)

- **플레이스 링크 오연결** — 2장 P0-4. 최우선.
- **NAP 불일치** — 플랫폼별 층수·진료과 표기가 제각각(4-1). 4개 원의 상호·주소(층 포함)·대표번호를 한 표로 확정하고 전 채널에 동일하게 배포해야 한다.
- **대표번호 공유의 부작용** — `1899-5109`를 여러 원이 함께 쓴다. 지역 검색은 전화번호를 업체 식별자로 쓰므로, 가능하면 원별 직통번호를 병기하는 편이 유리하다.
- **블로그 자산의 단절** — 안과(`grandwoorieyesclnic`)·피부과(`kikfjifimv`) 네이버 블로그가 운영 중인데 사이트와 `sameAs`로 묶여 있지 않다. 안과는 플레이스 홈페이지 칸에 블로그가 들어가 있어 **사이트가 아예 없는 것처럼 보인다.**
- **경쟁 상황** — 춘천 지역에서 이미 자체 도메인으로 상위에 올라온 병원들이 있다(예: 정형외과 `seulgilounos.com`, 피부과 `bbeauty365clinic.co.kr`). 자체 사이트로 이기는 게 불가능한 시장이 아니라는 뜻이다.

---

## 6. 구조 제안

### 6-1. 도메인을 합쳐야 하나? — 아니다, 급하지 않다
"피부과만 별도 도메인"이 손해라는 통념이 있지만, 구글 공식 입장은 **서브도메인·서브디렉터리·별도 도메인의 순위 차이는 미미**하다는 것이고, 사내 진단 기준도 이 항목을 감점하지 않는다. 게다가

- 4개 원은 **법적으로 별개 의료기관**이다 (상호·대표자가 다름). 도메인 분리에 명분이 있다.
- grand4는 임대형 솔루션이라 통합 이전 비용이 크다.

따라서 **도메인 통합은 권고하지 않는다.** 지켜야 할 원칙은 하나뿐이다.

> **한 진료과 = 정본 URL 하나.** 지금 위반된 건 피부과뿐이다(`grand1/skin` + `grand4`). 그것만 정리하면 현재 구조는 유효하다.

### 6-2. 권고안 — 「타워 허브 + 과별 정본」
```
grand1.co.kr/                  ← 그랜드메디컬타워 허브 (건물·공통 안내·과별 진입)
  ├ /orthopedics/              ← 그랜드연합의원 (정형외과) 정본
  ├ /ophthalmology/            ← 그랜드우리안과의원 정본
  ├ /internal-medicine/        ← 그랜드배내과의원 정본  (구 /pediatrics/ 에서 301)
  └ /skin/*  ──301──▶  grand4.co.kr 대응 페이지   ← 구 사이트 폐기

grand4.co.kr                   ← 그랜드아름다운의원 (피부과) 정본, 그대로 유지
```
결속 방법 (도메인이 갈려도 하나의 엔티티로 인식시키는 장치):
- 허브 ↔ 각 과 **양방향 링크**를 헤더/푸터에 고정 (grand4 → 타워 허브 링크 포함)
- 각 과 JSON-LD에 `parentOrganization`(그랜드메디컬타워) + `sameAs`(플레이스·블로그·플랫폼 프로필)
- 허브에 `MedicalOrganization` + `department[]`로 4개 원을 명시
- 공통 NAP 블록(주소·층·전화·진료시간)을 4개 사이트에서 **동일 문자열**로 노출

### 6-3. `/skin/` 폐기 절차 (되돌릴 수 없으니 순서대로)
1. `/skin/` 하위 색인 URL 전수 수집 (네이버 서치어드바이저 + GSC + 사이트 내부 목록)
2. 시술 페이지는 grand4의 대응 페이지로 **1:1 301** (예: `/skin/content/beauty_botox` → grand4 보톡스 페이지). 대응이 없으면 grand4 시술 목록으로.
3. 상담 게시판(`bo_table=counsel`)은 **먼저 미답변 문의를 확인·처리**한 뒤 닫는다. (환자 민원 리스크)
4. 1:1 매핑이 불가능하면 최소한 `/skin/` → `https://www.grand4.co.kr/` 301 + 개별 페이지 `noindex`
5. 301 후 두 콘솔에서 색인 이전 추적 (보통 2~8주)

---

## 7. 실행 로드맵

### P0 — 0~2주 (비용 거의 0, 효과 최대)
| # | 작업 | 담당 | 확인 방법 |
|---|---|---|---|
| 1 | grand1 **HTTPS 인증서 발급**(Let's Encrypt 무료 가능) + `http→https` 301 + www 단일화 | 서버 | 브라우저 자물쇠, 리다이렉트 체인 1회 |
| 2 | grand1 **봇 차단 정책 수정** — 깨진 `/cupid.js`(404) 복구 또는 챌린지 해제, `robots.txt`·`sitemap.xml`은 무조건 예외, 검색·AI 크롤러 화이트리스트 | 서버/보안 | 크롤러 UA 응답이 실제 HTML인지 |
| 3 | **GSC · 네이버 서치어드바이저 등록** (4개 사이트 전부) | 마케팅 | 크롤링 통계·수집 진단으로 P0-2 확정 |
| 4 | **네이버 플레이스 4곳 홈페이지 링크 교정** (특히 피부과 → grand4) | 마케팅 | 플레이스 화면 |
| 5 | grand1 `robots.txt` + `sitemap.xml` 신규 작성 (과별 전 URL) | 웹 | 서치어드바이저 제출 |
| 6 | `/skin/` 상담 게시판 미답변 확인 | 병원 | — |

### P1 — 2~8주
| # | 작업 | 효과 |
|---|---|---|
| 7 | `/skin/` → grand4 **301 이전 및 폐기** (6-3 절차) | 피부과 카니발라이제이션 종료 |
| 8 | grand4 **페이지별 title/description** 부여 (관리자에서 불가하면 브레인메디에 기능 요청) | 사내 기준 16점 + CTR |
| 9 | grand4 **H1 채우기** — "그랜드아름다운의원 의료진", "춘천 피부과 오시는 길" 등 | 6점 + 주제 인식 |
| 10 | **스키마 전면 교체**: `MedicalClinic` + `address`(전체) + `geo` + `telephone` + `openingHoursSpecification` + `medicalSpecialty` + `sameAs`(플레이스·블로그) | AI 인용 정확도 |
| 11 | `/about/doctor.php`에 **`Physician` 스키마** (3인 학력·학회) | E-E-A-T |
| 12 | 이미지 속 카피를 **HTML 텍스트로 병기**, alt 100% | 색인·AEO·접근성 |
| 13 | sitemap에 **시술 상세 전량 추가**, `clinicView` 빈 파라미터(`word=&sort=`) 제거 | 색인 커버리지 |
| 14 | `/pediatrics/` → `/internal-medicine/` 301 (다른 개편과 함께) | 의미 정합 |
| 15 | 네이버 애널리틱스 설치 | 유입 측정 |

### P2 — 분기 단위
| # | 작업 |
|---|---|
| 16 | **과별 Q&A 페이지 + `FAQPage` 스키마** — "춘천 백내장 수술", "도수치료 가격", "토요일 진료", "주차" 등 실제 질문 기반 |
| 17 | **비급여 페이지를 AEO 자산으로 승격** — 표를 HTML 테이블로, sitemap 등재, 가격 질문 대응 |
| 18 | **의료 플랫폼 정보 정합화** — 모두닥·굿닥·똑닥·나우닥의 진료과·층수·진료시간을 4개 원 기준으로 통일 (AI 인용 소스 교정) |
| 19 | 과별 블로그 ↔ 사이트 상호 연결, `sameAs` 등록 |
| 20 | grand4 임대형 솔루션의 구조적 한계(페이지별 메타 제약·m-dot·이미지 중심) 재평가 → 반응형 자체 사이트 전환 검토 |

---

## 8. 측정 계획
- **1차 데이터**: Google Search Console(크롤링 통계·색인 커버리지·검색 실적), 네이버 서치어드바이저(수집·색인 진단). 4개 사이트 전부 등록.
- **P0-2 확정 지표**: GSC 크롤링 통계의 응답 코드 분포 — 403/타임아웃 비중.
- **P0-3 확정 지표**: `site:grand1.co.kr/skin` 색인 수의 감소 곡선, grand4 색인 수 증가.
- **AEO 지표**: 주요 질문("춘천 피부과 추천", "그랜드연합의원 진료시간" 등)에 대한 AI 답변에서의 인용 여부·인용 소스.
- 순위는 보장 대상이 아니다. 위 지표는 **크롤·색인·인용이 되는가**를 본다.

---

## 9. 부수 리스크 (마케팅 실행 시 확인 필요)
- grand4의 시술·가격 노출("1DAY잡티올킬 레이저 199,000원" 등 이벤트 가격)과 표현 일부는 **의료광고 사전심의 대상** 여부를 확인해야 한다.
- 카피 중 최상급·효과 보장으로 읽힐 수 있는 표현은 사전 점검 권장.
- grand1의 온라인 상담 폼이 HTTPS 없이 개인정보를 수집 중이라면 **개인정보 처리 관점에서도 P0-1은 즉시 처리 사안**이다.

---

## 부록 A. 실측 방법
- 외부 샌드박스에서 각 호스트에 직접 HTTP 요청(브라우저 UA / Googlebot UA / Yeti UA / GPTBot UA / ClaudeBot UA), 응답 코드·바이트·본문 파싱
- TLS 인증서는 `openssl s_client`로 주체·발급자·유효기간 확인
- 색인 상태는 네이버 검색(웹문서·지역)과 구글 검색 결과로 확인
- grand1은 봇 차단 챌린지로 본문을 받을 수 없어 **우회하지 않았고**, 구조는 검색엔진 색인에 남은 URL·제목·요약으로 재구성했다

## 부록 B. 확인된 grand1 URL (색인 기준)
```
http://www.grand1.co.kr/
http://www.grand1.co.kr/orthopedics/
http://www.grand1.co.kr/orthopedics/content/orthopedics6            (찾아오시는길)
http://www.grand1.co.kr/orthopedics/core/board.php?bo_table=news&wr_id=28
http://www.grand1.co.kr/ophthalmology/
http://www.grand1.co.kr/ophthalmology/content/sub1_1                (병원소개)
http://www.grand1.co.kr/ophthalmology/content/sub1_2                (의료진소개)
http://www.grand1.co.kr/ophthalmology/content/sub1_4                (진료시간/오시는길)
http://www.grand1.co.kr/ophthalmology/content/sub5_1_1              (영유아시력검사)
http://grand1.co.kr/ophthalmology/core/board.php?bo_table=notice&wr_id=84
http://www.grand1.co.kr/pediatrics/                                 (그랜드 배내과)
http://www.grand1.co.kr/pediatrics/content/greeting
http://www.grand1.co.kr/pediatrics/content/location
http://www.grand1.co.kr/pediatrics/content/sub5_1                   (수액클리닉)
http://www.grand1.co.kr/pediatrics/content/clinic_neck03            (구내염)
http://grand1.co.kr/skin/                                           ← 폐기 대상
http://www.grand1.co.kr/skin/content/introduce
http://www.grand1.co.kr/skin/content/beauty_filler
http://www.grand1.co.kr/skin/content/beauty_botox
http://grand1.co.kr/skin/content/obesity_hpl
http://grand1.co.kr/skin/content/index.php?co_id=price&device=mobile
http://grand1.co.kr/skin/core/board.php?bo_table=counsel&page=2
http://www.grand1.co.kr/skin/core/board.php?bo_table=new_event&sca=…
```
