# Google 검색(SEO) 공식 문서 지식맵 — 마스터 인덱스

> **출처**: `google_seo_guide/` 폴더 내 **201개 마크다운 파일** (Google 검색 센터 / Google 크롤링 인프라 한국어 공식 문서)
> **작성 방식**: 201개 파일 전문(全文) 정독 후 구조화. **파일에 실제 기재된 내용만 반영(할루시네이션 없음)**. 파일에서 누락·중복·스텁으로 확인된 사항은 그대로 표기.
> **문서 번호 `[n]`**: `file_index_win.txt`의 정렬 순번(1~201)과 일치.

---

## 0. 개요 및 통계

| 항목 | 값 |
|------|-----|
| 총 파일 수 | 201개 (전부 `.md`) |
| 실질 고유 문서 | 약 160종 (중복본 약 41개 제외) |
| 대분류 | ① Google 검색 센터 Documentation(약 160) ② 크롤링 인프라(약 35) ③ What's new / Status(소수) |
| 확인된 완전 중복본 | 아래 §17 중복본 지도 참조 |
| 캡처 누락 확인 | `[30]` URL 구조 문서의 상세 표가 빈 표(헤더만)로 캡처됨 |

### 카테고리 구조 (본 지식맵의 목차)
1. SEO 기초 & 검색 작동 원리
2. 콘텐츠 품질 & E-E-A-T & 생성형 AI
3. 크롤링 · 색인 생성
4. robots.txt
5. Google 크롤러(User-Agent) — 크롤링 인프라
6. 사이트맵
7. URL 구조 & 표준화(Canonical) & 리디렉션
8. 구조화된 데이터(스키마) — 리치 결과
9. 전자상거래(이커머스)
10. 국제화(다국어·다지역)
11. 스팸 · 보안 정책
12. AMP · 웹 스토리
13. Search Console · 분석 · 디버깅
14. 검색 노출 기능(SERP 요소)
15. 순위 시스템 & 알고리즘 업데이트 & 페이지 경험
16. JavaScript SEO
17. 중복본 지도 & 문서 변경 로그
18. 핵심 수치·제약 통합 레퍼런스

---

## 1. SEO 기초 & 검색 작동 원리

- **[89] SEO 기본 가이드 기본사항 (Starter Guide)** — 가장 일반적·효과적인 SEO 개선사항 종합. `site:`로 색인 확인, CSS/JS 차단 금지, 설명적 URL·디렉터리 그룹화, 사람 중심 콘텐츠, 이미지 alt. **무시할 것**: 키워드 메타태그 미사용, 키워드 스터핑=스팸, URL/도메인 키워드는 순위에 거의 무영향, 콘텐츠 길이는 순위요인 아님, 중복 콘텐츠 페널티 없음, E-E-A-T는 직접 순위요인 아님.
- **[40] Google 검색의 작동 방식 상세 가이드** — 3단계: **크롤링**(URL 발견·렌더링, 최신 Chrome, JS 실행) → **색인 생성**(콘텐츠·태그 분석, 중복 클러스터링·표준 선정) → **게재**(위치·언어·기기 등으로 관련성 결정). 준수해도 크롤링·색인·게재 보장 안 됨. 금전으로 순위 상승 불가.
- **[8] Google 검색 Essentials (구 웹마스터 가이드라인)** — 3축: 기술 요구사항(최소요건) / 스팸 정책(위반 시 강등·제거) / 주요 권장사항(개선요소).
- **[10] Google 검색 기술 요구사항** — 최소 3요건: ①Googlebot 미차단 ②페이지 작동(HTTP `200`) ③색인 가능 콘텐츠 존재.
- **[128] 기술 SEO 기법 및 전략** — 유지관리 심화(중복·표준화, robots.txt, 사이트맵, hreflang, 이전 301/302, soft 404 회피, 크롤링 예산). 전 세계 인터넷 인구 60%+ 모바일.
- **[162] 웹 개발자를 위한 SEO 가이드** — 크롤링 가능한 `<a>`, 사이트맵, JS 앱 URL, 텍스트화, 의미론적 HTML(CSS `content` 값은 색인 안 됨).
- **[104] SEO 전문가 채용 도움말** — 서비스 범위·인터뷰 질문. Search Console은 **읽기 권한만** 부여. '1위 보장'·'Google 특별관계' 주장 주의. 신고: 미 FTC / econsumer.gov.
- **[157] 서드 파티 SEO 도구·조언 안내** — 데이터·경험 기반이거나 공식 가이드 인용 조언이 좋은 조언. 'Google 승인' 주장 주의, 도구가 순위 보장 못함, 내부 순위 데이터 접근 불가.

---

## 2. 콘텐츠 품질 & E-E-A-T & 생성형 AI

- **[171] 유용하고 신뢰할 수 있는 사용자 중심 콘텐츠** — 자가평가 질문 세트. **E-E-A-T 중 신뢰성이 가장 중요**하나 E-E-A-T 자체는 직접 순위요소 아님. **YMYL**(건강·금융·안전)은 높은 E-E-A-T에 가중. '누가·어떻게·왜' 평가. 선호 단어 수 없음. 순위 조작용 AI 대량 생성=스팸.
- **[169] 생성형 AI 콘텐츠 안내** — 가치 없는 대량 생성 = '확장된 콘텐츠 악용' 위반. 품질평가자 가이드라인 §4.6.5/§4.6.6. AI 이미지엔 IPTC `DigitalSourceType`=`TrainedAlgorithmicMedia`.
- **[39] 생성형 AI 기능 최적화 가이드** — 생성형 AI 검색도 핵심 순위 시스템 기반 → 기존 SEO 유효. **RAG(그라운딩)**·**쿼리 팬아웃** 설명. **하지 않아도 되는 것**: LLMS.txt(무시), 청킹, AI 전용 재작성, 진정성 없는 언급, 구조화데이터 과집중. (2026-06-24)
- **[1] AI 기능 및 웹사이트 (AI 개요/AI 모드)** — AI 기능 노출에 특별 최적화 불필요(기존 SEO면 충분). 제어: `nosnippet`, `data-nosnippet`, `max-snippet`, `noindex`; AI 학습 제한은 `Google-Extended`.
- **[38] Google 검색의 리뷰 시스템** — 심층·독창 고품질 리뷰 우대. 퍼스트파티 리뷰 평가(제품페이지의 서드파티 사용자 리뷰는 미평가). 적용 11개 언어.
- **[141] 리뷰 작성 방법** — 전문성 입증(영상·증거), 수치 측정, 장단점, 여러 판매자 링크. 길이 아닌 품질·독창성.
- **[143] 메타 설명 작성 방법** — 스니펫은 주로 콘텐츠에서 자동 생성. 제어: `nosnippet`/`max-snippet`/`data-nosnippet`. 길이 제한 없음(기기폭 잘림), 페이지별 고유.
- **[170] 유연한 샘플링 가이드라인** — 구독/페이월. **한도 측정(월간 권장)**·도입부 표시. 일일 뉴스 게시자 **월 6~10개(출발점 10개)**. 페이월 10%+ 조회 노출 시 만족 급감.

