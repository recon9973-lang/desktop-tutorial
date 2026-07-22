/*!
 * VENOM SEO Engine — 독립 실행형 SEO 진단 엔진 (의존성 0)
 * 평가 기준(1차): Google Search Central(SEO 시작 가이드·helpful content·page experience)
 *               + Google PageSpeed Insights / Lighthouse(Core Web Vitals 공식 임계값)
 * 평가 기준(2차): 네이버 서치어드바이저 가이드
 * ※ 순위 보장 아님 — 1차 데이터는 Google Search Console 확인 권장
 *
 * 사용법 (브라우저):
 *   const result = SEOEngine.analyze({ url, html, robots, isHttps });
 *   document.getElementById('out').innerHTML = SEOEngine.renderInfographic(result);
 *   // 정밀(성능) 분석 후:
 *   const merged = SEOEngine.mergePSI(result, psiJson);
 *
 * 사용법 (Node + jsdom/linkedom):
 *   const { JSDOM } = require('jsdom');
 *   const doc = new JSDOM(html).window.document;
 *   const result = SEOEngine.analyze({ url, html, robots, isHttps, doc });
 *
 * 다른 사이트 재사용: 이 파일 하나만 복사하면 됩니다. 브랜드색은 renderInfographic의
 *   opts.brand 로 교체 (기본 #533afd).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SEOEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var VERSION = '1.8.0';
  // 배포 캐시버전(index.html의 seo-engine.js?v=와 동일하게 유지). 결과 푸터에 노출해
  // "새 엔진이 실제로 로드됐는지"를 사용자가 즉시 확인할 수 있게 한다(캐시 오인 방지).
  var BUILD = '2.1.7';

  // ── Core Web Vitals — Google 공식 임계값 (web.dev/vitals, PageSpeed Insights 기준) ──
  //   LCP: good ≤ 2.5s · needs-improvement ≤ 4.0s · poor > 4.0s   (초 단위)
  //   CLS: good ≤ 0.10 · needs-improvement ≤ 0.25 · poor > 0.25   (단위 없음)
  //   INP: good ≤ 200ms · needs-improvement ≤ 500ms · poor > 500ms (ms, 2024년 FID 대체)
  var CWV_THRESHOLDS = {
    LCP: { good: 2.5, ni: 4.0, unit: 's' },
    CLS: { good: 0.10, ni: 0.25, unit: '' },
    INP: { good: 200, ni: 500, unit: 'ms' }
  };
  // 측정값을 Google 공식 3구간(good / needs-improvement / poor)으로 분류. 값 없으면 'unknown'.
  function cwvClassify(metric, value) {
    var t = CWV_THRESHOLDS[String(metric || '').toUpperCase()];
    if (!t || value == null || isNaN(value)) return 'unknown';
    if (value <= t.good) return 'good';
    if (value <= t.ni) return 'needs-improvement';
    return 'poor';
  }

  // ── robots.txt 표준 파서 (RFC 9309) ─────────────────────────────
  // 지정 UA(또는 *)가 루트('/') 접근 가능한지. 충돌 시 least-restrictive(Allow 우선).
  function robotsAllows(robots, ua) {
    if (!robots || !robots.trim()) return true;
    ua = (ua || '*').toLowerCase();
    var lines = robots.split(/\r?\n/);
    var groups = [], cur = null, lastWasUA = false;
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].replace(/#.*$/, '').trim();
      if (!line) continue;
      var m = line.match(/^User-agent\s*:\s*(.+)$/i);
      if (m) {
        if (!lastWasUA || !cur) { cur = { agents: [], rules: [] }; groups.push(cur); }
        cur.agents.push(m[1].trim().toLowerCase());
        lastWasUA = true;
        continue;
      }
      lastWasUA = false;
      if (!cur) continue;
      var d = line.match(/^(Disallow|Allow)\s*:\s*(.*)$/i);
      if (d) cur.rules.push({ type: d[1].toLowerCase(), path: d[2].trim() });
    }
    function pick(name) {
      for (var g = 0; g < groups.length; g++) if (groups[g].agents.indexOf(name) >= 0) return groups[g];
      return null;
    }
    var grp = pick(ua) || pick('*');
    if (!grp) return true;
    var allowRoot = false, disRoot = false;
    for (var r = 0; r < grp.rules.length; r++) {
      var p = grp.rules[r].path;
      if (p === '/' || p === '/*' || p === '/$') {
        if (grp.rules[r].type === 'allow') allowRoot = true; else disRoot = true;
      }
    }
    return !(disRoot && !allowRoot);
  }

  function parseDoc(html, providedDoc) {
    if (providedDoc) return providedDoc;
    if (typeof DOMParser !== 'undefined') {
      try { return new DOMParser().parseFromString(html || '', 'text/html'); } catch (e) {}
    }
    return null;
  }

  // ── 핵심 분석 ───────────────────────────────────────────────────
  function analyze(input) {
    input = input || {};
    var url = input.url || '';
    var html = input.html || '';
    var robots = input.robots || '';
    var isHttps = (typeof input.isHttps === 'boolean') ? input.isHttps : /^https:/i.test(url);
    // 응답 헤더(보안·압축 신호). 키는 소문자. 없으면 빈 객체 → 관련 항목은 '정밀필요'로 낮춤.
    var H = input.headers || null;
    var hget = function (k) { return (H && H[k] != null) ? String(H[k]) : ''; };
    var doc = parseDoc(html, input.doc);
    var domain = url.replace(/^https?:\/\//i, '').split('/')[0] || url;

    function metaByName(name) {
      if (!doc) return '';
      var metas = doc.querySelectorAll('meta[name]');
      for (var i = 0; i < metas.length; i++)
        if ((metas[i].getAttribute('name') || '').toLowerCase() === name)
          return (metas[i].getAttribute('content') || '').trim();
      return '';
    }
    function metaByProp(prop) {
      if (!doc) return '';
      var metas = doc.querySelectorAll('meta[property]');
      for (var i = 0; i < metas.length; i++)
        if ((metas[i].getAttribute('property') || '').toLowerCase() === prop)
          return (metas[i].getAttribute('content') || '').trim();
      return '';
    }
    function q(sel, attr) {
      if (!doc) return '';
      var n = doc.querySelector(sel);
      return n ? (attr ? (n.getAttribute(attr) || '') : (n.textContent || '')) : '';
    }

    // 제목·디스크립션·H1 (네이버 가이드: 존재·단일·길이)
    var title = q('title').trim();
    var titleCount = doc ? (doc.head ? doc.head.querySelectorAll('title').length : doc.querySelectorAll('title').length) : 0;
    var titleLen = title.length;
    var titleLenBad = titleLen > 0 && (titleLen < 10 || titleLen > 60);
    var titlePass = !!title && titleCount <= 1 && !titleLenBad;
    var titleNote = !title ? 'title 태그 없음 — 추가 필요'
      : (titleCount > 1 ? '⚠ title 태그 ' + titleCount + '개 발견 — 페이지당 1개여야 함'
        : ('현재 ' + titleLen + '자' + (titleLen < 10 ? ' · 너무 짧음(권장 10~60)' : titleLen > 60 ? ' · 너무 김(권장 10~60, 검색결과 잘림)' : ' · 적정')));

    var metaDesc = metaByName('description');
    var descCount = doc ? doc.querySelectorAll('meta[name="description"],meta[name="Description"]').length : 0;
    var descLen = metaDesc.length;
    var descPass = !!metaDesc && descCount <= 1;
    var descNote = !metaDesc ? '메타 디스크립션 없음 — 검색 스니펫에 직접 영향'
      : (descCount > 1 ? '⚠ description 태그 ' + descCount + '개 — 페이지당 1개·고유하게'
        : ('현재 ' + descLen + '자' + (descLen < 50 ? ' · 너무 짧음(권장 50~160)' : descLen > 160 ? ' · 너무 김(권장 50~160)' : ' · 적정')));

    var h1Count = doc ? doc.querySelectorAll('h1').length : 0;
    var h1Pass = h1Count === 1;
    var h1Note = h1Count === 0 ? 'H1 없음 — 페이지 대표 제목 추가 필요'
      : h1Count > 1 ? ('⚠ H1 ' + h1Count + '개 발견 — 1개만 사용 권장(네이버)') : '대표 제목 1개 — 적정';

    // 이미지 ALT (속성 누락만 집계, alt=""·추적픽셀 제외, ≤10% 허용)
    var allImgs = doc ? Array.prototype.slice.call(doc.querySelectorAll('img')) : [];
    var imgs = allImgs.filter(function (im) {
      if (!im.getAttribute('src') && !im.getAttribute('data-src') && !im.getAttribute('srcset')) return false;
      var w = parseInt(im.getAttribute('width')), h = parseInt(im.getAttribute('height'));
      if ((w === 1 && h === 1) || w === 0 || h === 0) return false;
      return true;
    });
    var imgNoAlt = imgs.filter(function (im) { return im.getAttribute('alt') === null; }).length;
    var imgAltOk = imgs.length === 0 || (imgNoAlt / imgs.length) <= 0.1;
    var imgDesc = imgs.length > 0 ? (imgNoAlt === 0 ? '모든 이미지 alt 있음' : ('' + imgNoAlt + '/' + imgs.length + '개 alt 누락')) : '이미지 없음';

    // 의미있는 링크 텍스트 (Google: 서술형 앵커)
    var anchors = doc ? Array.prototype.slice.call(doc.querySelectorAll('a[href]')) : [];
    var realAnchors = anchors.filter(function (a) {
      var href = a.getAttribute('href') || '';
      if (!href || href.charAt(0) === '#' || /^(javascript:|mailto:|tel:)/i.test(href)) return false;
      return true;
    });
    var genericRe = /^(여기|여기클릭|클릭|클릭하세요|더보기|자세히|자세히보기|바로가기|링크|이동|here|click|clickhere|readmore|more|link|go)$/i;
    var badAnchors = realAnchors.filter(function (a) {
      if (a.querySelector('img')) return false;
      var t = (a.textContent || '').replace(/\s+/g, '').trim();
      if (!t) return true;
      return genericRe.test(t) || /^https?:\/\//i.test(t);
    });
    var linkTextOk = realAnchors.length === 0 || (badAnchors.length / realAnchors.length) <= 0.2;

    // 서술형 URL (Google URL 구조 가이드)
    var urlPath = '', urlSearch = '';
    try { var u = new URL(url); urlPath = decodeURIComponent(u.pathname); urlSearch = u.search; } catch (e) { urlPath = '/'; }
    var hasSession = /[?&](sessionid|sid|phpsessid|jsessionid)=/i.test(urlSearch);
    var isHome = (urlPath === '/' || urlPath === '');
    var urlOk = (isHome && !hasSession) ||
      (/[a-z가-힣]{2,}/i.test(urlPath) && !/\/\d{6,}(\/|$)/.test(urlPath) && !/[0-9a-f]{16,}/i.test(urlPath) && !hasSession);
    var urlNote = hasSession ? '세션ID 포함 — 쿠키 사용 권장(Google)'
      : isHome ? '홈 경로 — 적정' : urlOk ? '의미있는 단어 포함 — 적정' : '임의 ID/숫자 경로 — 서술형 단어·하이픈(-) 권장';

    // 기술·크롤링
    var hasViewport = !!metaByName('viewport');
    // favicon 실측: <link rel=icon> 태그 OR 실제 /favicon.ico(HTTP 200) 존재 → 거짓 음성 방지.
    var faviconStatus = (typeof input.faviconStatus === 'number') ? input.faviconStatus : null;
    var hasFaviconTag = !!(doc && doc.querySelector('link[rel~="icon"],link[rel="shortcut icon"],link[rel="apple-touch-icon"]'));
    var hasFavicon = hasFaviconTag || faviconStatus === 200;
    var canonical = q('link[rel="canonical"]', 'href');
    var lang = doc ? (doc.documentElement.getAttribute('lang') || '').trim() : '';
    var robotsMeta = (metaByName('robots') || metaByName('googlebot'));
    var notNoindex = !/noindex/i.test(robotsMeta);
    // robots.txt 유효성: 단순 '비어있지 않음'은 소프트 404(HTML을 200으로 주는 호스팅)를 오탐한다.
    // → ① HTTP 200 (상태코드 있으면), ② HTML이 아님, ③ 실제 지시어(user-agent/disallow/allow/sitemap) 포함.
    var robotsStatus = (typeof input.robotsStatus === 'number') ? input.robotsStatus : null;
    var _robotsBody = (robots || '').trim();
    var robotsIsHtml = /^<(?:!doctype|html|\?xml|head|body)/i.test(_robotsBody);
    var robotsHasDirective = /(^|\n)\s*(user-agent|disallow|allow|sitemap|crawl-delay)\s*:/i.test(_robotsBody);
    var robotsTxtOk = _robotsBody.length > 0 && !robotsIsHtml && robotsHasDirective
      && (robotsStatus === null || robotsStatus === 200);
    var robotsTxtNote = robotsTxtOk ? '크롤러 수집 규칙 파일 제공'
      : (robotsStatus && robotsStatus !== 200) ? ('robots.txt 없음 — HTTP ' + robotsStatus + ' 응답')
      : (robotsIsHtml || (!robotsHasDirective && _robotsBody.length > 0)) ? 'robots.txt 없음 — 페이지(HTML)가 대신 응답(소프트 404)'
      : 'robots.txt 없음 — /robots.txt 파일을 추가하세요';
    var crawlOk = robotsAllows(robots, 'Googlebot') && robotsAllows(robots, 'Yeti') && robotsAllows(robots, '*');

    // 검색 노출
    // 구조화 데이터: 단순 존재가 아니라 JSON-LD가 '파싱 가능'한지 검증(깨진 JSON 거짓 양성 방지).
    var _ldBlocks = html.match(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi) || [];
    var ldValid = false;
    for (var _lx = 0; _lx < _ldBlocks.length; _lx++) {
      try {
        var _inner = _ldBlocks[_lx].replace(/<script[^>]*>/i, '').replace(/<\/script>/i, '').trim();
        var _obj = JSON.parse(_inner);
        if (_obj && (typeof _obj === 'object')) { ldValid = true; break; }
      } catch (e) {}
    }
    var hasLd = ldValid; // 파싱 성공한 JSON-LD가 하나라도 있어야 통과
    var ldNote = _ldBlocks.length === 0 ? 'JSON-LD 없음 — Schema.org 구조화 데이터 추가 권장'
      : ldValid ? 'Schema.org JSON-LD — Google 페이지 이해·리치결과'
      : '⚠ JSON-LD ' + _ldBlocks.length + '개 발견됐지만 파싱 실패(문법 오류) — 검증 필요';
    var ogTitle = metaByProp('og:title'), ogDesc = metaByProp('og:description');
    var ogOk = !!ogTitle && !!ogDesc;
    // sitemap 실측: robots.txt 선언 OR 실제 /sitemap.xml(HTTP 200 + XML) 존재.
    var sitemapDeclared = /^\s*sitemap\s*:/im.test(robots);
    var sitemapStatus = (typeof input.sitemapStatus === 'number') ? input.sitemapStatus : null;
    var sitemapFileOk = sitemapStatus === 200 && input.sitemapIsXml === true;
    var hasSitemap = sitemapDeclared || sitemapFileOk;
    var sitemapNote = hasSitemap
      ? (sitemapFileOk && sitemapDeclared ? '/sitemap.xml 존재 + robots 선언 — 최적'
        : sitemapFileOk ? '/sitemap.xml 존재(200) — robots.txt에도 선언 권장'
        : 'robots.txt에 Sitemap 선언됨')
      : (sitemapStatus && sitemapStatus !== 200 ? ('sitemap.xml 없음 — /sitemap.xml HTTP ' + sitemapStatus)
        : 'sitemap.xml 없음 — 생성 후 robots.txt에 선언');


    // SPA 감지
    var bodyText = doc && doc.body ? doc.body.textContent.replace(/\s+/g, ' ').trim() : '';
    var scriptCount = doc ? doc.querySelectorAll('script[src]').length : 0;
    var isSPA = (bodyText.length < 150 && scriptCount >= 2 && !title && !h1Count) ||
      (doc && !!doc.querySelector('#root:empty,#app:empty,[data-reactroot]:empty'));

    // 정적 페치로 평가 불가한 'JS 렌더링/봇 차단' 정황 — 메타·구조화데이터를 JS로 주입하거나
    // 봇 차단(401/403)으로 빈 응답이 오면, 해당 신호를 '실패'가 아니라 '정밀필요(pending)'로 처리한다.
    // (정적 HTML에 이미 있으면 그대로 통과 — 거짓 통과는 만들지 않음)
    var renderSuspect = isSPA
      || (scriptCount >= 4 && !hasLd && !ogOk)          // JS 다수인데 구조화데이터·OG 둘 다 정적엔 없음
      || (titleCount === 0 && bodyText.length < 400);   // 제목 없고 본문 빈약 → 차단/미렌더 의심
    // JS로 흔히 주입되는 신호: 정적에 있으면 pass, 없으면 renderSuspect일 때 pending(null), 아니면 fail
    var jsItem = function (v) { return v === true ? true : (renderSuspect ? null : false); };

    // ── 보안 헤더 · 정적 속도 신호 (NXT 벤치마크 반영) ─────────────
    // 헤더(H)가 없으면(구버전 프록시·수집 실패) 해당 항목은 '정밀필요(null)'로 둔다(거짓 실패 방지).
    var hdrItem = function (v) { return H ? (v === true) : null; };
    var csp = hget('content-security-policy');
    var hasHsts = /max-age=\s*[1-9]/i.test(hget('strict-transport-security'));
    var hasNosniff = /nosniff/i.test(hget('x-content-type-options'));
    var hasFrameGuard = !!hget('x-frame-options') || /frame-ancestors/i.test(csp);
    var hasReferrer = !!hget('referrer-policy');
    var hasCSP = !!csp;
    var enc = hget('content-encoding').toLowerCase();
    var hasCompression = /gzip|br|deflate|zstd/.test(enc);
    // 정적 속도: 차세대 이미지(webp/avif)·이미지 지연로딩(loading="lazy")
    var imgTags = doc ? Array.prototype.slice.call(doc.querySelectorAll('img')) : [];
    var srcBlob = imgTags.map(function (im) { return (im.getAttribute('src') || '') + ' ' + (im.getAttribute('srcset') || '') + ' ' + (im.getAttribute('data-src') || ''); }).join(' ');
    // 실측 승격(#45): 실제 <img> src/srcset/data-src·<picture> source에 webp/avif가 있는지만 본다.
    // (과거 html 전체 정규식은 CSS·스크립트 문자열까지 걸려 오탐 → 실측으로 승격하며 제거)
    var usesNextGen = /\.(webp|avif)(\?|#|\s|$)/i.test(srcBlob) || !!(doc && doc.querySelector('picture source[type="image/webp"],picture source[type="image/avif"]'));
    var lazyImgs = imgTags.filter(function (im) { return (im.getAttribute('loading') || '').toLowerCase() === 'lazy'; }).length;
    var hasLazy = imgTags.length === 0 || (lazyImgs / imgTags.length) >= 0.5;
    var lazyNote = imgTags.length === 0 ? '이미지 없음' : (lazyImgs + '/' + imgTags.length + '개 지연로딩(loading="lazy")');
    // 이미지 최적화: 과다 개수·대용량 인라인(base64) 점검
    var bigInline = imgTags.filter(function (im) { var s = im.getAttribute('src') || ''; return s.indexOf('data:') === 0 && s.length > 30000; }).length;
    var imgOptOk = imgTags.length <= 50 && bigInline === 0;
    var imgOptNote = imgTags.length === 0 ? '이미지 없음' : (imgTags.length + '개' + (bigInline ? ' · 대용량 인라인 ' + bigInline + '개' : ''));

    // 페이지 핵심 키워드 시드 자동 추출(meta keywords·제목·H1 기반) → 클라이언트가 검색량 조회에 사용(NXT 벤치마크).
    // seeds[0]만 실제 조회에 쓰이므로 '지역+시술' 2-gram을 최우선으로 뽑는다(브랜드·문장·형용사 배제).
    var _metaKw = metaByName('keywords');
    var _h1txt = (doc && doc.querySelector('h1')) ? (doc.querySelector('h1').textContent || '').trim() : '';
    var _KWSTOP = /^(병원|의원|클리닉|치과|한의원|피부과|정형외과|성형외과|내과|안과|가정의학과|공식|공식홈페이지|홈페이지|home|소개|대표|원장|진료|안내|예약|상담|문의|오시는길|비용|가격|후기|추천|전문|전문의|잘하는|최고|국내|대한민국|믿을|나오나요|어때|어디|메인|main|blog|블로그|센터|의료원|마케팅|에이전시|no|the|and|for|of|www|com|net|kr)$/i;
    var _KWCITY = /(서울|부산|대구|인천|광주|대전|울산|세종|수원|성남|고양|용인|창원|청주|천안|전주|안산|안양|김해|포항|제주)/;
    var _kwRegion = function (w) { return _KWCITY.test(w) || /(역|구|동|시|군|읍|면)$/.test(w); };
    var _KWVERB = /(하는|나요|습니다|입니다|하세요|세요|해요|어요|아요|되는|있는|겠다|까요|였|더라|든지|하기|보기)$/;
    var _KWJOSA = /(으로|에서|에게|까지|부터|이나|을|를)$/; // 명사 끝(과·은·는·이·가·의·와·도·만·로)은 보존
    var _KWBRAND = /(의원|병원|한의원|의료원|메디컬|메디칼|센터)$/;
    function _kwClean(s) { return String(s || '').replace(/[|·•\-–—:_/()\[\]{}"'~!?,.]/g, ' ').replace(/\s+/g, ' ').trim(); }
    function _kwNorm(w) { return w.replace(_KWJOSA, ''); }
    function _kwIsNoun(w) {
      if (_KWVERB.test(w)) return false;           // 동사/형용사 어미는 원형에서 판정
      var n = _kwNorm(w);
      return n.length >= 2 && n.length <= 12 && /[가-힣A-Za-z]/.test(n) && !_KWSTOP.test(n) && !_KWBRAND.test(n) && !/^\d+$/.test(n);
    }
    var keywordSeeds = (function () {
      var out = [], seen = {};
      function add(s) { s = _kwClean(s); if (!s || seen[s] || s.length < 2 || s.length > 20) return; seen[s] = 1; out.push(s); }
      if (_metaKw) _metaKw.split(/[,|]/).slice(0, 4).forEach(function (k) { k = _kwClean(k); if (k && k.length <= 20 && !_KWSTOP.test(k)) add(k); });
      var h1c = _kwClean(_h1txt);
      var h1ok = h1c && h1c.split(' ').length <= 5 && !/나요|어때|어디|무엇|인가요|있나요/.test(h1c); // 문장형 H1은 노이즈 → 제외
      var src = _kwClean((title || '') + ' ' + (h1ok ? h1c : ''));
      var nouns = []; src.split(' ').forEach(function (w) { if (_kwIsNoun(w)) nouns.push(_kwNorm(w)); });
      for (var i = 0; i < nouns.length - 1 && out.length < 3; i++) if (_kwRegion(nouns[i])) add(nouns[i] + ' ' + nouns[i + 1]);
      for (var a = 0; a < nouns.length - 1 && out.length < 4; a++) add(nouns[a] + ' ' + nouns[a + 1]);
      for (var b = 0; b < nouns.length && out.length < 5; b++) if (!_kwRegion(nouns[b]) || nouns[b].length >= 4) add(nouns[b]);
      return out.slice(0, 4);
    })();

    // ── 신뢰·전문성(E-E-A-T) · 엔티티 신호 — 의료(YMYL) 가중 ─────────
    // 근거: [171]신뢰성 최우선·YMYL(건강) 가중 · [145]기사 author/datePublished/dateModified
    //       [185]Organization(sameAs·주소) · [121]LocalBusiness(주소·영업시간) · [39][1]생성형AI=기존SEO
    // 주의(공식 문서 반영): FAQ 리치결과 지원중단(2026)·llms.txt 불필요·"단어 수" 순위요인 아님 → SEO 점수 미채택.
    //   llms.txt·전화번호 구조화는 구글 순위 신호가 아니라 생성형 AI(GEO) 신호 → 'GEO 점수 진단' 도구에서만 채점한다.
    var ldText = '';
    try {
      var _ldN = doc ? doc.querySelectorAll('script[type="application/ld+json"]') : [];
      for (var _li = 0; _li < _ldN.length; _li++) ldText += ' ' + (_ldN[_li].textContent || '');
    } catch (e) {}
    if (!ldText && html) { var _ldM = html.match(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi); if (_ldM) ldText = _ldM.join(' '); }
    var bodyHead = bodyText.slice(0, 6000);
    // 실측(마크업)과 추정(본문 정규식)을 분리한다. 마크업 신호가 있으면 '실측 통과',
    // 마크업 없이 본문 단어만 걸리면 '추정 통과'로 표시(estXxx=true) — 정직성·오탐 구분(#45).
    var hasAuthorMarkup = !!metaByName('author')
      || /"author"\s*:/i.test(ldText)
      || (doc && !!doc.querySelector('[rel="author"],[itemprop="author"],[class*="author"],[class*="byline"],[class*="writer"]'));
    var hasAuthorText = /(작성자|글쓴이|감수|검수|대표원장|전문의|의료진|원장)/.test(bodyHead);
    var hasAuthor = hasAuthorMarkup || hasAuthorText;
    var authorEst = !hasAuthorMarkup && hasAuthorText;
    var hasDates = /"date(Published|Modified)"\s*:/i.test(ldText)
      || (doc && !!doc.querySelector('time[datetime],[itemprop="datePublished"],[itemprop="dateModified"]'))
      || !!metaByProp('article:published_time') || !!metaByProp('article:modified_time');
    // 실측: Organization류 JSON-LD 또는 사업자등록번호 패턴 / 추정: 본문의 상호·대표자 등 단어
    var hasOrgMarkup = /"@type"\s*:\s*"?(Organization|LocalBusiness|MedicalOrganization|MedicalClinic|Hospital|Dentist|Physician)"?/i.test(ldText)
      || /\d{3}-\d{2}-\d{5}/.test(bodyText);
    var hasOrgText = /(상호|대표자|사업자등록번호|의료기관)/.test(bodyHead);
    var hasOrg = hasOrgMarkup || hasOrgText;
    var orgEst = !hasOrgMarkup && hasOrgText;
    // 실측: tel: 링크 또는 JSON-LD의 schema.org telephone/address 속성 / 추정: 본문에 전화번호 형태 문자열
    var hasContactMarkup = (doc && !!doc.querySelector('a[href^="tel:"]'))
      || /"(telephone|address)"\s*:/i.test(ldText);
    var hasContactText = /0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}/.test(bodyText);
    var hasContact = hasContactMarkup || hasContactText;
    var contactEst = !hasContactMarkup && hasContactText;
    var extLinks = realAnchors.filter(function (a) {
      var h = a.getAttribute('href') || '';
      return /^https?:\/\//i.test(h) && h.indexOf(domain) === -1;
    }).length;
    // 실측: sameAs 구조화 신호 / 추정: 외부링크 2개 이상(엔티티 그라운딩 정황)
    var hasEntitySameAs = /"sameAs"\s*:/i.test(ldText);
    var hasEntity = hasEntitySameAs || extLinks >= 2;
    var entityEst = !hasEntitySameAs && extLinks >= 2;

    // ── 콘텐츠 최적화(작성 가이드) — 포커스 키워드 배치·구조·스캔성 ──
    // 근거: [89]서술형 제목·헤딩·사람중심 콘텐츠, [39]구조·스캔 가능성.
    // ※ 키워드 '밀도/스터핑'은 스팸 정책 위반([89][47])이라 미채택 — '배치(위치)'만 본다.
    var keyword = (input.keyword || '').trim().toLowerCase();
    var subHeads = doc ? Array.prototype.slice.call(doc.querySelectorAll('h2,h3')) : [];
    var subHeadText = subHeads.map(function (h) { return (h.textContent || ''); }).join(' ').toLowerCase();
    var firstParaEl = doc ? doc.querySelector('article p, main p, .content p, #content p, p') : null;
    var firstPara = firstParaEl ? (firstParaEl.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase() : '';
    var h1Low = (doc && doc.querySelector('h1')) ? (doc.querySelector('h1').textContent || '').toLowerCase() : '';
    var kwInTitle = !!keyword && title.toLowerCase().indexOf(keyword) >= 0;
    var kwInBody = !!keyword && (h1Low.indexOf(keyword) >= 0 || subHeadText.indexOf(keyword) >= 0 || firstPara.indexOf(keyword) >= 0);
    var kwInMeta = !!keyword && (metaDesc.toLowerCase().indexOf(keyword) >= 0 || urlPath.toLowerCase().indexOf(keyword) >= 0);
    var paras = doc ? Array.prototype.slice.call(doc.querySelectorAll('p')) : [];
    var longContent = bodyText.length >= 800;
    var hasSubheads = subHeads.length >= 2;
    var longParas = paras.filter(function (p) { return (p.textContent || '').replace(/\s+/g, ' ').trim().length > 500; }).length;
    var paraOk = paras.length === 0 || (longParas / Math.max(1, paras.length)) <= 0.3;
    var hasScan = doc ? (!!doc.querySelector('table') || doc.querySelectorAll('ul li, ol li').length >= 3) : false;

    // ── 배점(Google 우선순위 반영) ───────────────────────────────
    // Google Search Central(SEO 시작 가이드·helpful content·page experience)의 문서화된 우선순위에
    // 맞춰 배점: ①기술 기반(크롤/색인/모바일/HTTPS/canonical)과 ②핵심 콘텐츠 신호(title·description·
    // H1·alt·내부링크·URL)를 가장 무겁게, ③리치결과·공유용 '보너스' 신호는 낮게. 속도(CWV)는
    // 별도 게이지(PSI 실측)로 분리한다. 종합 배점 합계 = 100(콘텐츠42 + 기술42 + 검색16).
    var checks = {
      content: [
        ['제목(title) 태그', '검색결과 제목 — ' + titleNote, 12, jsItem(titlePass), 'Google'],
        ['메타 디스크립션', '검색결과 설명문 — ' + descNote, 8, jsItem(descPass), 'Google'],
        ['H1 대표 제목', h1Note, 6, jsItem(h1Pass), '공통'],
        ['이미지 ALT 텍스트', '이미지 대체 텍스트 (' + imgDesc + ')', 6, imgAltOk, 'Google'],
        ['의미있는 링크 텍스트', '서술형 앵커·내부링크 — "여기 클릭" 류 지양', 6, linkTextOk, 'Google'],
        ['서술형 URL', 'URL에 의미있는 단어 — ' + urlNote, 4, urlOk, 'Google']
      ],
      tech: [
        ['HTTPS 보안 연결', 'SSL 적용 — Google page experience 신뢰 신호', 8, isHttps, 'Google'],
        ['검색로봇 수집 허용', 'robots.txt가 Googlebot·Yeti 차단 안 함 — 크롤 가능성', 9, crawlOk, 'Google'],
        ['인덱싱 허용', 'meta robots noindex 미설정 — 색인 가능성', 8, notNoindex, 'Google'],
        ['Canonical 태그', '중복 URL 정규화 — 대표 주소 지정', 6, !!canonical, 'Google'],
        ['Viewport(모바일)', '모바일 반응형 메타 — 모바일 우선 인덱싱', 8, hasViewport, 'Google'],
        ['HTML lang 속성', '페이지 언어 명시 — 검색엔진 언어 인식', 3, !!lang, 'Google'],
        ['HTTP 압축', 'gzip/br 압축 — 전송량↓·로딩↑ (' + (enc || '미적용') + ')', 4, hdrItem(hasCompression), '공통'],
        ['차세대 이미지(WebP)', 'WebP/AVIF 사용 — 이미지 용량↓·속도↑', 3, jsItem(usesNextGen), 'Google'],
        ['이미지 지연로딩', 'loading="lazy" — 초기 로딩 속도 개선 (' + lazyNote + ')', 2, jsItem(hasLazy), 'Google'],
        ['이미지 최적화', '과다 이미지·대용량 인라인 점검 (' + imgOptNote + ')', 2, jsItem(imgOptOk), 'Google']
      ],
      // 검색 노출 강화 = 리치결과·공유 향상용 '보너스' 신호. 구조화 데이터는 Google이 페이지 이해·
      // 리치결과에 활용하므로 비중을 올리고(5), 나머지 공유·보조 신호는 낮게 유지한다.
      // (llms.txt·전화번호 구조화는 SEO 순위 신호가 아니라 GEO 신호 → 'GEO 점수 진단' 도구에서만 채점.)
      search: [
        ['구조화 데이터', ldNote, 5, jsItem(hasLd), 'Google'],
        ['Open Graph 태그', 'og:title·og:description — 공유 미리보기(보너스)', 2, jsItem(ogOk), '네이버'],
        ['sitemap.xml 선언', sitemapNote, 4, hasSitemap, '공통'],
        ['파비콘', '검색결과에 표시되는 사이트 아이콘', 2, hasFavicon, 'Google'],
        ['robots.txt 존재', robotsTxtNote, 3, robotsTxtOk, '공통']
      ],
      // 신뢰·전문성(E-E-A-T) = 의료(YMYL) 가중 신호. Google: E-E-A-T 중 '신뢰성'이 최우선이며
      // YMYL(건강)에 특히 가중([171]). 직접 순위요소는 아니나 병원 사이트엔 전환·품질 신뢰의 핵심.
      // 생성형 AI 노출도 기존 SEO+엔티티 신호로 충분([39][1]) — 별도 AEO 최적화 불필요.
      trust: [
        ['저자·의료진 정보', '작성자/감수 의료진·전문성 표기 — 의료(YMYL) 신뢰 신호 [171·145]', 5, jsItem(hasAuthor), 'Google', authorEst],
        ['조직·병원 정보', 'Organization/LocalBusiness 또는 상호·사업자번호 — 실체 신뢰 [185·121]', 4, jsItem(hasOrg), 'Google', orgEst],
        ['발행·수정일(최신성)', 'datePublished/dateModified·게시일 — 콘텐츠 최신성 [145]', 3, jsItem(hasDates), 'Google'],
        ['연락처·접근성', '전화(tel:)·주소 노출 — 신뢰·전환 [121]', 2, hasContact, '공통', contactEst],
        ['엔티티 신호(sameAs)', 'sameAs·권위있는 외부연결 — 생성형 AI/지식패널 그라운딩 [185·39]', 2, jsItem(hasEntity), 'Google', entityEst]
      ],
      // 콘텐츠 최적화(작성 가이드) = Rank Math류 '글 최적화'를 Google 근거로 안전하게 구현.
      // 포커스 키워드는 keyword 입력 시에만 '배치(위치)'를 평가(밀도/스터핑은 미채택). 구조·스캔성은 상시.
      writing: (keyword ? [
        ['포커스 키워드 — 제목', '"' + keyword + '" 제목 반영(자연스럽게, 스터핑 아님)', 3, jsItem(kwInTitle), 'Google'],
        ['포커스 키워드 — 본문·소제목', '"' + keyword + '" H1/소제목/첫 문단 반영', 3, jsItem(kwInBody), 'Google'],
        ['포커스 키워드 — 메타·URL', '"' + keyword + '" 메타 설명·URL 반영', 2, jsItem(kwInMeta), 'Google']
      ] : []).concat([
        ['소제목 구조', longContent ? (hasSubheads ? '긴 본문에 H2/H3 소제목 — 스캔 용이' : '긴 본문에 소제목 부족 — H2/H3 추가 권장') : '본문 분량 적정(소제목 선택)', 3, longContent ? jsItem(hasSubheads) : true, 'Google', '추정 기준'],
        ['문단 가독성', '지나치게 긴 문단 없음 — 스캔 가능성', 2, jsItem(paraOk), 'Google', '추정 기준'],
        ['스캔 구조(목록·표)', '목록·표로 정보 구조화 — AI/사용자 스캔', 2, jsItem(hasScan), 'Google', '추정 기준']
      ]),
      // 보안(응답 헤더) = NXT 벤치마크. 방문자 신뢰·클릭재킹/스니핑 방어. 헤더 미수집 시 정밀필요.
      security: [
        ['HTTPS 보안 연결', 'SSL 적용 — 전송 구간 암호화(신뢰 기본)', 4, isHttps, '공통'],
        ['HSTS 적용', 'Strict-Transport-Security — HTTPS 강제(다운그레이드 공격 방어)', 3, hdrItem(hasHsts), '공통'],
        ['콘텐츠 스니핑 차단', 'X-Content-Type-Options: nosniff — MIME 스니핑 방어', 3, hdrItem(hasNosniff), '공통'],
        ['클릭재킹 차단', 'X-Frame-Options 또는 CSP frame-ancestors — iframe 삽입 방어', 3, hdrItem(hasFrameGuard), '공통'],
        ['Referrer 정책', 'Referrer-Policy — 외부 이동 시 참조정보 제어', 2, hdrItem(hasReferrer), '공통'],
        ['콘텐츠 보안 정책(CSP)', 'Content-Security-Policy — XSS·주입 방어(보너스)', 2, hdrItem(hasCSP), '공통']
      ],
      // 속도(Core Web Vitals) = Google PageSpeed Insights / Lighthouse 실측 전용. PSI 없이는
      // 절대 점수를 만들지 않고 pending(정밀 필요) 유지. 배점 합계 10(성능4·LCP3·CLS2·INP1).
      speed: [
        ['성능 점수(Lighthouse)', 'Google Lighthouse 성능 — 정밀 분석(PSI) 시 측정', 4, null, 'Google'],
        ['LCP · 최대 콘텐츠 렌더', 'Google 기준 ≤2.5s 양호 — PSI 현장데이터 측정', 3, null, 'Google'],
        ['CLS · 누적 레이아웃 이동', 'Google 기준 ≤0.10 양호 — PSI 측정', 2, null, 'Google'],
        ['INP · 상호작용 반응성', 'Google 기준 ≤200ms 양호(2024 FID 대체) — PSI 측정', 1, null, 'Google']
      ]
    };

    var _res = buildResult(url, domain, isHttps, isSPA, checks, null);
    _res.renderSuspect = renderSuspect;
    _res.keywordSeeds = keywordSeeds;
    return _res;
  }

  // 종합 100점 = 6개 테마 가중치 합(속도는 별도 +α 게이지, 종합 미포함).
  // 배점 근거: Google Search Central 우선순위 — 핵심 콘텐츠 신호·기술기반을 가장 무겁게,
  // E-E-A-T(의료 YMYL) 가중, 리치결과·보안은 보조. weight 합 = 100.
  var CAT_DEF = [
    { key: 'content', label: '콘텐츠 & 메타', icon: '📝', color: '#533afd', weight: 28 },
    { key: 'tech', label: '기술·크롤링', icon: '⚙️', color: '#06b6d4', weight: 26 },
    { key: 'trust', label: '신뢰·전문성(E-E-A-T)', icon: '🩺', color: '#10b981', weight: 14 },
    { key: 'search', label: '검색 노출 강화', icon: '🔍', color: '#8b5cf6', weight: 12 },
    { key: 'writing', label: '콘텐츠 최적화', icon: '✍️', color: '#f43f5e', weight: 10 },
    { key: 'security', label: '보안(응답 헤더)', icon: '🔒', color: '#0ea5e9', weight: 10 },
    { key: 'speed', label: '속도(CWV) · +α', icon: '⚡', color: '#f59e0b', weight: 0 }
  ];

  // 실패(미충족) 항목에 보여줄 '바로 붙여넣는' 수정 코드 스니펫. 검사 항목명(it[0])이 키.
  // <head> 삽입/robots.txt/본문 예시를 그대로 복사할 수 있게 최소·정확하게 유지한다.
  var FIX = {
    '제목(title) 태그': '<!-- <head> 안, 페이지당 1개 · 10~60자 -->\n<title>병원명 · 지역 · 진료과목 핵심키워드</title>',
    '메타 디스크립션': '<!-- <head> 안 · 50~160자 · 페이지마다 고유 -->\n<meta name="description" content="지역 진료과목 병원 소개 — 핵심 진료·특장점을 한 문장으로 요약">',
    'H1 대표 제목': '<!-- 페이지 대표 제목, 페이지당 1개만 -->\n<h1>지역 진료과목 — 병원명</h1>',
    '이미지 ALT 텍스트': '<!-- 모든 의미있는 이미지에 alt -->\n<img src="clinic.jpg" alt="OO병원 임플란트 상담 장면">',
    '의미있는 링크 텍스트': '<!-- "여기 클릭"·"더보기" 대신 서술형 -->\n<a href="/implant">임플란트 진료 안내 보기</a>',
    '서술형 URL': '좋음: /implant-consult\n피함: /page?id=12983  (임의 숫자·세션ID)',
    'HTTPS 보안 연결': '# http → https 301 리다이렉트 + SSL 인증서 적용\n# (호스팅/CDN에서 강제 HTTPS 켜기)',
    '검색로봇 수집 허용': '# robots.txt — Googlebot·Yeti(네이버) 차단 금지\nUser-agent: *\nAllow: /',
    '인덱싱 허용': '<!-- noindex 제거 또는 index로 -->\n<meta name="robots" content="index, follow">',
    'Canonical 태그': '<!-- <head> 안, 이 페이지의 대표 주소 -->\n<link rel="canonical" href="https://도메인/현재-경로">',
    'Viewport(모바일)': '<!-- <head> 최상단 -->\n<meta name="viewport" content="width=device-width, initial-scale=1">',
    'HTML lang 속성': '<html lang="ko">',
    '구조화 데이터': '<script type="application/ld+json">\n{\n  "@context":"https://schema.org",\n  "@type":"MedicalClinic",\n  "name":"OO병원",\n  "address":"서울시 ...",\n  "telephone":"02-123-4567"\n}\n</script>',
    'Open Graph 태그': '<meta property="og:title" content="OO병원 — 지역 진료과목">\n<meta property="og:description" content="핵심 진료 소개">\n<meta property="og:image" content="https://도메인/og.jpg">',
    'sitemap.xml 선언': '# robots.txt 마지막 줄\nSitemap: https://도메인/sitemap.xml',
    '파비콘': '<link rel="icon" href="/favicon.ico">',
    'robots.txt 존재': '# /robots.txt 파일 생성\nUser-agent: *\nAllow: /\nSitemap: https://도메인/sitemap.xml',
    '저자·의료진 정보': '<!-- 작성/감수 의료진 명시 (YMYL 신뢰) -->\n<p class="byline">감수: OOO 대표원장 · OO과 전문의</p>',
    '조직·병원 정보': '<script type="application/ld+json">\n{"@context":"https://schema.org","@type":"Organization",\n "name":"OO병원","url":"https://도메인","telephone":"02-123-4567"}\n</script>',
    '발행·수정일(최신성)': '<time datetime="2026-07-20">2026년 7월 20일 게시</time>\n<!-- 또는 JSON-LD datePublished / dateModified -->',
    '연락처·접근성': '<a href="tel:0212345678">02-1234-5678</a>\n<address>서울시 OO구 OO로 00</address>',
    '엔티티 신호(sameAs)': '<!-- Organization JSON-LD 안 -->\n"sameAs":["https://blog.naver.com/OO","https://www.instagram.com/OO"]',
    '소제목 구조': '<h2>진료 안내</h2>\n<h3>임플란트</h3>\n<!-- 긴 본문은 H2/H3로 구획 -->',
    '문단 가독성': '<!-- 500자 넘는 문단은 2~3개로 분할, 핵심은 목록으로 -->',
    '스캔 구조(목록·표)': '<ul>\n  <li>진료시간 안내</li>\n  <li>비급여 항목 안내</li>\n</ul>',
    'HSTS 적용': '# 응답 헤더(서버·CDN 설정)\nStrict-Transport-Security: max-age=31536000; includeSubDomains',
    '콘텐츠 스니핑 차단': '# 응답 헤더\nX-Content-Type-Options: nosniff',
    '클릭재킹 차단': '# 응답 헤더 (둘 중 하나)\nX-Frame-Options: SAMEORIGIN\n# 또는 CSP: frame-ancestors \'self\'',
    'Referrer 정책': '# 응답 헤더\nReferrer-Policy: strict-origin-when-cross-origin',
    '콘텐츠 보안 정책(CSP)': "# 응답 헤더 (예시 — 사이트에 맞게 조정)\nContent-Security-Policy: default-src 'self'; img-src 'self' data: https:",
    'HTTP 압축': '# 서버/CDN에서 gzip 또는 brotli 압축 켜기\n# Nginx: gzip on;  ·  Vercel/Cloudflare: 기본 제공',
    '차세대 이미지(WebP)': '<picture>\n  <source srcset="img.webp" type="image/webp">\n  <img src="img.jpg" alt="설명">\n</picture>',
    '이미지 지연로딩': '<img src="img.webp" alt="설명" loading="lazy">',
    '이미지 최적화': '<!-- 대용량 인라인(data:base64)은 외부 파일로, 이미지 수는 필요한 만큼만 -->\n<img src="/img/photo.webp" alt="설명" loading="lazy" width="800" height="600">'
  };
  var fixFor = function (name) {
    if (FIX[name]) return FIX[name];
    if (/포커스 키워드/.test(name)) return '<!-- 타깃 키워드를 제목·H1·첫 문단·메타에 자연스럽게 1~2회 -->';
    return '';
  };

  function gradeFor(total, max) {
    var pct = max ? total / max : 0;
    if (pct >= 0.9) return { label: '플래티넘', color: '#7c3aed', desc: '최상위 SEO' };
    if (pct >= 0.8) return { label: '골드', color: '#d97706', desc: '상위 20%' };
    if (pct >= 0.7) return { label: '실버', color: '#64748b', desc: '개선 중' };
    if (pct >= 0.6) return { label: '브론즈', color: '#b45309', desc: '보통' };
    return { label: '개선필요', color: '#dc2626', desc: '즉시 조치 필요' };
  }

  function buildResult(url, domain, isHttps, isSPA, checks, psi) {
    // 각 테마 기여 = 가중치 × (통과 배점 / 테마 전체 배점).
    // '확인 필요(pending)' 항목은 아직 입증 안 된 점수이므로 분모(전체 배점)에 남겨 0점으로 반영하되,
    // 실패로 단정하지 않고 정밀분석(PSI)·수정으로 회복 가능하게 둔다(정직 + 오탐 방지 균형).
    var categories = CAT_DEF.map(function (cat) {
      var items = checks[cat.key].map(function (it) {
        return { name: it[0], desc: it[1], points: it[2], pass: it[3], source: it[4], est: it[5] || false, fix: fixFor(it[0]) };
      });
      var rawMax = items.reduce(function (s, it) { return s + it.points; }, 0);
      var earned = items.reduce(function (s, it) { return s + (it.pass === true ? it.points : 0); }, 0);
      var pendingPoints = items.reduce(function (s, it) { return s + (it.pass === null ? it.points : 0); }, 0);
      var pendingCount = items.filter(function (it) { return it.pass === null; }).length;
      var pendingFlag = pendingCount > 0;
      var w = cat.weight || 0;
      var ratio = rawMax ? (earned / rawMax) : 0;               // 0..1 (pending은 미획득)
      var pct = Math.round(ratio * 100);                        // 테마 달성률 %
      // '확인 필요' 배점이 전체에서 차지하는 비율 — 막대에 별도 구간으로 표시(회복 가능분).
      var pendPct = rawMax ? Math.round(pendingPoints / rawMax * 100) : 0;
      var isSpeed = (cat.key === 'speed');
      var dispScore = isSpeed ? earned : +(w * ratio).toFixed(1);
      var dispMax = isSpeed ? rawMax : w;
      return {
        key: cat.key, label: cat.label, icon: cat.icon, color: cat.color, weight: w,
        score: dispScore, max: dispMax, pct: pct, pendPct: pendPct,
        pending: pendingFlag, pendingCount: pendingCount,
        rawEarned: earned, rawMax: rawMax, items: items
      };
    });

    // 종합 100점 = 속도 제외한 6개 테마 가중점수의 합(가중치 합 = 100 → 항상 0~100).
    var headline = categories.filter(function (c) { return c.key !== 'speed'; });
    var total = Math.round(headline.reduce(function (s, c) { return s + c.score; }, 0));
    var max = 100;
    var improvable = Math.max(0, 100 - total);                  // 100까지 회복 가능한 점수
    var speedCat = categories.filter(function (c) { return c.key === 'speed'; })[0] || null;
    // 추정(정황) 기반 항목이 하나라도 있으면 UI에 범례를 노출한다(#45).
    var hasEstimated = categories.some(function (c) { return c.items.some(function (it) { return !!it.est; }); });

    // 항목 단위 집계(통과/미흡/확인필요·통과율)
    var passed = 0, failed = 0, pending = 0;
    categories.forEach(function (c) {
      c.items.forEach(function (it) {
        if (it.pass === null) pending++;
        else if (it.pass) passed++;
        else failed++;
      });
    });
    var rated = passed + failed;
    var summary = {
      passed: passed, failed: failed, pending: pending,
      totalItems: passed + failed + pending,
      passRate: rated ? Math.round(passed / rated * 100) : 0,
      improvable: improvable
    };
    return {
      version: VERSION, url: url, domain: domain, isHttps: isHttps, isSPA: isSPA,
      categories: categories, baseTotal: total, baseMax: 100, speedCat: speedCat,
      total: total, max: max, hasPSI: !!psi, psi: psi || null,
      hasEstimated: hasEstimated,
      summary: summary, grade: gradeFor(total, max)
    };
  }

  // ── PSI(Lighthouse) 결과 병합 → 속도 항목 채점 + 종합점수 갱신 ──
  function mergePSI(result, psiJson) {
    var audits = (psiJson.lighthouseResult && psiJson.lighthouseResult.audits) || {};
    var cats = (psiJson.lighthouseResult && psiJson.lighthouseResult.categories) || {};
    function pass(id) { var a = audits[id]; return !!(a && (a.score === 1 || a.score === null)); }
    function labNum(id) { var a = audits[id]; return (a && typeof a.numericValue === 'number') ? a.numericValue : null; }
    var perf = Math.round((cats.performance ? cats.performance.score : 0) * 100);

    // Core Web Vitals — CrUX 현장데이터 우선, 없으면 Lighthouse 랩(lab) 값으로 보정.
    var le = psiJson.loadingExperience, ole = psiJson.originLoadingExperience;
    var crux = null, src = (le && le.metrics) ? le : (ole && ole.metrics) ? ole : null;
    if (src) {
      var lcp = src.metrics.LARGEST_CONTENTFUL_PAINT_MS,
          cls = src.metrics.CUMULATIVE_LAYOUT_SHIFT_SCORE,
          inp = src.metrics.INTERACTION_TO_NEXT_PAINT;
      var lcpSecF = lcp ? +(lcp.percentile / 1000).toFixed(2) : null;   // ms → s
      var clsValF = cls ? +(cls.percentile / 100).toFixed(3) : null;    // CrUX는 ×100
      var inpMsF = inp ? inp.percentile : null;                          // ms
      crux = {
        origin: !(le && le.metrics),
        // 카테고리는 Google 공식 임계값(cwvClassify)으로 직접 산출 — good/needs-improvement/poor
        lcp: lcpSecF != null ? { sec: lcpSecF, cat: cwvClassify('LCP', lcpSecF) } : null,
        cls: clsValF != null ? { val: clsValF, cat: cwvClassify('CLS', clsValF) } : null,
        inp: inpMsF != null ? { ms: inpMsF, cat: cwvClassify('INP', inpMsF) } : null,
        overall: src.overall_category || ''
      };
    }
    // CWV 채점값(현장 → 랩 폴백). good만 통과(true), ni/poor는 미흡(false), 값 자체 없으면 랩 프록시.
    var lcpSec = (crux && crux.lcp) ? crux.lcp.sec : (labNum('largest-contentful-paint') != null ? +(labNum('largest-contentful-paint') / 1000).toFixed(2) : null);
    var clsVal = (crux && crux.cls) ? crux.cls.val : (labNum('cumulative-layout-shift') != null ? +labNum('cumulative-layout-shift').toFixed(3) : null);
    var inpMs = (crux && crux.inp) ? crux.inp.ms : null;
    var lcpCat = cwvClassify('LCP', lcpSec), clsCat = cwvClassify('CLS', clsVal), inpCat = cwvClassify('INP', inpMs);
    function cwvPass(cat) { return cat === 'good' ? true : (cat === 'unknown' ? null : false); }
    // INP는 CrUX 현장데이터에만 존재 — 없으면 Lighthouse 랩 프록시(TBT: Total Blocking Time)로 대체.
    var tbt = audits['total-blocking-time'];
    var inpPass = (inpMs != null) ? cwvPass(inpCat) : (tbt ? (tbt.score != null ? tbt.score >= 0.9 : null) : null);
    var lcpNote = lcpSec != null ? ('현재 ' + lcpSec + 's (' + lcpCat + ')') : '데이터 없음';
    var clsNote = clsVal != null ? ('현재 ' + clsVal + ' (' + clsCat + ')') : '데이터 없음';
    var inpNote = inpMs != null ? ('현재 ' + inpMs + 'ms (' + inpCat + ')') : (tbt ? 'CrUX 현장데이터 없음 · 랩(TBT) 프록시' : '데이터 없음');
    var speedItems = [
      ['성능 점수(Lighthouse)', 'Google Lighthouse 성능: ' + perf + '/100 (≥90 통과)', 4, perf >= 90, 'Google'],
      ['LCP · 최대 콘텐츠 렌더', 'Google 기준 ≤2.5s 양호 — ' + lcpNote, 3, cwvPass(lcpCat), 'Google'],
      ['CLS · 누적 레이아웃 이동', 'Google 기준 ≤0.10 양호 — ' + clsNote, 2, cwvPass(clsCat), 'Google'],
      ['INP · 상호작용 반응성', 'Google 기준 ≤200ms 양호(2024 FID 대체) — ' + inpNote, 1, inpPass, 'Google']
    ];
    // PSI(Lighthouse)는 실제 브라우저로 렌더링하므로, 정적 수집이 놓친 항목을 렌더링 기준으로 보정한다.
    // (경쟁사 NXT가 높은 점수를 주는 이유 = JS 렌더 후 평가. score===1 통과, 0 실패, 그 외=정적 유지)
    function seoAudit(id) { var a = audits[id]; if (!a) return undefined; return a.score === 1 ? true : (a.score === 0 ? false : undefined); }
    var psiByName = {
      '제목(title) 태그': seoAudit('document-title'),
      '메타 디스크립션': seoAudit('meta-description'),
      '이미지 ALT 텍스트': seoAudit('image-alt'),
      '의미있는 링크 텍스트': seoAudit('link-text'),
      '인덱싱 허용': seoAudit('is-crawlable'),
      'robots.txt 존재': seoAudit('robots-txt'),
      'Canonical 태그': seoAudit('canonical'),
      'Viewport(모바일)': seoAudit('viewport')
    };
    var checks = {};
    result.categories.forEach(function (c) {
      if (c.key === 'speed') { checks.speed = speedItems; return; }
      checks[c.key] = c.items.map(function (it) {
        var pv = psiByName[it.name];
        var finalPass = (pv !== undefined) ? pv : it.pass;   // PSI 렌더 결과 우선, 없으면 정적값
        return [it.name, it.desc, it.points, finalPass, it.source];
      });
    });
    var _mergedRes = buildResult(result.url, result.domain, result.isHttps, result.isSPA, checks, {
      // 요청하지 않은 카테고리는 null → 게이지에 '—'로 표시(0점 오해 방지).
      seo: cats.seo ? Math.round(cats.seo.score * 100) : null,
      perf: perf,
      accessibility: cats.accessibility ? Math.round(cats.accessibility.score * 100) : null,
      bestPractices: cats['best-practices'] ? Math.round(cats['best-practices'].score * 100) : null,
      crux: crux
    });
    _mergedRes.keywordSeeds = result.keywordSeeds; // 키워드 시드 유지(PSI 병합 후에도)
    return _mergedRes;
  }

  // ── 인포그래픽 (SVG, 의존성 0) ─────────────────────────────────
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function srcColor(s) { return s === 'Google' ? '#4285F4' : s === '네이버' ? '#03C75A' : '#94a3b8'; }

  function donut(score, max, color, sub) {
    var r = 54, c = 2 * Math.PI * r, pct = max ? Math.max(0, Math.min(1, score / max)) : 0;
    var off = c * (1 - pct);
    return '<svg viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="SEO 점수 ' + score + '점">' +
      '<circle cx="70" cy="70" r="' + r + '" fill="none" stroke="#eef0f5" stroke-width="14"/>' +
      '<circle cx="70" cy="70" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="14" stroke-linecap="round" ' +
      'stroke-dasharray="' + c.toFixed(1) + '" stroke-dashoffset="' + off.toFixed(1) + '" transform="rotate(-90 70 70)" ' +
      'style="transition:stroke-dashoffset 1s ease"/>' +
      '<text x="70" y="66" text-anchor="middle" font-size="34" font-weight="800" fill="' + color + '">' + score + '</text>' +
      '<text x="70" y="88" text-anchor="middle" font-size="12" fill="#64748b">/ ' + max + '점</text>' +
      (sub ? '<text x="70" y="104" text-anchor="middle" font-size="11" font-weight="700" fill="' + color + '">' + esc(sub) + '</text>' : '') +
      '</svg>';
  }

  // 막대 = 통과분(진한 색) + 확인 필요분(빗금 앰버) + 미흡분(회색). 확인 필요가 있어도
  // 이미 획득한 점수만큼은 반드시 채워 보여준다(예: 6.7/28 → 24% 채움). 오른쪽엔 배점·확인건수.
  function bar(c) {
    var earnedPct = c.max ? Math.round(c.score / c.max * 100) : 0;
    var pendPct = c.pendPct || 0;
    if (earnedPct + pendPct > 100) pendPct = Math.max(0, 100 - earnedPct); // 반올림 오버플로 방지
    var pendSeg = pendPct > 0
      ? '<span title="확인 필요 — 정밀분석(PSI)에서 인정 가능" style="height:100%;width:' + pendPct +
        '%;background:repeating-linear-gradient(45deg,#fcd34d,#fcd34d 4px,#fef3c7 4px,#fef3c7 8px)"></span>'
      : '';
    var pendTag = c.pendingCount
      ? '<span style="color:#b45309;font-weight:800"> · 확인 ' + c.pendingCount + '</span>' : '';
    return '<div style="display:flex;align-items:center;gap:11px;margin:9px 0;font-size:14px">' +
      '<span style="width:132px;flex-shrink:0;color:#1e293b;font-weight:700">' + esc(c.label) + '</span>' +
      '<span style="flex:1;height:11px;background:#eaeef3;border-radius:9px;overflow:hidden;display:flex">' +
      '<span style="height:100%;width:' + earnedPct + '%;background:' + c.color + ';transition:width .8s ease"></span>' +
      pendSeg + '</span>' +
      '<span style="width:88px;text-align:right;font-weight:800;font-size:13.5px;color:' + c.color + '">' +
      c.score + '/' + c.max + pendTag + '</span></div>';
  }

  function renderInfographic(result, opts) {
    opts = opts || {};
    var brand = opts.brand || '#533afd';
    var g = result.grade;
    var gauge = donut(result.total, result.max, g.color, g.label);
    var bars = result.categories.filter(function (c) { return c.key !== 'speed'; })
      .map(function (c) { return bar(c); }).join('');
    // 속도(성능)는 종합점수와 분리된 별도 게이지 — Google 성능 점수와 동일 위상
    var sc = result.speedCat;
    var speedGauge = '';
    if (sc && !sc.pending) {
      var sCol = sc.pct >= 70 ? '#16a34a' : sc.pct >= 40 ? '#d97706' : '#dc2626';
      speedGauge = '<div style="flex-shrink:0;text-align:center">' +
        donut(sc.score, sc.max, sCol, sc.pct + '%') +
        '<div style="font-size:13px;font-weight:700;color:' + sCol + ';margin-top:2px">⚡ 속도(성능)</div>' +
        '<div style="font-size:11px;color:#94a3b8">종합점수와 별도 · Google 기준</div></div>';
    }

    // 등급 스케일
    var pct = result.max ? result.total / result.max : 0;
    var tiers = [['90~100', '플래티넘', .9, 1, '#7c3aed'], ['80~89', '골드', .8, .9, '#d97706'],
      ['70~79', '실버', .7, .8, '#64748b'], ['60~69', '브론즈', .6, .7, '#b45309'], ['0~59', '개선필요', 0, .6, '#dc2626']];
    var scale = tiers.map(function (t) {
      var cur = pct >= t[2] && pct < t[3] + (t[3] === 1 ? 0.01 : 0);
      return '<span style="flex:1;text-align:center;font-size:10px;padding:6px 2px;border-radius:6px;line-height:1.4;' +
        (cur ? 'background:' + t[4] + ';color:#fff;font-weight:700' : 'background:#f4f6fa;color:#94a3b8') + '">' +
        t[0] + '<br>' + t[1] + '</span>';
    }).join('');

    var psiBadges = '';
    if (result.psi) {
      var p = result.psi;
      // 값이 null(미요청 카테고리)이면 '—'로 표시하고 회색 처리.
      var b = function (lbl, v, col) {
        var has = (v !== null && v !== undefined);
        return '<span style="background:#f4f6fa;border-radius:8px;padding:8px 12px;font-size:12px">' + lbl +
          ' <strong style="color:' + (has ? col : '#9ca3af') + '">' + (has ? v : '—') + '</strong></span>';
      };
      psiBadges = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">' +
        b('SEO', p.seo, '#4285F4') + b('성능', p.perf, p.perf >= 90 ? '#16a34a' : p.perf >= 50 ? '#d97706' : '#dc2626') +
        b('접근성', p.accessibility, '#06b6d4') + b('권장사항', p.bestPractices, '#8b5cf6') + '</div>';
      if (p.crux) {
        var cx = p.crux;
        psiBadges += '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:12px 14px;margin-top:10px;font-size:12px;color:#166534">' +
          '📊 실제 사용자 현장 데이터(CrUX' + (cx.origin ? ' · 도메인 누적' : '') + ') · Google 공식 임계값 ' +
          (cx.lcp ? 'LCP <strong>' + cx.lcp.sec + 's (' + cx.lcp.cat + ')</strong> ' : '') +
          (cx.cls ? '· CLS <strong>' + cx.cls.val + ' (' + cx.cls.cat + ')</strong> ' : '') +
          (cx.inp ? '· INP <strong>' + cx.inp.ms + 'ms (' + cx.inp.cat + ')</strong>' : '') + '</div>';
      }
    }

    // 집계 수치 스트립 — 각 수치에 '기준(최대치·분모)'을 함께 표기해 맥락 없이 숫자만 뜨지 않게 한다.
    var sm = result.summary || { passed: 0, failed: 0, pending: 0, totalItems: 0, passRate: 0, improvable: 0 };
    var rated = sm.passed + sm.failed;                          // 판정된 항목(확인 필요 제외)
    var stat = function (v, l, sub, col) {
      return '<div style="flex:1;min-width:112px;text-align:center;background:#f8fafc;border:1px solid #e8ecf1;border-radius:12px;padding:13px 8px">' +
        '<div style="font-size:26px;font-weight:900;color:' + col + ';line-height:1.1">' + v + '</div>' +
        '<div style="font-size:12.5px;color:#334155;font-weight:700;margin-top:5px">' + l + '</div>' +
        '<div style="font-size:11px;color:#94a3b8;font-weight:600;margin-top:2px">' + sub + '</div></div>';
    };
    var statsStrip = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">' +
      stat(sm.passed, '통과 항목', '전체 ' + sm.totalItems + '개 중', '#16a34a') +
      stat(sm.failed, '미흡 항목', '확인 필요 ' + sm.pending + '건 별도', '#dc2626') +
      stat(result.total + '<span style="font-size:15px;color:#94a3b8">/100</span>', '현재 종합점수', '개선 시 +' + sm.improvable + ' → 100점', brand) +
      stat(sm.passRate + '%', '통과율', '통과 ' + sm.passed + ' / 판정 ' + rated + '건', '#0ea5e9') + '</div>';
    // 카테고리 요약 테이블
    var tableRows = result.categories.map(function (c) {
      var passN = c.items.filter(function (it) { return it.pass === true; }).length;
      var pendMark = c.pendingCount ? ' <span style="color:#b45309;font-weight:700">·확인' + c.pendingCount + '</span>' : '';
      return '<tr><td style="padding:11px 12px;border-top:1px solid #eef1f5;font-size:14px;font-weight:600;color:#1e293b">' + c.icon + ' ' + esc(c.label) + '</td>' +
        '<td style="padding:11px 12px;border-top:1px solid #eef1f5;text-align:center;color:' + c.color + ';font-weight:800;font-size:14px">' + c.score + '/' + c.max + '</td>' +
        '<td style="padding:11px 12px;border-top:1px solid #eef1f5;text-align:center;color:#475569;font-size:13.5px">' + passN + '/' + c.items.length + pendMark + '</td>' +
        '<td style="padding:11px 12px;border-top:1px solid #eef1f5;text-align:center;color:#475569;font-size:13.5px;font-weight:700">' + c.pct + '%</td></tr>';
    }).join('');
    var table = '<table style="width:100%;border-collapse:collapse;margin-bottom:18px;border:1px solid #e8ecf1;border-radius:12px;overflow:hidden">' +
      '<thead><tr style="background:#f1f4f8;font-size:12.5px;color:#334155;font-weight:800">' +
      '<th style="padding:11px 12px;text-align:left">테마 (가중치)</th><th style="padding:11px 12px">가중점수</th><th style="padding:11px 12px">통과</th><th style="padding:11px 12px">달성률</th></tr></thead>' +
      '<tbody>' + tableRows + '</tbody></table>';

    return '<div class="seoeng" style="font-family:inherit;color:#0f172a">' +
      '<div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;padding-bottom:18px;border-bottom:1px solid #e3e8ee;margin-bottom:18px">' +
        '<div style="flex-shrink:0;text-align:center">' + gauge +
          '<div style="font-size:15px;font-weight:800;color:' + g.color + ';margin-top:4px">' + esc(g.label) + '</div>' +
          '<div style="font-size:12px;color:#64748b;margin-top:1px">종합 SEO 100점 만점</div>' +
          '<div style="font-size:12px;color:#94a3b8;margin-top:1px">' + esc(result.domain) + '</div></div>' +
        '<div style="flex:1;min-width:220px">' + bars +
          (result.summary && result.summary.pending ?
            '<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:11px;color:#64748b;font-weight:600">' +
              '<span style="display:inline-flex;align-items:center;gap:5px"><span style="width:14px;height:9px;border-radius:3px;background:#533afd"></span>통과(획득)</span>' +
              '<span style="display:inline-flex;align-items:center;gap:5px"><span style="width:14px;height:9px;border-radius:3px;background:repeating-linear-gradient(45deg,#fcd34d,#fcd34d 3px,#fef3c7 3px,#fef3c7 6px)"></span>확인 필요(회복 가능)</span>' +
              '<span style="display:inline-flex;align-items:center;gap:5px"><span style="width:14px;height:9px;border-radius:3px;background:#eaeef3"></span>미흡</span>' +
            '</div>' : '') +
          (result.summary && result.summary.pending && !result.psi ?
            '<div style="font-size:12px;color:#b45309;margin-top:6px;font-weight:600">※ <b>확인 필요</b> 항목은 정적 수집으로 통과를 입증하지 못한 것(0점 반영) — 이미 적용돼 있으면 <b>정밀 분석(PSI)</b>에서 인정되고, 없으면 각 항목의 수정 코드를 적용하세요.</div>' : '') +
          (result.hasEstimated ?
            '<div style="font-size:12px;color:#92400e;margin-top:6px;font-weight:600">※ <span style="background:#fef3c7;border:1px solid #fcd34d;border-radius:5px;padding:1px 5px;font-weight:800">추정</span> 배지는 마크업 등 <b>실측</b>이 아니라 정황(정규식·임계값)으로 판단한 항목입니다 — <b>구조화 데이터(JSON-LD)</b>로 명시하면 실측으로 확정됩니다.</div>' : '') +
          '<div style="font-size:12px;color:#64748b;margin-top:5px">※ 종합점수는 <b>속도(성능) 제외</b>(별도 +α 게이지) — Google이 SEO와 속도를 분리하는 것과 동일 기준.</div>' +
          (result.renderSuspect && !result.psi ?
            '<div style="font-size:11.5px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 10px;margin-top:8px;line-height:1.5">⚠️ 이 사이트는 <b>JS 렌더링/봇 차단</b>으로 정적 분석이 제한적입니다. 메타·구조화데이터가 자바스크립트로 주입되면 정적 수집으로는 보이지 않아 <b>확인 필요</b>로 표시했습니다. 정확한 점수는 <b>정밀 분석(PSI)</b>을 실행하세요.</div>' : '') +
        '</div>' +
        speedGauge +
      '</div>' +
      statsStrip +
      psiBadges +
      '<div style="display:flex;gap:5px;margin:16px 0">' + scale + '</div>' +
      table +
      renderItems(result) +
      '<div style="background:#f4f6fa;border:1px solid #e3e8ee;border-radius:10px;padding:9px 13px;margin-top:14px;font-size:11px;color:#64748b;line-height:1.7">' +
        '📚 평가 기준(1차): <a href="https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=ko" target="_blank" rel="noopener" style="color:#4285F4;font-weight:700">Google Search Central</a> + ' +
        '<a href="https://pagespeed.web.dev/" target="_blank" rel="noopener" style="color:#4285F4;font-weight:700">PageSpeed Insights(Lighthouse)</a> · ' +
        '2차: <a href="https://searchadvisor.naver.com/guide" target="_blank" rel="noopener" style="color:#03C75A;font-weight:700">네이버 서치어드바이저</a> · ' +
        '속도는 Google Core Web Vitals 공식 임계값(LCP≤2.5s·CLS≤0.10·INP≤200ms) 기준 · 순위 보장 아님, 1차 데이터는 Search Console 확인 권장' +
        '<span style="float:right;color:#cbd5e1;font-weight:700">엔진 v' + BUILD + '</span>' +
      '</div></div>';
  }

  function renderItems(result) {
    return result.categories.map(function (c) {
      var rows = c.items.map(function (it) {
        var badge = it.source ? '<span style="font-size:10px;font-weight:800;padding:2px 6px;border-radius:5px;margin-left:6px;color:#fff;background:' + srcColor(it.source) + '">' + it.source + '</span>' : '';
        // '추정' 배지: 마크업 등 실측이 아니라 정황(정규식·임계값)으로 판단한 항목 — 실측과 구분(#45).
        var estLabel = (it.est === true) ? '추정' : (typeof it.est === 'string' ? it.est : '');
        if (estLabel) badge += '<span title="정적 수집 기반 추정 — 마크업 등 실측 신호가 아니라 정황(정규식·임계값)으로 판단했습니다. 정밀 분석(PSI)·구조화 데이터로 확정하세요." style="font-size:10px;font-weight:800;padding:2px 6px;border-radius:5px;margin-left:5px;color:#92400e;background:#fef3c7;border:1px solid #fcd34d">' + estLabel + '</span>';
        // 항목: 아이콘 + (이름 / 설명 2줄) + 점수. 이름은 크고 진하게, 설명은 대비 있게.
        if (it.pass === null) {
          // '확인 필요' = 정적 수집으로 통과/실패를 단정할 수 없는 항목(JS 주입·헤더 미수집).
          // 오탐 방지를 위해 실패로 찍지 않되, 설명 + 수정 코드로 '다른 항목처럼' 조치 가능하게 한다.
          var pendBlock = it.fix ?
            '<div style="margin:4px 0 10px 33px">' +
            '<div style="font-size:12.5px;font-weight:800;color:#b45309;margin-bottom:5px">🔎 정적 수집으로 확인 안 됨 — 이미 있다면 <b>정밀 분석(PSI)</b>에서 인정됩니다. 없다면 아래를 추가하세요</div>' +
            '<pre style="margin:0;background:#0f172a;color:#e2e8f0;border-radius:9px;padding:12px 14px;font-size:12.5px;line-height:1.6;overflow-x:auto;white-space:pre;font-family:ui-monospace,SFMono-Regular,Menlo,monospace">' +
            esc(it.fix) + '</pre></div>' : '';
          return '<div style="display:flex;gap:11px;align-items:flex-start;padding:11px 0;border-top:1px solid #eef1f5">' +
            '<span style="flex-shrink:0;width:22px;height:22px;border-radius:50%;background:#fef3c7;color:#b45309;font-size:13px;font-weight:800;text-align:center;line-height:22px">!</span>' +
            '<span style="flex:1;min-width:0"><span style="font-size:15px;font-weight:700;color:#0f172a">' + esc(it.name) + '</span>' + badge +
              '<div style="font-size:13px;color:#5b6675;margin-top:2px;line-height:1.5">' + esc(it.desc) + '</div></span>' +
            '<span style="color:#b45309;font-size:13px;font-weight:800;flex-shrink:0">확인 필요</span></div>' + pendBlock;
        }
        var ok = it.pass;
        var codeBlock = '';
        if (!ok && it.fix) {
          codeBlock = '<div style="margin:4px 0 10px 33px">' +
            '<div style="font-size:12.5px;font-weight:800;color:#dc2626;margin-bottom:5px">🔧 이렇게 고치세요 — 아래 코드를 삽입</div>' +
            '<pre style="margin:0;background:#0f172a;color:#e2e8f0;border-radius:9px;padding:12px 14px;font-size:12.5px;line-height:1.6;overflow-x:auto;white-space:pre;font-family:ui-monospace,SFMono-Regular,Menlo,monospace">' +
            esc(it.fix) + '</pre></div>';
        }
        return '<div style="display:flex;gap:11px;align-items:flex-start;padding:11px 0;border-top:1px solid #eef1f5">' +
          '<span style="flex-shrink:0;width:22px;height:22px;border-radius:50%;font-size:13px;font-weight:800;text-align:center;line-height:22px;color:#fff;background:' + (ok ? '#16a34a' : '#dc2626') + '">' + (ok ? '✓' : '✗') + '</span>' +
          '<span style="flex:1;min-width:0"><span style="font-size:15px;font-weight:' + (ok ? 700 : 800) + ';color:#0f172a">' + esc(it.name) + '</span>' + badge +
            '<div style="font-size:13px;color:#5b6675;margin-top:2px;line-height:1.5">' + esc(it.desc) + '</div></span>' +
          '<span style="font-size:14px;font-weight:800;flex-shrink:0;color:' + (ok ? '#16a34a' : '#dc2626') + '">' + (ok ? '+' + it.points : '0/' + it.points) + '</span></div>' +
          codeBlock;
      }).join('');
      // 카테고리 헤더: 아이콘·이름 크게, 우측에 가중점수/가중치(+달성률·상태) 명확히.
      var headRight = (c.score + '/' + c.max + '점 · ' + c.pct + '%')
        + (c.pendingCount ? ' · 확인 ' + c.pendingCount + '건' : '');
      return '<div style="border:1px solid #e3e8ee;border-radius:14px;overflow:hidden;margin-bottom:14px">' +
        '<div style="display:flex;align-items:center;gap:10px;padding:14px 16px;background:linear-gradient(180deg,#f8fafc,#f1f4f8);border-bottom:1px solid #e8ecf1">' +
          '<span style="font-size:19px">' + c.icon + '</span>' +
          '<span style="font-weight:800;font-size:16.5px;color:#0f172a">' + esc(c.label) + '</span>' +
          '<span style="margin-left:auto;font-weight:800;font-size:14px;color:' + c.color + '">' + headRight + '</span></div>' +
        '<div style="padding:4px 16px 12px">' + rows + '</div></div>';
    }).join('');
  }

  // ── PDF 리포트 (브라우저 인쇄 → PDF 저장, 의존성 0) ──
  function buildReportHTML(result, opts) {
    opts = opts || {};
    var brand = opts.brand || '#533afd';
    var title = opts.title || 'SEO 진단 리포트';
    var dateStr = opts.date || '';
    if (!dateStr && typeof Date !== 'undefined') {
      var d = new Date();
      dateStr = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
    }
    var body = renderInfographic(result, opts);
    return '<!doctype html><html lang="ko"><head><meta charset="utf-8">' +
      '<title>' + esc(title) + ' — ' + esc(result.domain) + '</title><style>' +
      '@page{margin:12mm}' +
      'body{font-family:\'Pretendard\',\'Apple SD Gothic Neo\',\'Noto Sans KR\',system-ui,sans-serif;color:#0f172a;margin:0;padding:24px;line-height:1.6;-webkit-print-color-adjust:exact;print-color-adjust:exact}' +
      '.rpt-head{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid ' + brand + ';padding-bottom:14px;margin-bottom:22px}' +
      '.rpt-brand{font-size:22px;font-weight:800;letter-spacing:-.02em}.rpt-brand b{color:' + brand + '}' +
      '.rpt-meta{font-size:12px;color:#64748b;text-align:right;line-height:1.7}' +
      '.seoeng table{page-break-inside:avoid}@media print{button{display:none!important}}' +
      '</style></head><body>' +
      '<div class="rpt-head"><div class="rpt-brand">' + esc(title) + ' <b>·</b></div>' +
      '<div class="rpt-meta"><div><strong>' + esc(result.domain) + '</strong></div><div>진단일 ' + esc(dateStr) + '</div>' +
      '<div>종합 ' + result.total + '/' + result.max + '점 · ' + esc(result.grade.label) + '</div></div></div>' +
      body +
      '<div style="margin-top:18px;font-size:11px;color:#94a3b8;text-align:center">Google SEO 시작 가이드 · 네이버 서치어드바이저 기준 · 참고용 분석(순위 보장 아님)</div>' +
      '</body></html>';
  }

  function printReport(result, opts) {
    var w = (typeof window !== 'undefined') ? window.open('', '_blank') : null;
    if (!w) { if (typeof alert !== 'undefined') alert('팝업이 차단되었습니다. 허용 후 다시 시도해주세요.'); return false; }
    w.document.write(buildReportHTML(result, opts));
    w.document.close(); w.focus();
    setTimeout(function () { try { w.print(); } catch (e) {} }, 500);
    return true;
  }

  return {
    version: VERSION,
    analyze: analyze,
    mergePSI: mergePSI,
    cwvClassify: cwvClassify,
    CWV_THRESHOLDS: CWV_THRESHOLDS,
    robotsAllows: robotsAllows,
    renderInfographic: renderInfographic,
    buildReportHTML: buildReportHTML,
    printReport: printReport,
    gradeFor: gradeFor
  };
});
