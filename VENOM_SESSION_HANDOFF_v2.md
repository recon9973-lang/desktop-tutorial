# 베놈 마케팅 웹사이트 — 새 대화 핸드오프 문서 v2

## 프로젝트 개요

- **회사**: 주식회사 베놈 (병원마케팅 대행사) / 대표 김보형 / 대구광역시 수성구
- **GitHub 리포지토리**: `recon9973-lang/desktop-tutorial`
- **개발 브랜치**: `claude/nice-cray-94p4hx`
- **Vercel 배포**: main 브랜치 자동 배포 (도메인 venomad 관련)
- **주요 파일 경로**: `/home/user/desktop-tutorial/venom-wordpress/preview/`

---

## 핵심 파일 목록

| 파일 | 설명 |
|------|------|
| `venom-wordpress/preview/index.html` | 메인 SPA (전체 사이트, CSS+JS 통합) |
| `venom-wordpress/preview/admin.html` | 관리자 페이지 (방문자 통계, 키워드 도구) |
| `venom-wordpress/preview/sample-dental.html` | 임플란트 치과 샘플 |
| `venom-wordpress/preview/sample-natural.html` | 자연주의 한의원 샘플 |
| `venom-wordpress/preview/sample-premium.html` | 프리미엄 뷰티클리닉 샘플 |
| `venom-wordpress/preview/sample-trust.html` | 대형병원 신뢰형 샘플 |
| `logo_venomad_hospital marketing.png` | 현재 사용 중인 로고 (루트) |

---

## index.html 구조 요약

### 헤더 (line ~609)
```html
<header class="site-header">
  <div class="container"> <!-- grid: 1fr auto 1fr -->
    <div></div>
    <div class="header-center">
      <a href="#" onclick="sp('home');return false" class="logo">
        <img src="https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/logo_venomad_hospital%20marketing.png" 
             alt="병원마케팅 베놈" style="height:52px;width:auto;display:block">
      </a>
      <nav><ul class="main-nav">
        <li>병원마케팅 dropdown (임플란트/교정 제외)</li>
        <li>AI마케팅 dropdown</li>
        <li>온라인마케팅</li>
        <li>블로그</li>
        <li>홈페이지 제작</li>
      </ul></nav>
    </div>
    <div class="header-actions">💬 상담신청</div>
  </div>
</header>
```

### 헤더 CSS
```css
.site-header .container { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; height:100% }
.site-header .header-center { display:flex; align-items:center; gap:8px }
.site-header .header-actions { display:flex; align-items:center; justify-content:flex-end; gap:8px }
.main-nav { display:flex; align-items:center; gap:2px }
```

### 페이지 전환 함수 (line ~4336)
```javascript
function sp(id, pushState) {
  if(pushState !== false) history.pushState({page:id}, '', '#'+id);
  // 페이지 활성화, 스크롤 top, preview-bar 활성, breadcrumb 업데이트
}
function ld(cat, pushState) {
  currentCat = cat;
  if(!pg-detail.active) sp('detail', false);
  if(pushState !== false) history.pushState({page:'detail', cat:cat}, '', '#'+cat);
  // 콘텐츠/TOC/키워드/사이드바 주입
}
// popstate 리스너 → 뒤로/앞으로 지원
// 초기 해시 복원 (location.hash 기반)
```

### 중요 숫자/내용
- 병원 운영 사례: **900+** (hero slide + stat-bar 두 곳)
- stat-bar CSS 충돌 해결: `.stat-bar { display:block }` 오버라이드 (line ~3151)

### 상담 폼 (id="contact-form")
- Google Apps Script Webhook: `https://script.google.com/macros/s/AKfycby8DngUbdYtGWz52yWVciUgo9I9B75mUQcgKcxo_q2ai0CBehLh-TUGzZ5d1BeY1S1wjg/exec`
- 구글 시트 + 이메일(venomad@naver.com 포함) 전송
- 마케팅 체크박스: 네이버광고/블로그, 인스타그램/SNS, GEO(AI검색), 병원홈페이지, 파워링크, 기타(텍스트입력)

### 홈페이지 샘플 모달
```javascript
openSample('sample-dental.html', '제목') // 모달로 iframe 띄움
closeSample() // ESC 또는 backdrop 클릭으로 닫기
```

### 입력 필드 엔터키 지원
- `#geo-name` → `runGEO()` (GEO 점수 분석)
- `#kw-input` → `runKW()` (키워드 검색량 조회)

---

## Git 작업 규칙 (중요)

```bash
# 커밋 전 항상 설정
git config user.email noreply@anthropic.com
git config user.name Claude
git config commit.gpgsign false

# 커밋
git add <파일>
git commit -m "메시지"

# 푸시 (개발 브랜치로)
git push -u origin main:claude/nice-cray-94p4hx

# diverged 상황 시
git fetch origin main
git rebase origin/main
git push origin main:claude/nice-cray-94p4hx --force
```

---

## 완료된 기능 목록

- [x] 전체 SPA 구조 (병원마케팅 카테고리별 상세 페이지)
- [x] 헤더 로고+nav 중앙 정렬 (3-col grid)
- [x] 로고 교체 (`logo_venomad_hospital marketing.png`)
- [x] 통계 수치: 병원 운영 사례 900+
- [x] 상담 폼 → Google Sheets + 이메일 전송
- [x] 홈페이지 제작 샘플 4종 + 모달 미리보기
- [x] 관리자 페이지: 방문자 통계, 키워드 도구
- [x] 브라우저 뒤로/앞으로 버튼 지원 (history API)
- [x] 텍스트 입력 엔터키로 분석 실행

## 향후 작업 아이디어 (미구현)

- 모바일 반응형 개선
- 실제 네이버 API 연동 (키워드 검색량)
- 블로그 콘텐츠 실제 데이터 연동