---

## 3. 크롤링 · 색인 생성

- **[58] 크롤링 및 색인 생성 (개요/허브)** — 하위 주제 목차. (2025-12-31)
- **[49] 웹 크롤링에 대해 알아야 할 사항** — Googlebot 외 특화 크롤러 다수. 반복 크롤링(뉴스 몇 분~미변경 한 달). 페이월 로그인 뒤 미접근. 모바일 페이지 중앙값 816KB→**2.3MB**, 로드 파일 60개+.
- **[196]/[195] 크롤링에 관한 허구와 사실** — 사이트맵 압축은 예산 미증가; Google은 날짜 아닌 품질 평가; 쿼리매개변수 URL 크롤링 가능; 빠른 로드=더 많은 크롤링; `crawl-delay` 미지원; `noindex`/`nofollow`도 예산 소모, 4xx(429제외)는 낭비 아님; 크롤링은 순위 신호 아님.
- **[194]/[193] 크롤링 예산 관리** — 대상: 고유 100만+(주1변경)/1만+(매일). 예산 = 용량 한도 + 수요. 호스트명별 별도. 중복 통합·robots 차단·404/410·soft404 제거·`<lastmod>`.
- **[16] 크롤링 오류 문제 해결** — 가용성/미크롤링/지연/효율/과도. `If-Modified-Since`/`If-None-Match`→`304`. 과도 시 일시 `503`/`429`(2일 초과 시 색인 삭제 위험).
- **[86] HTTP 상태 코드의 영향** — `2xx` 처리(204는 불가, 빈페이지=soft404); `3xx` 최대 10홉(301/308 강함, 302/303/307 약함); `4xx` 미사용·삭제(429는 서버오류 취급); `5xx`·429 속도 저하 후 지속 시 삭제.
- **[56] 네트워크 및 DNS 오류 디버그** — 네트워크 타임아웃·DNS 오류는 5xx 유사 처리→즉시 속도 저하. `dig`로 A/CNAME/NS 확인, DNS 전파 72시간.
- **[64] Googlebot이란** — 스마트폰·데스크톱 통칭(토큰 동일, 선택 타겟 불가). 대부분 모바일 색인. 지원 형식 처음 **2MB**, PDF **64MB**(압축해제 기준).
- **[68] 재크롤링 요청** — 소수는 URL 검사도구(할당량), 다수는 사이트맵. 며칠~몇 주.
- **[75] 색인 가능 파일 형식** — `Content-Type`로 판별. 플랫/인코딩 파일 다수(**.hwp 한글** 포함). 이미지: BMP,GIF,JPEG,PNG,WebP,SVG,AVIF. 동영상: 3GP,MP4,WebM,MKV 등. (2026-02-06)
- **[87] noindex로 색인 차단** — `<meta name="robots" content="noindex">` 또는 `X-Robots-Tag`. robots.txt의 noindex 미지원. robots.txt 차단 시 태그 못 봐서 계속 노출 가능.
- **[139] 로봇 메타 태그 사양** — 지원 토큰 `googlebot`,`googlebot-news`. 규칙: noindex,nofollow,none,nosnippet,indexifembedded,`max-snippet:[n]`,`max-image-preview`,`max-video-preview`,notranslate,noimageindex,`unavailable_after`. `data-nosnippet`은 span/div/section. `max-snippet` 0=nosnippet, -1=길이 제한 없이 Google이 최적 길이 선택; `max-video-preview` 0=정적이미지, -1=무제한.
- **[79] 지원 메타 태그·속성** — description,robots/googlebot,notranslate,nopagereadaloud,google-site-verification,Content-Type,refresh,viewport,rating. 미지원: keywords, HTML lang, rel next/prev, nositelinkssearchbox. 충돌 시 더 제한적 적용.
- **[105] 발신 링크 관계(rel)** — `sponsored`(유료)·`ugc`(사용자생성)·`nofollow`. 다중값 공백/쉼표.
- **[80] SEO 링크 권장사항** — `href` 있는 `<a>`만 안정 크롤링. 앵커텍스트 구체·간결. `nofollow`/`sponsored`/`ugc`.
- **[24] Google과 공유 정보 관리(콘텐츠 차단)** — 삭제/비밀번호/`noindex`/robots.txt(이미지·동영상)/서비스 사용중지.
- **[74] 사이트 정보 삭제** — 삭제 도구 임시(약 **6개월** 지속). 영구: 삭제/비밀번호/`noindex`.
- **[76] 수정된 정보 제외** — 검은 사각형·동일 글꼴색은 실제 삭제 아님(OCR 노출). 이미지는 삽입 전 편집·병합(PNG/WEBP).
- **[26] 이미지 삭제** — 긴급=삭제도구, 비긴급=robots.txt Disallow 또는 `noindex X-Robots-Tag`. `Googlebot-Image`=이미지검색만.
- **[136] 동적 렌더링** — 크롤러엔 정적 HTML, 사용자엔 CSR. **임시방편(권장 아님)**. 유사 콘텐츠면 클로킹 아님.
- **[144] 모바일 중심 색인** — 스마트폰 크롤러 색인. 반응형(권장)/동적게재/별도URL(m.). 모바일·데스크톱 동일 콘텐츠·메타·구조화데이터.
- **[66] 페이지로 나누기** — pagination/load more/무한스크롤. `<a href>`만 크롤링(버튼 클릭 안 함). 각 페이지 고유 URL(`?page=n`), 프래그먼트 금지.
- **[187] 지연 로드 콘텐츠** — 뷰포트 진입 시 로드, 상호작용 의존 금지. IntersectionObserver. 무한스크롤=고유·영구 URL·절대 페이지번호.
- **[29] A/B 테스팅 권장사항** — 버전별 URL+리디렉션 또는 JS 동적 삽입. **클로킹 금지**(Googlebot·사용자 동일). 대체 URL은 `rel=canonical`(noindex보다 권장). 리디렉션은 `302`(임시). 필요 기간만, 종료 후 신속 제거.
- **[175] 이미지 SEO 권장사항** — 표준 `<img src>`(CSS 배경 이미지 색인 안 됨), `srcset`/`<picture>`도 `src` 대체 지정. 선호 이미지 `primaryImageOfPage`/`og:image`. 구체적 파일명·alt(스터핑 금지). 인라인 연결 해제=Google 리퍼러에 `200`(내용없음)/`204`. 지원 형식 BMP/GIF/JPEG/PNG/WebP/SVG/AVIF.

