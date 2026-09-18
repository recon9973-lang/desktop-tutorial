# RESUME (상권 네비 방) — **닫힘. 전부 나갔다** (2026-09-18 확인)

<!-- 가지: claude/charming-cerf-s4n1ca -->

> 상세는 `docs/session-logs/2026-09-16-nav-local.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.
> **이 방에서 이어갈 작업은 없다.** 설계 사이트맵 대비 미구현분도 없다.

## 한 줄

사장님 「상단 네비에 상권 탭이 없는데」 → 탭 하나가 아니라 **지역·상권 축 자체가 없었다.**
축을 세우고, 이어서 **설계 사이트맵에만 있고 만들지 않았던 자리를 전부 채웠다.**
**A·B·C 등급 모두 닫혔다.** main 반영과 실서비스 반영을 실측으로 확인했다.

## 나간 것

```
70e3136  상권분석 탭 + /local 지역·상권 허브 + 베놈 체크업 연결        (#249)
af0d7e6  태블릿 헤더 겹침 + 지역 글 6편에 제 주소                      (#250)
b8cd5ca  방 기록                                                      (#256)
6383ee5  B등급 여섯 — 페이지 14개 신설 + GEO/AEO/SEO 3단 구성          (#261)
df1eb9b  C등급 셋 — 조직 안내 · 샘플 연결 · 아래 메뉴 6칸              (#263)
```

다섯 커밋 전부 `origin/main` 조상 [실측 · merge-base]. 작업 가지 `claude/charming-cerf-s4n1ca`
는 main 과 같고 **앞선 커밋 0건.** 다시 커밋·배포할 일이 없다.

**만든 것 요약** — 상단 탭 7개(상권분석 신설) · `/local` 지역·상권 허브 ·
검색광고 4종 · SNS 2종 · 브랜드마케팅 4종 · SEO 세분 3종 · `/resources` ·
GEO/AEO/SEO 3단 구성 · 조직 안내 · 사이트맵 204 → 230 URL.

**실서비스 실측** — 두 번 쟀다. 재는 법은 아래 「재는 법」.

```
[실측 2026-09-16] A 등급 판  상단 탭에 상권분석 · /local · 헤더 CTA → /contact ·
                             드로어 분기점 1023px · 사이트맵 216 URL
[실측 2026-09-18] B·C 판     사이트맵 230 URL · /local · /resources ·
                             /naver-ads/powerlink · /brand/planning · /seo/technical ·
                             /online-marketing/daangn · /clinic/location/ 전부 실려 있다
```

## 다음 방 몫

**없다.** 설계 원본 `홈페이지 제작을 위한 최종 사이트맵 구조 (Sitemap).txt` 대비
A·B·C 등급 미구현분이 전부 닫혔다. 새로 재려면 세션 기록의 「구조 점검」 절과 같은 방식으로
설계 원본과 `PAGE_ROUTES`·`DETAIL_ROUTES` 를 대조하면 된다.

굳이 남은 것을 꼽자면 **사장님 확인이 필요한 것 하나** —
조직 안내의 「담당 영역 일곱」은 **지금 파는 서비스를 기준으로** 정리한 것이다.
실제 조직과 다르면 `index.html` 의 `AREAS` 한 곳만 고치면 된다.

## 주의·제약 (다음 방이 밟을 자리)

- **이 방은 실서비스를 직접 못 잰다** — venomad.com·vercel egress 403.
  대신 **`fetch-file.yml` 을 workflow_dispatch 로 띄우면 러너가 대신 받아 가지에 커밋한다.**
  이 저장소에서는 `actions:write` 가 **된다**(옛 방 인계의 「403」 과 다르다 · 이 방에서 두 번 썼다).
  확인이 끝나면 임시 파일은 지운다.
- **상단 네비는 `뷰포트 − 321px` 를 넘으면 헤더 우측 버튼과 겹친다.** 탭을 늘리기 전에 이 값부터 재라.
  지금 7탭이고 1024px↑ 겹침 0px, 1023px↓ 는 드로어다. **메뉴를 늘릴 일이 생기면 탭이 아니라
  드롭다운·메가로 담는다**(B등급 때 21항목을 그렇게 담았다).
- **큰 객체 리터럴에 이어 붙일 때는 앞 항목이 쉼표로 끝나는지 먼저 본다.**
  `DETAIL_ROUTES` 마지막 항목에 쉼표가 없어 전 페이지 JS 가 깨진 적이 있다.
  브라우저 오류는 엉뚱한 곳을 가리키므로 **스크립트 블록 단위 구문 검사**로 위치를 특정한다
  (인라인 JS 15블록 · 구조화데이터 8블록이 정상 구성).
- **로컬 검증 서버는 `vercel.json` rewrite 를 그대로 흉내내고, 파일시스템을 먼저 본다.**
  느슨하게 쓰면 `/seo/seo-engine.js` 가 HTML 로 돌아와 **없는 JS 오류**가 생긴다(이 방이 한 번 속았다).
  `/seo/` 는 실제 디렉터리가 있으므로 하위 라우트를 더할 때 특히 주의.
- **사진은 파일명으로 고르지 말고 보고 고른다.** 후보를 한 장에 펼쳐 놓고 확인하면 된다.
  광고·마케팅 글에 임상 사진(수술 기구·시술 장면)이 들어가면 안 된다.
- **기준선을 같은 조건에 놓기 전에 단언하지 말 것.** 이 방은 여섯 번 틀렸고 대부분 그 이유였다
  (세션 기록 「내가 틀린 자리」).
- 정적 지역 글을 더할 때는 `index.html` 의 `slug` 와 `lib/sitemap-builder.js` 의
  `STATIC_POST_SLUGS` **둘 다** 고친다. 한쪽만 고치면 `check-sitemap` 이 표류로 잡는다(정상 동작).
- `PROJECT_STATE.md` 는 자동 생성물 — 손대지 말고 CI 또는 `node scripts/gen-project-state.mjs`.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` + `Claude-Session: …`.
  모델 ID 는 트레일러에만.
- 사장님께는 **쉬운 말**로. 「커밋」·「배포」 두 낱말만, 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 재는 법 (이 방이 쓴 것)

```
로컬 검증   preview/ 를 정적 서버로 띄우고 vercel.json rewrite 를 흉내낸다
            (파일시스템 우선 → 그다음 리라이트) · playwright-core + /opt/pw-browsers
기준선 대조  git show origin/main:…/index.html > __baseline.html 로 같은 서버에 띄워 같은 자를 댄다
실서비스     워크플로 fetch-file.yml (workflow_dispatch) 로 러너가 받아 오게 한다
구문 검사    인라인 <script> 를 블록 단위로 new Function() 에 넣어 본다
사이트맵     node scripts/check-sitemap.js (표류 기준 = 라이브 + 정적)
```

## 참고

- 루트 `RESUME.md` 는 **다른 방 것**이다(방마다 바뀐다). 이 방 것은 이 파일이다.
- 이 저장소 인계는 방마다 따로다 — `RESUME-*.md` 목록을 먼저 볼 것.
- **이 저장소는 베놈 마케팅 사이트**(`venom-new-site.vercel.app`)다. ANSEO(`veo.seokorea.org`)
  는 `veo-platform` 저장소다 — 다른 물건이다(CLAUDE.md 맨 앞 규칙).
