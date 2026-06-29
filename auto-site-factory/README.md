# 🏭 VENOM Site Factory

홈페이지 자동 개발 시스템. 고객 정보를 입력하면 기획→제작까지 자동으로 사이트를 찍어낸다.

전체 설계는 [`MASTER_PLAN.md`](./MASTER_PLAN.md) 참고.

## 현재 구현 (MVP 1차)

- **대상**: 병원·의료 카테고리 (`clinic`)
- **운영 모델**: 직원용 내부 도구
- **출력**: 정적 사이트 (index.html + robots.txt + sitemap.xml + llms.txt)

```
auto-site-factory/
├── MASTER_PLAN.md            # 전체 기획안
├── intake/index.html         # ① 직원용 고객정보 입력폼 → site-spec.json
├── blueprints/clinic/        # ② 병원 카테고리 정의
│   ├── blueprint.json        #    진료과목·규모·기본옵션
│   └── template.html         #    홈페이지 템플릿 (토큰 치환)
├── engine/                   # ③ 자동생성 엔진
│   ├── generate.js           #    site-spec + blueprint → 완성 사이트
│   └── seo.js                #    robots/sitemap/llms.txt (SEO팩 기본내장)
├── samples/site-spec.example.json
└── output/                   # 생성된 사이트 (gitignore, 재생성 가능)
```

## 사용법

**1) 직원이 입력폼 작성** — `intake/index.html`을 브라우저로 열어 고객 정보 입력 → `site-spec.json` 다운로드

**2) 엔진으로 사이트 생성**
```bash
node engine/generate.js samples/site-spec.example.json
# → output/seoul-smile-com/ 에 완성 사이트 생성
```

**3) 미리보기** — `output/<도메인>/index.html`을 브라우저로 열기

## 옵션 팩 (베놈 도구 재활용)

| 팩 | 기능 | 상태 |
|---|---|---|
| ⑤ AI검색 최적화 | SEO/AEO/GEO/llms.txt | ✅ 기본 내장 |
| ③ 의료광고 검수 | 의료광고법 위반 검수 | 🔌 `lib/medical-ad-validator.js` 연결 예정 |
| ① 블로그 자동발행 | 키워드→AI초안→발행 | 🔌 `lib/post-generator.js` 연결 예정 |
| ② 이미지 변환 | AI이미지+WebP | 🔌 `lib/image-generator.js` 연결 예정 |
| ④ 다국어 | 자동번역 | 🔌 `lib/translate.js` 연결 예정 |
| ⑥ 분석 | 방문 인사이트 | 🔌 `api/analytics.js` 연결 예정 |

## 워드프레스 멀티사이트 배포 (2차 — 구현됨)

같은 `site-spec.json`을 워드프레스 멀티사이트에 실제 사이트로 찍어낸다. (콘텐츠는 정적 출력과 동일 — `prepare()` 공유)

```bash
# 1) 멀티사이트 1회 초기화
cd venom-wordpress/docker && ./multisite-setup.sh

# 2) spec → 프로비저닝 스크립트 생성
node auto-site-factory/engine/wp-adapter.js auto-site-factory/samples/site-spec.example.json --write
#   → output/<slug>/provision.sh  (wp site create + 페이지 + 옵션팩 플러그인 + SEO)

# 3) 멀티사이트에 실제 생성
cd venom-wordpress/docker
docker compose run --rm wp-cli bash < ../../auto-site-factory/output/<slug>/provision.sh
```

`provision.sh`가 하는 일: ① 네트워크에 새 사이트 생성 → ② 브랜드 색상/슬로건 저장 → ③ 옵션 팩 플러그인 활성화 → ④ 홈+서브 페이지 생성(콘텐츠 주입) → ⑤ SEO(robots/sitemap/llms.txt) 발행.

## 다음 단계 (3차)

- 옵션 팩 플러그인(`venom-seo`, `venom-autoblog` 등)에 기존 `lib/*` 모듈 실제 배선
- 소상공인(`local`) 블루프린트 추가 — 두 번째 카테고리
- 도메인 자동 매핑 + SSL + Cloudflare 캐시 연동