---

## 4. robots.txt

- **[96] robots.txt 소개·가이드** — 요청 과부하 방지용. **검색에서 숨기는 수단 아님**(숨김=noindex/비밀번호). 차단해도 외부 링크로 색인 가능. 리소스 파일 차단 금지.
- **[72] (69·70·71 중복) robots.txt 사양 해석** — REP(RFC 9309). 최상위 위치, 호스트·프로토콜·포트별 적용, 경로 대소문자 구분. 지원 필드 4개: user-agent/allow/disallow/sitemap(`crawl-delay` 미지원). 와일드카드 `*`·`$`. 우선순위=긴(구체) 규칙. **크기 500KiB, UTF-8, 캐시 24시간**. HTTP: 2xx정상 / 3xx 5홉+=404 / 4xx(429제외)=제한없음 / 5xx=12시간 중단·30일 캐시.
- **[97]/[98] robots.txt 만들기·제출** — 루트 위치, robots 배제 표준. 4단계(생성·규칙·업로드·테스트). `Disallow`/`Allow`는 `/` 시작, allow가 disallow 재정의. `*`는 AdsBot 제외 전체 적용. sitemap은 정규화 URL.
- **[99]/[100]/[101] robots.txt 업데이트** — 다운로드(브라우저/`curl -o`/Search Console) → 수정(UTF-8) → 업로드. 캐시 **24시간**, 빠른 갱신은 재크롤링 요청.
- **[174] (172·173 중복) 유용한 robots.txt 규칙** — 표 형식 예시. `Disallow: /`도 URL 색인 가능. 빈 Disallow=전체 허용. 와일드카드 예 `/*.gif$`. 여러 User-agent 결합.

---

## 5. Google 크롤러(User-Agent) — 크롤링 인프라

- **[55] 크롤러 개요** — 3분류: 일반 크롤러 / 예외 상황 크롤러 / 사용자 트리거 가져오기. HTTP/1.1·HTTP/2(거부=`421`), FTP/FTPS. 캐싱 ETag/Last-Modified(ETag 우선). 파일 한도 처음 **15MB**(프로젝트별 상이, Googlebot 2MB). gzip/deflate/Brotli.
- **[84] (83 중복) 일반 크롤러** — Googlebot(`Googlebot`), 이미지(`Googlebot-Image`), 동영상(`Googlebot-Video`), 뉴스(`Googlebot-News`), StoreBot(`Storebot-Google`), InspectionTool, GoogleOther(±Image/Video), Google-CloudVertexBot, **Google-Extended**(Gemini 학습·그라운딩 제어, 검색·순위 무영향). `common-crawlers.json`, 역DNS `crawl-*.googlebot.com`.
- **[45]/[46] 예외 상황 크롤러** — 전역 `*` 무시, 명시 토큰만. APIs-Google, AdsBot(`AdsBot-Google`), AdsBot 모바일, AdSense(`Mediapartners-Google`), Google 안전센터(`Google-Safety`, robots.txt 완전 무시). `special-crawlers.json`.
- **[42]/[43] 사용자 트리거 가져오기 도구** — robots.txt **무시**. Google-CWS, FeedFetcher, Google-Agent(Project Mariner), GoogleMessages, Google-NotebookLM, Google-Pinpoint, GoogleProducer, Google-Read-Aloud, Site-Verification.
- **[3] APIs-Google** — 푸시 알림(HTTPS POST), 지수 백오프. 올바른 SSL 필요. robots.txt `APIs-Google` 지정으로 차단.
- **[5] Feedfetcher** — RSS/Atom(팟캐스트만 색인). robots.txt **무시**. 시간당 2회↓. `Feedfetcher-Google`.
- **[6] Google Read Aloud** — TTS. robots.txt 선택해제 불가 → `nopagereadaloud` meta. 페이월=`isAccessibleForFree=False`. 구명 `google-speakr`.
- **[59]/[60]/[61] 크롤링 속도 낮추기** — 긴급 감속: `500`/`503`/`429` 응답(2~3시간~1~2일). 속도 증가 요청 불가.
- **[53]/[54] 요청 확인(위장 방지)** — 역방향 DNS(`googlebot.com`/`google.com`/`googleusercontent.com`) + 순방향 확인, 또는 IP 범위 대조(JSON 목록).
- **[57] 크롤링 문서 변경 로그** — web-bot-auth(2026-05), Google-Agent(2026-03), IP 범위 이동(2026-02), Google 메시지(2026-01), 크롤링 문서 사이트 이전(2025-11) 등. RSS 제공.
- **[165]/[166] 웹 크롤러 인증(실험용, Web Bot Auth)** — 암호화 서명 인증(IETF 초안). 실험용→IP/역DNS 병행. `agent.bot.goog`, `Signature-Agent`/`Signature`/`Signature-Input`, RFC 9421.

---

## 6. 사이트맵

