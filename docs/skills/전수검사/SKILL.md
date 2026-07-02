---
name: 전수검사
description: VENOM 사이트 전체를 10개 영역으로 전수조사하고 발견 즉시 수정·배포한다 — SEO(seo-medical-expert 스킬 연계)·의료광고법·콘텐츠 6요구사항·오탈자·링크 매칭·실사 사진 현황 보고·코드 간소화·UI/UX·보안·개인정보처리방침/이용약관. "전수조사", "전수검사", "전체 점검", "사이트 감사" 요청 시 사용. 모든 수정은 사전 승인된 것으로 간주하고 커밋→PR→머지→브랜치 리셋 파이프라인으로 즉시 반영한다.
---

# 전수검사 — VENOM 사이트 종합 감사·수정 절차

지시가 오면 아래 10개 영역을 **자동화 스크립트 우선**으로 전수 점검하고,
발견 사항은 **즉시 수정 → 검증 → 커밋 → PR → 머지 → 브랜치 리셋**한다(모든 사항 사전 승인).
대상: `venom-wordpress/preview/` (index.html SPA + api/lib + images + vercel.json).

## 0) 준비
- **seo-medical-expert 스킬을 먼저 로드**해 §1.5 6요구사항·§7 의료광고 사례집 기준을 적용한다.
- 점검 스크립트는 스크래치패드에 작성. 과거 세션 스크립트 재사용 가능:
  `full-audit.js`(6요구사항+금지표현+오탈자), `final-matrix.js`, `link-audit*.js`, `inject-tables.js`.

## 1) 콘텐츠 6요구사항 매트릭스 (모든 H1 페이지)
pages 객체를 균형 파서로 항목 분해 후 페이지별 판정:
- 글자수 **3,000자 이상(공백 포함, 태그 제외)** — 공백 제외로 재지 말 것(과거 오판 원인)
- 인포그래픽(`data-vinfo`) · 실사진(`images/dept/`) · 데이터표(`<table`) · 출처 4개 이상(섹션 분산)
- 표 누락 시: 각 섹션 h2+💡콜아웃(없으면 첫 문단)을 "핵심 요약" 2열 표로 재구조화해 첫 dc-section 앞 주입
  (기존 콘텐츠 재구성 = 새 의학 주장 없음, `.dc-table` CSS 재사용)

## 2) 의료광고법 (의료법 제56·57조)
- 금지표현 정규식 스캔: 부작용/통증 없음 단정, 100%, 완치, 최초/유일/최저가, 비교·비방형, 유인성 할인
- **교육 맥락 제외 휴리스틱** 적용(금지·위반·지양·단정할 수 없습니다 등 주변어) 후 실위반만 조치
- "100%"는 CSS 노이즈가 대부분 — 콘텐츠 문장만 판정

## 3) 오탈자
- 패턴: 되요/안되/몇일/됬/드릴께/할께/왠만/단어중복 등
- 주의: `이가|가이` 같은 조사 패턴은 "가이드"에 오탐 — 결과는 반드시 눈으로 재확인

## 4) 링크 매칭
- 정적 앵커(href/ld()/sp()) + 본문 이스케이프 앵커 + 블로그 포스트(content/blog-posts*.json) 전수
- 검사: 라우트 존재(DETAIL_ROUTES/PAGE_ROUTES), 라벨↔목적지 일치, 기관명↔도메인 정답표 대조,
  비URL href·환각 도메인(예: venomagency.com) — 발견 시 공식 카카오채널(`pf.kakao.com/_jxjxdcxj/chat`)로 교정
- content-validator.js의 링크 소독 규칙이 재발 방지 중임을 확인

## 5) 실사 사진 보고 (수정 아닌 보고 항목)
- `images/dept/*.jpg` md5 중복 그룹핑 → 종류별 슬롯 수·고유 사진 수·신규 필요 수 산출
- 종류: 진료과 허브(7)·진료 세부주제(42+)·온라인마케팅(7)·섹션 공용(20)·심의/의료기기(2)·홈 의사(1)
- 파일명 규칙과 업로드 안내는 `images/dept/PHOTO-LIST.md`

## 6) 코드 간소화
- 죽은 코드: pages 항목 중 ld() 호출·라우트 참조 0건인 것(과거: geo/aeo/seo 구형 중복 195줄 제거)
- 중복 구조: 페이지별 복제 블록은 전역 1개로 통합(과거: 푸터 15→1, 614줄 감소)
- 삭제 전 반드시 참조 grep으로 0건 확인

## 7) UI/UX (Playwright — file:// 금지, python3 -m http.server 사용)
- 모바일 375px: `scrollWidth==clientWidth`(가로 오버플로 0 — logo-marquee-track은 의도된 예외),
  햄버거 메뉴 동작, 표 폭, 히어로 요소 폭
- 데스크톱: 대표 페이지 렌더, 신규 요소 스크린샷
- 직접 URL 접속 테스트는 로컬에서 404가 정상(SPA rewrite는 Vercel 전용) — 클라이언트 라우팅(sp/ld)으로 검증

## 8) 보안
- 시크릿 노출 grep: `sk-|github_pat_|ghp_|pplx-|AIza` + 알려진 시크릿 값
- vercel.json 보안 헤더(HSTS·X-Frame-Options·X-Content-Type-Options·Referrer-Policy·Permissions-Policy)
- admin은 클라이언트 게이트 + 서버측 ADMIN_SECRET 이중 구조가 정상

## 9) 개인정보처리방침·이용약관
- `/privacy`·`/terms` 페이지 존재, PAGE_ROUTES·rewrites·sitemap 등재, 푸터 링크, 상담 폼 동의 체크박스(required)
- 방침 필수 항목: 목적·항목·기간·제3자 제공·위탁/국외이전(Vercel·GitHub·카카오)·파기·권리·안전조치·책임자·변경고지

## 10) SEO 구조 + WebP
- H1=1/URL, 헤딩 건너뛰기 0, 고유 title/desc/canonical, sitemap.xml에 전 라우트 등재
  (**주의**: lib/sitemap-builder.js의 SITE_PATHS는 라우트 추가 시 수동 동기 필요)
- WebP: 사이트 이미지는 정적 .webp 직접 참조, 블로그 글은 imgToWebp()(wsrv.nl) 동적 송출,
  신규 업로드는 convert-webp.yml(재귀·sharp 명시 설치)이 자동 변환 — 3계층 모두 확인

## 검증·배포 규칙 (매 수정마다)
1. 인라인 JS 문법: vm.Script 전수 (10개 스크립트, 0오류)
2. Playwright 실렌더: H1 수·헤딩 순서·이미지 로드·라우팅
3. 커밋 메시지에 근거·검증 결과 명시, 트레일러:
   `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` + Claude-Session 링크
4. push → create_pull_request → merge_pull_request → `git checkout -B <작업브랜치> origin/main` → force-with-lease push
5. 최종 보고: 영역별 표(발견→조치→검증), 사진 보고 표, 잔여/권고 사항

## 하드 룰
- 가짜 인용·통계 금지(실출처만), 시크릿 값을 코드/PR/커밋에 넣지 않음
- vercel.app/cloudfront egress 차단 우회 금지 — 프로덕션 확인은 GitHub Actions(api-check.yml) 활용
- 삭제·대규모 치환 전 반드시 건수 확인 후 실행, 실행 후 잔존 0건 재확인
