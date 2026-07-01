/*!
 * VENOM SEO 용어사전 — 데이터 + 렌더/필터 (초성 ㄱㄴㄷ · ABC · 카테고리 · 검색)
 * 사용: <div id="glossary-root"></div> 후 Glossary.mount('glossary-root')
 */
(function (root) {
  'use strict';
  var CATS = {
    basic:    { label: '기본 용어',    color: '#533afd' },
    engine:   { label: '검색엔진',     color: '#0ea5e9' },
    keyword:  { label: '키워드',       color: '#16a34a' },
    technical:{ label: '테크니컬',     color: '#ea580c' },
    link:     { label: '링크빌딩',     color: '#9333ea' },
    optimize: { label: '최적화',       color: '#e11d48' },
    ai:       { label: 'AI·의료',      color: '#0d9488' }
  };
  // [ko, en, def, cat]
  var TERMS = [
    ['검색엔진 최적화','SEO','검색엔진에서 찾기 쉽도록 사이트를 개선하는 프로세스.','basic'],
    ['검색 엔진','Search engine','구글, 야후, 네이버와 같이 정보를 찾아주는 엔진.','basic'],
    ['SERP','SERP','Search Engine Results Pages의 약자로 검색엔진 결과 페이지를 의미.','basic'],
    ['온페이지 SEO','on-page SEO','소유하고 있는 웹사이트상에서 수행하는 최적화 작업.','basic'],
    ['오프페이지 SEO','Off-page SEO','해당 웹사이트가 아닌 다른 공간에서 이루어지는 최적화 작업.','basic'],
    ['온서프 SEO','on-SERP SEO','검색결과 페이지에서 이루어지는 최적화 작업.','basic'],
    ['블랙햇 SEO','Black hat SEO','검색엔진의 정책에 반하는 SEO 작업.','basic'],
    ['화이트햇 SEO','White hat SEO','검색엔진이 권장하는 방식의 SEO 작업.','basic'],
    ['그레이햇 SEO','Grey hat SEO','블랙햇과 화이트햇의 경계에 있는 SEO 작업.','basic'],
    ['크롤링','Crawling','신규 또는 업데이트된 웹페이지를 찾는 프로세스.','basic'],
    ['피쳐드 스니펫','Featured snippets','특정 검색어에 제공되는 검색결과 상위의 오가닉 답변 박스.','basic'],
    ['이미지 캐러셀','Image carousels','특정 검색결과에 보여지는 좌우 스크롤형 이미지 모음집.','basic'],
    ['인덱싱','Indexing','수집 페이지를 분석한 후 빠르게 찾아볼 수 있도록 저장하는 작업.','basic'],
    ['KPI','KPI','Key Performance Indicator의 약자로 목표 달성 성과를 객관적으로 평가하는 핵심 기준.','basic'],
    ['로컬 팩','Local pack','검색어 주제와 검색자의 지리적 위치를 고려한 위치 기반 결과.','basic'],
    ['오가닉','Organic','유료 광고가 아닌 자연적으로 얻어진 검색결과 순위.','basic'],
    ['관련 질문','People Also Ask','검색결과에 보여지는 드롭다운 형태의 연관 추가 질문 모음.','basic'],
    ['쿼리','Query','사용자가 검색창에 입력하는 검색어.','basic'],
    ['랭킹','Ranking','검색어에 대한 연관순 검색결과 나열.','basic'],
    ['트래픽','Traffic','웹사이트로의 방문 유입.','basic'],
    ['URL','URL','Uniform Resource Locators의 약자로 콘텐츠의 주소·위치.','basic'],

    ['알고리즘','Algorithms','검색 의도에 가장 적합한 결과를 전달하기 위해 정보를 채굴·정렬하는 프로세스·공식.','engine'],
    ['크롤러','Crawler','스파이더·로봇으로 불리며 웹 페이지를 수집·색인 생성하는 자동 소프트웨어.','engine'],
    ['크롤 버짓','Crawl budget','검색엔진 수집봇이 웹사이트에서 평균적으로 수집하는 페이지 수.','engine'],
    ['페이지 랭크','PageRank','구글 검색 결과에서 웹페이지 순위를 정하는 구글의 알고리즘.','engine'],
    ['색인','Index','제공할 가치가 있는 콘텐츠를 선별해 모아놓은 거대한 데이터베이스.','engine'],
    ['2xx 상태 코드','2xx status codes','서버 요청 처리 성공 응답(상태) 코드.','engine'],
    ['301 리디렉션','301 redirect','도메인·URL을 영구적으로 변경할 때 사용하는 리디렉션.','engine'],
    ['302 리디렉션','302 redirect','페이지·사이트를 일시적으로 옮길 때 사용하는 리디렉션.','engine'],
    ['404 에러','404 error','요청한 파일이 없어 불러올 수 없을 때 표시하는 에러.','engine'],
    ['5xx 상태 코드','5xx status codes','서버 오류로 인한 요청 처리 불가 상태 코드.','engine'],
    ['캐싱','Caching','웹페이지의 저장본.','engine'],
    ['카페인','Caffeine','구글의 색인 시스템으로 수집된 웹 콘텐츠의 모음집.','engine'],
    ['클로킹','Cloaking','검색엔진과 방문자에게 서로 다른 콘텐츠를 보여주는 편법.','engine'],
    ['구글 서치 콘솔','Google Search Console','구글이 사이트를 어떻게 인식하는지 점검하는 관리자용 무료 툴.','engine'],
    ['HTML','HTML','Hypertext markup language의 약자로 웹 페이지를 만드는 데 쓰이는 언어.','engine'],
    ['내부 링크','Internal links','같은 웹사이트의 다른 페이지로 이동시키는 링크.','engine'],
    ['자바스크립트','JavaScript','웹 페이지에 행동 요소를 추가하는 프로그래밍 언어.','engine'],
    ['노인덱스 태그','NoIndex tag','검색엔진에게 특정 페이지를 색인하지 말라고 알려주는 메타 태그.','engine'],
    ['로봇 배제 표준','Robots.txt','검색엔진 로봇의 접근을 제어하고 사이트맵 위치를 알려주는 규약.','engine'],
    ['사이트 맵','Sitemap.xml','웹사이트 내의 모든 페이지들을 나열한 파일.','engine'],

    ['키워드 경쟁지수','Keyword Difficulty','특정 키워드를 사용하는 경쟁자가 얼마나 많은지 숫자로 나타낸 수치.','keyword'],
    ['롱테일 키워드','Long-tail keywords','검색량은 적지만 검색의도가 구체적으로 표현된 키워드.','keyword'],
    ['검색량','Search volume','해당 키워드를 얼마나 검색했는지 보여주는 수치.','keyword'],
    ['시드 키워드','Seed keywords','제공하는 제품·서비스를 설명하는 기본적인 단어.','keyword'],
    ['LSI 키워드','LSI keywords','Latent Semantic Indexing, 특정 주제와 밀접하게 관련되어 자주 쓰이는 단어.','keyword'],
    ['키워드 카니발리제이션','Keyword cannibalization','여러 콘텐츠가 동일 키워드로 경쟁해 어느 것도 상위가 아닌 상태.','keyword'],

    ['오픈 그래프','Open Graph Protocol','페이스북 등에서 웹사이트의 디테일한 정보를 제공하게 하는 기능.','technical'],
    ['트위터 카드','Twitter card','트위터에서 링크 공유 시 글·이미지를 미리보기로 보는 기능.','technical'],
    ['이미지 대체 텍스트','Image alt text','웹 수집봇에게 이미지를 설명하는 문자열.','technical'],
    ['앵커 텍스트','Anchor text','링크가 삽입된 텍스트.','technical'],
    ['이미지 사이트 맵','Image sitemap','웹사이트에 업로드된 이미지의 URL만 나열한 파일.','technical'],
    ['키워드 스터핑','Keyword stuffing','같은 키워드를 의도적으로 반복하는 정책 위반 작업.','technical'],
    ['타이틀 태그','Title tag','검색결과에서 페이지의 제목을 보여주는 HTML 태그.','technical'],
    ['메타 디스크립션','Meta descriptions','웹페이지에 대한 요약 설명글.','technical'],
    ['보안 프로토콜','Security Protocol(HTTPS)','HTTP 보안 강화 버전으로 SSL·TLS로 세션 데이터를 암호화.','technical'],
    ['캐노니컬 태그','Rel=canonical','원본 및 중복 URL 주소를 검색엔진에게 알려주는 태그.','technical'],
    ['SSL','SSL','Secure Sockets Layer, 서버·브라우저 간 데이터를 암호화하는 보안 기술.','technical'],
    ['썸네일','Thumbnails','큰 이미지의 작은 버전.','technical'],
    ['AMP','AMP','Accelerated Mobile Pages, 더 빠른 로딩을 제공하는 페이지 복사본.','technical'],
    ['브라우저','Browser','웹에서 정보를 얻을 수 있게 하는 소프트웨어(크롬·익스플로러 등).','technical'],
    ['서브 도메인','Subdomain','상위 도메인의 하위에 있는 독립적인 웹사이트.','technical'],
    ['서브 폴더','Subfolder','루트 폴더 하위에 속한 폴더.','technical'],
    ['ccTLD','ccTLD','country code top level domain, 특정 국가 관련 도메인(.kr·.uk 등).','technical'],
    ['CSS','CSS','Cascading Style Sheet, 웹 페이지의 디자인 요소를 설정하는 언어.','technical'],
    ['Hreflang','Hreflang','문서의 언어 및 지역을 지정하는 HTML 메타 요소.','technical'],
    ['IP 주소','IP address','Internet Protocol, 네트워크 상 컴퓨터의 고유 주소.','technical'],
    ['모바일 중심 색인','Mobile-first indexing','모바일 버전 수집봇으로 모바일 페이지를 중점 크롤링·색인하는 구글 방식.','technical'],
    ['렌더링','Rendering','코드를 사용자가 볼 수 있는 비주얼 형식으로 변환하는 프로세스.','technical'],
    ['반응형 웹 디자인','Responsive design','각 기기에 최적화된 사이즈로 변하는 구글 권장 웹 디자인.','technical'],
    ['리치 스니펫','Rich snippet','이미지·비디오·FAQ 등이 추가되어 개선된 검색결과(리치 결과).','technical'],
    ['구조화된 데이터','Structured Data','검색엔진이 콘텐츠를 더 잘 이해하도록 조직화해 제공하는 데이터.','technical'],

    ['도메인 점수','Domain Authority','DA, 웹사이트가 상위 랭킹에 오를 가능성을 예측한 점수.','link'],
    ['백링크','Backlinks','다른 도메인의 사이트에서 해당 페이지로 연결된 링크.','link'],
    ['링크 주스','Link Juice','하이퍼링크를 통해 다른 사이트로 전달하는 가치·권력.','link'],
    ['노팔로우 링크','rel=nofollow','링크 주스를 제공하지 않고 검색 순위에 기여하지 않는 링크.','link'],
    ['팔로우 링크','DoFollow links','모든 링크의 기본 상태로 링크 주스를 제공하는 링크.','link'],
    ['구글 애널리틱스','Google Analytics','사이트와 사용자의 상호작용 인사이트를 제공하는 구글 무료 툴.','link'],
    ['링크 빌딩','Link building','다른 사이트로부터 방문자 유입 링크를 얻어 권위를 높이는 작업.','link'],

    ['이탈율','Bounce rate','사이트를 방문한 후 상호작용 없이 이탈한 비율.','optimize'],
    ['채널','Channel','소셜미디어·자연검색 등 유입을 얻기 위한 다양한 수단.','optimize'],
    ['클릭율','Click-through rate','CTR, 노출 대비 얻은 URL 클릭수의 비율.','optimize'],
    ['전환율','Conversion rate','유입된 방문자 수 대비 전환수의 비율.','optimize'],
    ['구글 애널리틱스 목표','GA goals','구글 애널리틱스로 전환율을 추적하기 위해 설정하는 목표.','optimize'],
    ['구글 태그 관리자','Google Tag Manager','웹사이트의 여러 트래킹 코드를 관리하는 구글 무료 툴.','optimize'],
    ['구글봇','Googlebot','구글의 웹 수집봇.','optimize'],
    ['프루닝','Pruning','부진한 콘텐츠를 버려 웹사이트 전체 퀄리티를 높이는 작업.','optimize'],
    ['서치 트래픽','Search traffic','구글과 같은 검색엔진을 통해 유입된 웹사이트 방문.','optimize'],
    ['페이지 체류시간','Time on page','사용자가 한 페이지에 체류하는 시간.','optimize'],
    ['UTM 코드','UTM code','Urchin tracking module, URL 끝에 삽입해 유입 경로를 추적하는 코드.','optimize'],

    ['GEO','GEO','Generative Engine Optimization, 생성형 AI가 병원을 추천·인용하도록 최적화하는 전략.','ai'],
    ['AEO','AEO','Answer Engine Optimization, AI 답변 엔진이 병원 콘텐츠를 답변으로 채택하도록 최적화.','ai'],
    ['E-E-A-T','E-E-A-T','경험·전문성·권위성·신뢰성, 구글이 YMYL 콘텐츠 품질을 평가하는 기준.','ai'],
    ['Core Web Vitals','Core Web Vitals','LCP·INP·CLS 3지표로 페이지 품질을 측정하는 구글의 핵심 웹 지표.','ai'],
    ['의료광고 심의','Medical ad review','의료법 제56·57조에 따라 특정 의료광고가 받아야 하는 사전 자율심의.','ai']
  ];

  var CHO = ['ㄱ','ㄱ','ㄴ','ㄷ','ㄷ','ㄹ','ㅁ','ㅂ','ㅂ','ㅅ','ㅅ','ㅇ','ㅈ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
  var CHO_LIST = ['ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
  function chosung(ko) { var c = ko.charCodeAt(0); if (c >= 0xAC00 && c <= 0xD7A3) return CHO[Math.floor((c - 0xAC00) / 588)]; return null; }
  function abcLead(en) { var m = String(en).match(/[A-Za-z]/); return m ? m[0].toUpperCase() : '#'; }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

  var state = { mode: 'all', val: '', cat: 'all', q: '' };
  var rootEl = null;

  function chip(label, active, attrs) { return '<button class="gl-chip' + (active ? ' on' : '') + '" ' + attrs + '>' + label + '</button>'; }

  function buildControls() {
    var abcSet = {}; TERMS.forEach(function (t) { abcSet[abcLead(t[1])] = 1; });
    var abcKeys = Object.keys(abcSet).sort();
    var catChips = '<button class="gl-chip cat' + (state.cat === 'all' ? ' on' : '') + '" data-cat="all">전체</button>';
    Object.keys(CATS).forEach(function (k) { catChips += '<button class="gl-chip cat' + (state.cat === k ? ' on' : '') + '" data-cat="' + k + '" style="--c:' + CATS[k].color + '">' + CATS[k].label + '</button>'; });
    var choChips = chip('전체', state.mode === 'all', 'data-mode="all"');
    CHO_LIST.forEach(function (c) { choChips += chip(c, state.mode === 'cho' && state.val === c, 'data-mode="cho" data-val="' + c + '"'); });
    var abcChips = ''; abcKeys.forEach(function (a) { abcChips += chip(a, state.mode === 'abc' && state.val === a, 'data-mode="abc" data-val="' + a + '"'); });
    return '<div class="gl-search"><input type="search" id="gl-q" placeholder="용어 검색 — 한글·영문·설명" value="' + esc(state.q) + '" autocomplete="off"></div>'
      + '<div class="gl-row"><span class="gl-row-lbl">카테고리</span>' + catChips + '</div>'
      + '<div class="gl-row"><span class="gl-row-lbl">가나다</span>' + choChips + '</div>'
      + '<div class="gl-row"><span class="gl-row-lbl">ABC</span>' + abcChips + '</div>';
  }

  function match(t) {
    var cho = chosung(t[0]), abc = abcLead(t[1]);
    if (state.cat !== 'all' && t[3] !== state.cat) return false;
    if (state.mode === 'cho' && cho !== state.val) return false;
    if (state.mode === 'abc' && abc !== state.val) return false;
    if (state.q) { var hay = (t[0] + ' ' + t[1] + ' ' + t[2]).toLowerCase(); if (hay.indexOf(state.q.toLowerCase()) < 0) return false; }
    return true;
  }

  function buildCards() {
    var list = TERMS.filter(match).sort(function (a, b) { return a[0].localeCompare(b[0], 'ko'); });
    if (!list.length) return '<p class="gl-empty">검색 결과가 없습니다. 다른 키워드로 찾아보세요.</p>';
    var cards = list.map(function (t) {
      var c = CATS[t[3]] || CATS.basic;
      return '<div class="gl-card">'
        + '<div class="gl-top"><span class="gl-term">' + esc(t[0]) + '</span><span class="gl-cat" style="--c:' + c.color + '">' + c.label + '</span></div>'
        + '<div class="gl-en">' + esc(t[1]) + '</div>'
        + '<p class="gl-def">' + esc(t[2]) + '</p></div>';
    }).join('');
    return '<div class="gl-count">' + list.length + '개 용어</div><div class="gl-grid">' + cards + '</div>';
  }

  function renderCards() { var c = rootEl.querySelector('#gl-cards'); if (c) c.innerHTML = buildCards(); }
  function renderAll() {
    rootEl.querySelector('#gl-controls').innerHTML = buildControls();
    renderCards();
    var q = rootEl.querySelector('#gl-q'); if (q) { q.focus(); try { q.setSelectionRange(q.value.length, q.value.length); } catch (e) {} }
  }

  function onClick(e) {
    var b = e.target.closest ? e.target.closest('.gl-chip') : null; if (!b) return;
    if (b.hasAttribute('data-cat')) { state.cat = b.getAttribute('data-cat'); }
    else { state.mode = b.getAttribute('data-mode'); state.val = b.getAttribute('data-val') || ''; }
    renderAll();
  }
  function onInput(e) { if (e.target && e.target.id === 'gl-q') { state.q = e.target.value; renderCards(); } }

  function mount(id) {
    rootEl = document.getElementById(id || 'glossary-root'); if (!rootEl) return;
    if (rootEl.getAttribute('data-mounted')) return;
    rootEl.setAttribute('data-mounted', '1');
    injectCSS();
    rootEl.innerHTML = '<div id="gl-controls"></div><div id="gl-cards"></div>';
    rootEl.querySelector('#gl-controls').innerHTML = buildControls();
    renderCards();
    rootEl.addEventListener('click', onClick);
    rootEl.addEventListener('input', onInput);
  }

  function injectCSS() {
    if (document.getElementById('gl-css')) return;
    var s = document.createElement('style'); s.id = 'gl-css';
    s.textContent = [
      '.gl-search input{width:100%;box-sizing:border-box;padding:14px 18px;border:1.5px solid var(--border,#e3e8ee);border-radius:12px;font-size:15px;font-family:inherit;margin-bottom:16px}',
      '.gl-search input:focus{outline:none;border-color:var(--p,#533afd)}',
      '.gl-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:10px}',
      '.gl-row-lbl{font-size:12px;font-weight:800;color:var(--mute,#64748d);width:56px;flex-shrink:0}',
      '.gl-chip{border:1px solid var(--border,#e3e8ee);background:#fff;color:#334155;border-radius:20px;padding:6px 13px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s}',
      '.gl-chip:hover{border-color:var(--p,#533afd);color:var(--p,#533afd)}',
      '.gl-chip.on{background:var(--p,#533afd);border-color:var(--p,#533afd);color:#fff}',
      '.gl-chip.cat.on{background:var(--c,#533afd);border-color:var(--c,#533afd)}',
      '.gl-count{margin:18px 2px 12px;font-size:13px;font-weight:700;color:var(--mute,#64748d)}',
      '.gl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}',
      '.gl-card{border:1px solid var(--border,#e3e8ee);border-radius:14px;padding:16px 18px;background:#fff;transition:.15s}',
      '.gl-card:hover{border-color:var(--p,#533afd);box-shadow:0 8px 22px -12px rgba(83,58,253,.35);transform:translateY(-2px)}',
      '.gl-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}',
      '.gl-term{font-size:16px;font-weight:800;color:var(--bd,#1c1e54);word-break:keep-all}',
      '.gl-cat{font-size:10.5px;font-weight:800;color:var(--c,#533afd);background:color-mix(in srgb,var(--c,#533afd) 12%,#fff);padding:3px 9px;border-radius:12px;white-space:nowrap;flex-shrink:0}',
      '.gl-en{font-size:12px;font-weight:700;color:var(--p,#533afd);margin:2px 0 8px}',
      '.gl-def{font-size:13.5px;line-height:1.65;color:var(--ink2,#475569);margin:0}',
      '.gl-empty{padding:40px;text-align:center;color:var(--mute,#64748d)}'
    ].join('');
    document.head.appendChild(s);
  }

  root.Glossary = { mount: mount, TERMS: TERMS, count: TERMS.length };
})(typeof window !== 'undefined' ? window : this);