- **[153] 사이트맵이란** — 효율 크롤링 지원 파일. 필요: 대규모/새 사이트/리치미디어·뉴스. 불필요할 수 있음: **500개 이하**·내부 긴밀 연결.
- **[151] 사이트맵 제작·제출** — 형식 XML/RSS·Atom/텍스트. UTF-8·절대·표준 URL. `<priority>`·`<changefreq>` 무시, `<lastmod>`는 일관·정확시만. 제출: Search Console/API/robots.txt `Sitemap:`/WebSub. **1개당 50MB(비압축) 또는 URL 50,000개**.
- **[150] (149 중복) 사이트맵 색인 파일** — 분할 후 색인 파일. **계정당 색인 파일 500개**, 색인 파일에 `loc` **최대 50,000개**. 네임스페이스 `sitemap/0.9`.
- **[152] 확장 프로그램 결합** — `xmlns`로 image(`sitemap-image/1.1`)/news(`sitemap-news/0.9`)/video(`sitemap-video/1.1`)/xhtml(hreflang) 네임스페이스 선언.
- **[176] 이미지 사이트맵** — `<image:image>`(url당 **최대 1,000개**)·`<image:loc>`. 네임스페이스 `sitemap-image/1.1`. caption/geo/title/license 지원 중단.
- **[130] 뉴스 사이트맵** — `news:` 확장. **지난 2일 이내** 기사만. 사이트맵당 **1,000개** news 태그. 네임스페이스 `sitemap-news/0.9`. 필수: news/publication/name/language/publication_date/title.
- **[133] 동영상 Sitemap** — `<video:video>`+thumbnail_loc/title/description + (content_loc 또는 player_loc). duration 1~28800초, description 2,048자, tag 32개, rating 0.0~5.0. 네임스페이스 `sitemap-video/1.1`.

---

## 7. URL 구조 & 표준화(Canonical) & 리디렉션

- **[30] URL 구조 권장사항** — IETF STD 66, 설명형·하이픈·매개변수 최소·대소문자 인지. 복잡 URL=중복·대역폭 낭비. ⚠️ **본문 상세 표가 빈 표로 캡처됨**(규칙 세부 누락).
- **[181] 전자상거래 URL 구조** — 3대 문제(프래그먼트 콘텐츠 누락·중복 크롤링·무한 URL). `?key=value`, 임시 매개변수 내부링크 금지, 빈 카테고리 `noindex`/`404`.
- **[94] URL 표준화란** — 중복 삭제로 대표 URL 선택. 원인: 지역·기기·프로토콜·필터·실수. 중복 자체는 정상(스팸 아님). 신호: HTTPS·리디렉션·사이트맵·`rel=canonical`(힌트).
- **[95] rel=canonical 지정 방법** — 강도: 리디렉션 > `rel=canonical` > 사이트맵. HTML head 또는 HTTP 헤더(일관). 절대경로. HTTPS·hreflang 클러스터 선호. robots.txt/삭제도구/noindex로 표준 지정 금지.
- **[200] 표준화 문제 해결** — URL 검사도구로 선택 확인. 문제: hreflang 누락·CMS 오지정·서버 오구성·해킹·신디케이션·모방(DMCA). (2025-12-31)
- **[140] 리디렉션 및 Google 검색** — 영구(`301`/`308`/즉시 meta refresh/JS location)=새 대상 표시. 임시(`302`/`303`/`307`/지연 refresh)=소스 표시. 서버측 권장.
- **[147] 사이트 이동·이전(URL 변경)** — 5단계. 한 번에 하나만, 트래픽 적을 때, `301`은 PageRank 손실 없음. 체인 최대 10홉(권장 ≤3, 최대 5). **리디렉션 최소 1년 유지**. 중소형 몇 주.
- **[167] 웹 호스팅·SEO 변경(URL 무변경 이전)** — 임시 호스트 `noindex`, **DNS TTL 1주 전 낮춤**, Search Console 소유권 유지, 이전 시작 시 차단 삭제.
- **[168] 웹사이트 일시중지·사용 중지** — **권장: 기능 제한**(온라인 유지). 전체 중지는 비권장(복구 시간·보장 없음). 불가피 시 1~2일=`503`(robots.txt는 계속 허용, `retry-after`), 장기=`200` 자리표시자. `403/404/410`·`noindex` 금지.

---

## 8. 구조화된 데이터(스키마) — 리치 결과

- **[114] 구조화 데이터 작동 방식 소개** — 리치 결과. 형식 **JSON-LD(권장)**/마이크로데이터/RDFa. 사례(Rotten Tomatoes CTR +25% 등). 빈/미표시 정보 마크업 금지.
- **[115] 일반 가이드라인** — 기술(3형식, Googlebot 미차단) + 품질(스팸 금지, 미표시 콘텐츠 마크업 금지, 가짜 리뷰 금지) + 관련성 + 완전성 + 이미지 크롤링 가능.
- **[28] 지원 마크업 갤러리** — 지원 유형 카탈로그(기사·탐색경로·캐러셀·과정·이벤트·채용·지역비즈니스·제품·Q&A·레시피·리뷰·앱·Speakable·페이월·공유숙박·동영상 등). 캐러셀은 단독 불가.
- **[132] 대화형 인리치드 검색결과** — 리치 결과 하위집합. 3종: 채용/레시피/이벤트. 완전성이 핵심 신호. 리프 페이지 한정.
- **[179] JS로 구조화 데이터 생성** — GTM(맞춤 HTML JSON-LD) 또는 맞춤 JS(`application/ld+json`) 또는 SSR. 리치결과 테스트 검증.

**콘텐츠·미디어 스키마**
- **[145] 기사(Article/NewsArticle/BlogPosting)** — 필수 없음. 권장 author/dateModified/datePublished/headline/image. 작성자 개별 나열, `Thing` 금지. (파일명은 '문서 스키마'지만 실제는 기사 스키마)
- **[135] 동영상(VideoObject/Clip/BroadcastEvent)** — **필수 name·thumbnailUrl·uploadDate**(description·duration(PT1M54S)·contentUrl·embedUrl은 권장). 실시간=BroadcastEvent(isLiveBroadcast). 중요부분=Clip/SeekToAction.
- **[134] 동영상 SEO 권장사항** — 표준 태그 삽입, 전용 보기 페이지. URL 3종(보기/플레이어/파일). 썸네일 최소 60x30px.
- **[138] 레시피** — 필수 image/name. 권장 다수(cookTime·recipeIngredient·recipeInstructions·nutrition). ItemList로 캐러셀.
- **[116] 영화(Movie)** — 캐러셀은 **휴대기기만**. ItemList/ListItem/Movie.
- **[117] 리뷰 스니펫(Review/AggregateRating)** — 도서·과정·이벤트·지역비즈니스·영화·제품·레시피·앱. 지역비즈니스·조직은 타 대상 리뷰 캡처 사이트만.
- **[159] 소프트웨어 앱(SoftwareApplication)** — 필수 name/offers.price/(aggregateRating 또는 review). VideoGame 단독 불가. 앱 유형 22종.
- **[102(103)]** → §13 (site: 연산자)
- **[88] Q&A 페이지(QAPage)** — 사용자 답변 제출형만. Question(answerCount/acceptedAnswer 또는 suggestedAnswer/name), Answer(text). (2026-06-24)
- **[113] 교육 Q&A(Quiz)** — 플래시카드 고정 `eduQuestionType:Flashcard`. 언어 영어·포르투갈어·베트남어(+스페인어 멕시코).
- **[118] 수학 문제 해결사(MathSolver)** — **홈페이지**에 추가. potentialAction(SolveMathAction). 첫 문제 풀이 접근 가능해야.
- **[110]/[109] 교육과정(Course)** — 리치결과 **영어만**, **3개 이상**. Course(description/name), ItemList(itemListElement/position/url). description 60자.
- **[106] 사실확인(ClaimReview)** — ⚠️ **Google 검색 지원 단계적 중단 중**(사실확인 탐색기는 유지). 페이지당 1개. claimReviewed 75자.
- **[93] Speakable(베타)** — TTS 섹션. Article/WebPage에서 cssSelector 또는 xPath(하나만). 20~30초/2~3문장. 영어 미국.
- **[198] 토론 포럼(DiscussionForumPosting/SocialMediaPosting)** — 포럼용. comment 중첩. mainEntity로 기본 게시물.
- **[201] 프로필 페이지(ProfilePage)** — mainEntity(Person/Organization, 기본 Person). dateCreated/dateModified. interactionStatistic.
- **[111] 구독·페이월(CreativeWork)** — 필수 `isAccessibleForFree:false`. hasPart.cssSelector(.class). 중첩 금지. 클로킹 구분용.
- **[197] 탐색경로(BreadcrumbList)** — itemListElement/name/item/position(1부터). 마지막 item 생략 가능. 데스크톱, 전 지역·언어.
- **[122] 캐러셀(ItemList)** — 4종: Course/Movie/Recipe/Restaurant. ListItem 2개+ 동일 유형.
- **[192] 캐러셀(베타)** — ItemList + LocalBusiness/Product/Event. **EEA·튀르키예·남아공만**. ListItem 3개+. 이미지 ≥50,000px.
- **[185] 조직(Organization)** — 홈페이지/회사소개에. 필수 없음. 로고 **최소 112x112px**. address(ISO 3166-1 alpha-2)·contactPoint·sameAs·식별자(DUNS/GLN/LEI). (2026-04-20)
- **[121] 지역 비즈니스(LocalBusiness)** — 필수 address/name. openingHoursSpecification. geo 소수점 5자리. priceRange 100자. (2026-02-20)
- **[52] 이벤트(Event)** — 필수 location/address/name/startDate(ISO 8601). eventStatus(취소/조정). 리프 페이지. 실제 물리 장소.
- **[188] 채용 정보(JobPosting)** — 필수 datePosted/description/hiringOrganization/title/jobLocation. 재택=jobLocationType TELECOMMUTE. 만료 미삭제 시 수동조치. Indexing API 권장.
- **[112] 고용주 평점(EmployerAggregateRating)** — itemReviewed(Organization)/ratingValue/(ratingCount 또는 reviewCount). 척도 기본 5.
- **[107] 공유숙박(VacationRental)** — 얼리어답터. 이미지 **최소 8장**, 위경도 **5자리+**. amenityFeature 영어 고정.
- **[37] 도서(Book: ReadAction/BorrowAction)** — 얼리어답터(신청 필요). 저작물(Work)/판본(Edition) 구분, workExample 필요. **ISBN-13 선호(ISBN-10 불가)**. 피드 파일 압축 전/후 각 1GB 미만, 루트 단일 DataFeed, `@context: https://schema.org`. 매일 갱신 권장(약 2일 색인). 호스팅 GCS/HTTPS/SFTP/AWS S3.
- **[159]**(위 참조), **[51] 이미지 메타데이터(ImageObject/IPTC)** — 라이선스 배지. 필수 contentUrl+(creator/creditText/copyrightNotice/license). 배지엔 license 필수. C2PA로 AI 생성 표시. (2026-02-20)

**제품(전자상거래) 스키마** → §9 참조: [81][119][120][123][124][125][126][183]

---

## 9. 전자상거래(이커머스)

- **[182] 전자상거래 SEO 권장사항(허브)** — 하위 문서 목차.
- **[85] 전자상거래 제품 데이터·콘텐츠** — 표시 경로: 검색·이미지·렌즈·쇼핑탭·비즈니스 프로필·지도. 렌즈/쇼핑탭/지도는 **판매자 센터** 필요.
- **[65] 제품 데이터 공유** — 구조화 데이터 또는 판매자 센터 피드. 쇼핑탭=판매자 센터 필수. Content API(즉시). `data-nosnippet`.
- **[78] 전자상거래 사이트 출시** — 5단계. 전략 4종: 완전 공개/홈페이지 출시/재고 없이 출시(`excluded_destination`)/제한적 출시.
- **[184] 탐색 구조** — Google은 링크 연결로 중요도 추론. 메뉴→카테고리→제품 링크 경로. `<a href>`, JS 이벤트 금지.
- **[81] 구조화 제품 데이터 소개** — 2종: 제품 스니펫(비구매·리뷰·장단점) / 판매자 등록정보(구매·배송·반품). 웹페이지+피드 병행 시 자격 극대화.
- **[119] 제품 스니펫(Product)** — review/aggregateRating. **장단점** positiveNotes/negativeNotes(ItemList).
- **[123] 판매자 등록정보(Product/Offer)** — 가격 3종: 활성/할인전(StrikethroughPrice)/회원가(validForMemberTier). priceSpecification(UnitPriceSpecification).
- **[120] 제품 옵션(ProductGroup/Product)** — variesBy(color/size/suggestedAge/suggestedGender/material/pattern), hasVariant, productGroupID. hasAdultConsideration=SexualContentConsideration. (2026-05-27)
- **[124] 반품 정책(MerchantReturnPolicy)** — Organization에 hasMerchantReturnPolicy. returnPolicyCategory 3종(Finite/NotPermitted/Unlimited). 국가 최대 50개.
- **[125] 배송 정책(ShippingService)** — hasShippingService. shippingConditions(목적지·주문금액별). handlingTime/transitTime(ServicePeriod). orderPercentage.
- **[126] 포인트 제도(MemberProgram)** — 필수 description/hasTiers/name. TierBenefitLoyaltyPoints/Price. 제공: DE/US/UK/AU/BR/CA/MX.
- **[183] 전자상거래 구조화 데이터** — 관련 유형: BreadcrumbList/LocalBusiness/Organization/Product·ProductGroup/Review/VideoObject.
- **[73] 배송 추적** — 얼리어답터(인도·일본·브라질). API 평균 700ms/95p 1,000ms. 필수 CurrentStatus.

---

## 10. 국제화(다국어·다지역)

- **[127] 국제·다국어 개요(허브)** — 하위 3편 링크. (스텁, 2025-12-18)
- **[131] 다지역·다국어 관리** — 다국어(언어)·다지역(국가) 구분. URL 언어 구분+hreflang. 자동 리디렉션 금지. 지역 타겟 URL(ccTLD/하위도메인/하위디렉터리/매개변수). gTLD 취급 ccTLD 목록(.io,.co,.tv,.me 등). geo.position meta 무시.
- **[199] 페이지의 현지화된 버전(hreflang)** — 3방법(HTML link/HTTP 헤더/사이트맵 xhtml:link). **양방향 링크 필수**, x-default. 언어 ISO 639-1, 지역 ISO 3166-1 alpha-2, 스크립트 ISO 15924. Google은 언어감지에 hreflang 미사용.
- **[77] 언어 적응형 페이지 크롤링** — Googlebot 미국 IP 기본, `Accept-Language` 미설정. 지역 분산 크롤링. 실제 사용자와 동일 취급.
- **[146] 번역된 검색결과** — 제목·스니펫 현지 언어 번역. 선택해제 `notranslate`. 지원 **21개 언어**(한국어 포함).
- **[108] 광고 네트워크 및 번역 검색 기능** — 번역 URL(`.translate.goog`) → 원 URL 디코딩(9단계 `decodeHostname`).

---

## 11. 스팸 · 보안 정책

- **[47] 웹 검색 스팸 정책** — 클로킹/도어웨이/만료도메인 악용/해킹/숨김텍스트/키워드 스터핑/링크 스팸/머신 트래픽/악의적 행위/**확장된 콘텐츠 악용**/**사이트 인지도 악용**/빈약한 제휴/UGC 스팸. `nofollow`·`sponsored`면 링크 스팸 아님.
- **[13] 스팸 업데이트** — SpamBrain(AI). 준수 학습 시 수개월 회복. **링크 스팸**은 이전 이점 제거되어 회복 안 될 수 있음.
- **[156] 사이트 악용 방지(허브)** — UGC 스팸/멀웨어/멀웨어 감염/소셜 엔지니어링/반복 위반자 링크.
- **[154]/[155] 사용자 생성 스팸 방지** — 가입 과제, `noindex`, `nofollow`/`ugc`, 수동 승인, IP 차단, reCAPTCHA. `site:`·Safe Browsing·Translate API 모니터링.
- **[142] 멀웨어 감염 방지** — Search Console 모니터링. 안전 비밀번호·패치·로그 점검·XSS/SQL 확인. SSH/SFTP.
- **[158] 소셜 엔지니어링(피싱·사기)** — 피싱/사기 콘텐츠/불충분 라벨 서드파티. Chrome '사기성 사이트' 경고. 4단계 해결. 타사 브랜드 명시.
- **[44] 세이프 브라우징 반복 위반자** — 준수/위반 반복 사이트. 지정 시 **30일 지속**(그동안 재검토 불가).
- **[129] 노골적 콘텐츠 SEO 가이드라인** — 세이프서치 필터, EDSA 예외. CSAM 항상 삭제·순위 강등. 5단계(UGC 방지·크롤링 허용·별도 도메인 그룹화·메타데이터). `rating:adult` 또는 RTA.
- **[48] 웹 스토리 콘텐츠 정책** → §12.
- **[25] 선정적 콘텐츠 오신고** — 세이프서치 확인. 흔한 실수 5종. 재처리 2~3개월.
- **[169]** → §2 (생성형 AI 콘텐츠).

---

## 12. AMP · 웹 스토리

- **[36] (31·32·33·34·35 중복, 총 6본) AMP 정보** — Google은 AMP도 동일 기준 색인. AMP HTML 사양, 표준 페이지 동일 콘텐츠. 모바일 전용 아님(반응형 권장). 데스크톱 AMP는 검색 기능 미지원.
- **[22] AMP 콘텐츠 향상** — 제작→가이드라인→표준 연결. AMP 테스트·리치결과 테스트. CMS 플러그인.
- **[2] AMP 유효성 검사** — AMP 테스트/리치결과/Search Console AMP 보고서. `rel="amphtml"`·`rel="canonical"`.
- **[23] AMP 삭제** — 3옵션(모두/AMP만/CMS). `301`/`302`/`404`.
- **[82] 웹 스토리 사용 설정** — 유효 AMP·메타데이터·색인·정책. 디스커버 표시 미국·브라질·인도. 필수 publisher-logo-src/poster-portrait-src/title/publisher.
- **[164] 웹 스토리 만들기 권장사항** — 페이지당 텍스트 ~280자, 제목 90자 미만(70 권장), 동영상 15초(최대 60), 오디오 5초+. poster 640×853(3:4), 로고 96×96(1:1). (2026-06-17)
- **[48] 웹 스토리 콘텐츠 정책** — 저작권/텍스트 과다/저품질/불완전 스토리/과도 광고 금지. 180자+ 텍스트면 미표시 가능, 동영상 페이지당 60초 미만.

---

## 13. Search Console · 분석 · 디버깅

- **[91] Search Console 사용 방법** — 4단계(소유권·색인·사이트맵·실적). SEO/개발자 역할별 보고서. 이메일 알림. 삭제 도구 약 6개월.
- **[90] Search Console + Google 애널리틱스 데이터** — SC(방문 전)·GA(방문 후). 클릭수↔세션수. Looker Studio. 불일치 원인 다수(시간대 PT·기여모델·비HTML).
- **[92] 풍선형 차트** — Looker Studio. y=평균게재순위(반전)·x=CTR(로그). 4사분면 분석.
- **[17] 트래픽 감소 파헤치기** — 원인(업데이트/계절성/기술/보안/이전/오류). 16개월 기간·비교·게재순위. Google 트렌드로 업계 전반 확인.
- **[62] Google 트렌드 시작** — 집계·익명 샘플. 탐색·실시간 도구. 검색어 최대 5개.
- **[15] 검색 연산자 디버깅** — `filetype:`/`imagesize:`/`site:`/`src:`. URL 검사 도구가 더 안정적.
- **[50] 이미지 검색 연산자** — `src:`(참조 페이지)·`imagesize:`(크기). 이미지 검색만.
- **[103]/[102] site: 연산자** — 도메인/URL/접두사 한정. 색인 확인·스팸 식별. 모든 URL 반환 안 함, 검색어 없으면 무작위(짧은 URL 상단).
- **[7] Search Status Dashboard** — 검색 서비스 상태. ⚠️ (영어 스텁, 실질 내용 거의 없음).
- **[186] 지역 검색결과 등 표시 중지** — 쇼핑/항공/호텔/지역결과 opt-out. **도메인별** 적용. 기존 콘텐츠 30일 내 삭제.

---

## 14. 검색 노출 기능(SERP 요소)

- **[11] 검색 노출(허브)** — 노출 기능·구조화 데이터 기능 목록.
- **[14] 시각적 요소 갤러리** — 텍스트/리치/이미지/동영상 결과. 기여분석(파비콘·사이트명·URL). 사이트링크 그룹=2개+.
- **[27] 시선을 끄는 제목 링크** — 모든 페이지 `<title>` 구체·고유. 키워드 스터핑·상용구 금지. Google이 소스(title/heading/og:title/앵커/WebSite)로 생성·개선. (2025-12-18)
- **[20] 유효한 페이지 메타데이터** — `<head>` 유효 HTML. 무효 요소(iframe/img) 뒤 요소 무시.
- **[21] 검색에 표시되는 사이트 이름** — `WebSite` 구조화 데이터(홈페이지). name/url 필수. alternateName. 사이트당 1개(도메인 단위).
- **[19] 파비콘 정의** — 홈페이지 `<link rel="icon">`. 사이트당 1개. 정사각형 ≥8x8(48x48+ 권장).
- **[18] 검색결과 서명일** — CreativeWork datePublished/dateModified. 표시 날짜와 일치. 향후·이벤트 날짜 금지.
- **[148] 사이트링크** — 자동 생성(제어 불가). 유익한 제목·논리 구조·내부 앵커. 삭제=페이지 삭제/noindex.
- **[191] 추천 스니펫** — 상단 설명 상자. 차단 `nosnippet`/`data-nosnippet`, 추천만 차단 `max-snippet` 짧게. 강제 표시 불가.
- **[137] 디스커버에 콘텐츠 등록** — 자동 자격(특별 태그 불필요). 큰 이미지(≥1,200px·300,000px+·16:9, `max-image-preview:large`). 클릭베이트 지양. 16개월 보고서.
- **[163] 선호하는 소스(Preferred Sources)** — 사용자가 선택→주요 뉴스·AI 배지. 도메인·하위도메인만. 딥링크 `google.com/preferences/source?q=`. 한국어 버튼 애셋.
- **[177] 인기 장소 목록 최적화** — 실제 매장만. 진정성·독립·비후원. 표시 중지 옵션.
- **[67] 비즈니스 세부정보 추가** — 비즈니스 프로필 소유권. Search Console 확인. 지식 패널 재정의. Organization 로고·탐색경로. 반영 약 1주.

---

## 15. 순위 시스템 & 알고리즘 업데이트 & 페이지 경험

- **[12] 순위 시스템 가이드** — 페이지 수준+사이트 신호. AI: BERT/MUM/신경망/RankBrain. 기타: 위기정보/중복삭제/EMD/최신정보/링크분석·PageRank/원본/신뢰정보/리뷰/사이트 다양성(동일 사이트 2개+ 방지). 삭제 기반 강등(법적·개인정보). 통합: 유용한콘텐츠(2024.3 편입)·Panda(2015)·Penguin(2016). SpamBrain.
- **[41] 핵심 업데이트** — 연 수 회 광범위 변경. 특정 사이트 겨냥 아님(레스토랑 비유). SC 진단(완료 후 1주+). 빠른 해결책 금지. 수일~수개월 회복.
- **[13] 스팸 업데이트** → §11.
- **[63] 페이지 경험 이해** — 전반적 경험 보상. 자가평가(CWV·HTTPS·모바일·광고·전면광고). 순위 직접 사용은 **Core Web Vitals**. 2023-05 INP 도입.
- **[4] Core Web Vitals** — 실제 사용자 경험. **LCP ≤2.5초, INP <200ms, CLS <0.1**. SC CWV 보고서. (2025-12-18)
- **[180] 전면 광고·대화상자** — 방해 전면 광고=성능 저하. 배너 권장. 전체 리디렉션 금지(1페이지만 남음). 필수 광고(연령인증) 예외.

---

## 16. JavaScript SEO

- **[178] JavaScript SEO 기본** — 3단계(크롤링·렌더링·색인, Chromium Evergreen). robots 차단 시 렌더 안 함. 고유 title·canonical(HTML 동일)·HTTP 상태. soft 404 방지. 프래그먼트 대신 History API. 지문 파일명.
- **[9] JS 문제 해결** — 리치결과/URL 검사, 전역 onerror. SPA soft 404 방지. Googlebot 권한 요청 거부. AJAX 크롤링 스킴 중단(2015). WRS 상태 미유지, WebSocket/WebRTC 미지원.
- **[136] 동적 렌더링** → §3.
- **[179] JS 구조화 데이터** → §8.
- **[187] 지연 로드** → §3.

---

## 17. 중복본 지도 & 문서 변경 로그

### 완전 중복본 지도 (내용 100% 동일, 파일명 `(n)` 차이만)
| 대표 | 중복 사본 | 주제 |
|------|-----------|------|
| [36] | [31][32][33][34][35] | AMP 정보 (6본) |
| [72] | [69][70][71] | robots.txt 사양 해석 (4본) |
| [98] | [97] | robots.txt 만들기·제출 |
| [99] | [100][101] | robots.txt 업데이트 (3본) |
| [174] | [172][173] | 유용한 robots.txt 규칙 (3본) |
| [103] | [102] | site: 검색 연산자 |
| [84] | [83] | 일반 크롤러 |
| [46] | [45] | 예외 상황 크롤러 |
| [43] | [42] | 사용자 트리거 가져오기 도구 |
| [54] | [53] | 크롤러 요청 확인 |
| [61] | [59][60] | 크롤링 속도 낮추기 (3본) |
| [110] | [109] | 교육과정(Course) 스키마 |
| [150] | [149] | 사이트맵 색인 파일 |
| [155] | [154] | 사용자 생성 스팸 방지 |
| [161] | [160] | 속성 탐색 URL 크롤링 관리 |
| [166] | [165] | 웹 크롤러 인증(실험용) |
| [190] | [189] | 최신 문서 업데이트(What's new) |
| [194] | [193] | 크롤링 예산 관리 |
| [196] | [195] | 크롤링에 관한 허구와 사실 |

### 문서 변경 로그
- **[189]/[190] 최신 검색 문서 업데이트(What's new)** — 2020~2026 변경 이력. 2026-07 AMP 간소화, 2026-06 llms.txt 불필요·FAQ 리치결과 삭제, 2026-05 hasAdultConsideration·생성형 AI 가이드·FAQ 지원 중단, 2026-04 뒤로가기 하이재킹 정책. RSS 제공.
- **[57] 크롤링 문서 변경 로그** → §5.

### 특이/스텁 문서
- **[7]** Search Status Dashboard — 영어 스텁.
- **[127]** 국제·다국어 개요 — 허브 스텁(13줄).
- **[156]/[182]/[58]/[11]** — 링크 목차 성격의 허브 페이지.
- **[30]** URL 구조 — 상세 표 캡처 누락.
- **[145]** 파일명 '문서 스키마'지만 실제 내용은 **기사(Article) 스키마**.

### 속성 탐색 URL
- **[160]/[161] 속성 탐색 URL 크롤링 관리** — 필터/패싯의 무한 URL. robots.txt disallow·프래그먼트·`rel=canonical`·nofollow. 구분자 `&`. 결과 없는 조합 `404`.

---

## 18. 핵심 수치·제약 통합 레퍼런스

> 파일에 명시된 수치만 수록.

### HTTP 상태 코드 처리
| 코드 | Google 크롤러 처리 |
|------|-------------------|
| `2xx` | 색인 고려(204·빈페이지=soft404) |
| `301`/`308` | 영구(강한 표준 신호) |
| `302`/`303`/`307` | 임시(약한 신호) |
| `304` | 캐시 재사용(If-Modified-Since/If-None-Match) |
| `4xx`(429제외) | 미사용·색인 삭제 |
| `429`·`5xx` | 속도 저하, 지속 시 삭제 |
| `421` | HTTP/2 거부 시 |

### 크기·개수 한도
| 대상 | 한도 |
|------|------|
| robots.txt | 500KiB, UTF-8, 캐시 24시간 |
| 크롤러 파일 기본 | 처음 15MB(Googlebot 2MB, PDF 64MB) |
| 사이트맵 1개 | 50MB(비압축) / URL 50,000개 |
| 사이트맵 색인 파일 | 계정당 500개 / loc 50,000개 |
| 이미지 사이트맵 | url당 image 1,000개 |
| 뉴스 사이트맵 | news 태그 1,000개 (지난 2일 기사) |
| 동영상 duration | 1~28,800초(8h), description 2,048자, tag 32개 |
| 리디렉션 홉 | 최대 10(권장 ≤3, 최대 5) |
| 반품 정책 국가 | 최대 50개 |

### Core Web Vitals 임계
- LCP ≤ 2.5초 · INP < 200ms · CLS < 0.1

### 이미지 권장(구조화 데이터 공통)
- 비율 16x9 / 4x3 / 1x1, 최소 50,000픽셀(너비×높이)
- 조직 로고 최소 112×112px · 파비콘 최소 8×8px
- 지역비즈니스·공유숙박 위경도 소수점 5자리 이상

### 시간/기간
- 삭제 도구 지속: 약 6개월
- 세이프 브라우징 반복 위반자: 30일
- 서비스 opt-out 콘텐츠 삭제: 30일 이내
- DNS 전파 대기: 72시간
- 리디렉션 유지 권장: 최소 1년
- 페이월 샘플링: 월 6~10개 기사(출발점 10)

### 표준 코드 체계
- 국가: ISO 3166-1 alpha-2 · 언어: ISO 639-1 · 스크립트: ISO 15924 · 날짜/시간: ISO 8601 · URL: IETF STD 66

---

*본 지식맵은 `google_seo_guide/` 201개 파일의 전문 정독 결과를 구조화한 것이며, 각 항목은 해당 원본 파일에서 확인된 사실만을 담고 있습니다. 원문 상세(코드 예시·전체 속성 표 등)는 `[n]` 번호에 해당하는 원본 `.md` 파일을 참조하세요.*
