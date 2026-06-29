/*!
 * VENOM SEO Engine — 독립 실행형 SEO 진단 엔진 (의존성 0)
 * 평가 기준: Google SEO 시작 가이드 + 네이버 서치어드바이저 가이드
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

  var VERSION = '1.0.0';

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
    var hasFavicon = !!(doc && doc.querySelector('link[rel~="icon"],link[rel="shortcut icon"],link[rel="apple-touch-icon"]'));
    var canonical = q('link[rel="canonical"]', 'href');
    var lang = doc ? (doc.documentElement.getAttribute('lang') || '').trim() : '';
    var robotsMeta = (metaByName('robots') || metaByName('googlebot'));
    var notNoindex = !/noindex/i.test(robotsMeta);
    var robotsTxtOk = robots.trim().length > 0;
    var crawlOk = robotsAllows(robots, 'Googlebot') && robotsAllows(robots, 'Yeti') && robotsAllows(robots, '*');

    // 검색 노출
    var hasLd = /application\/ld\+json/i.test(html);
    var ogTitle = metaByProp('og:title'), ogDesc = metaByProp('og:description');
    var ogOk = !!ogTitle && !!ogDesc;
    var hasSitemap = /^\s*sitemap\s*:/im.test(robots);

    // SPA 감지
    var bodyText = doc && doc.body ? doc.body.textContent.replace(/\s+/g, ' ').trim() : '';
    var scriptCount = doc ? doc.querySelectorAll('script[src]').length : 0;
    var isSPA = (bodyText.length < 150 && scriptCount >= 2 && !title && !h1Count) ||
      (doc && !!doc.querySelector('#root:empty,#app:empty,[data-reactroot]:empty'));

    var checks = {
      content: [
        ['제목(title) 태그', '검색결과 제목 — ' + titleNote, 8, titlePass, '공통'],
        ['메타 디스크립션', '검색결과 설명문 — ' + descNote, 8, descPass, '공통'],
        ['H1 대표 제목', h1Note, 6, h1Pass, '네이버'],
        ['이미지 ALT 텍스트', '이미지 대체 텍스트 (' + imgDesc + ')', 7, imgAltOk, '공통'],
        ['의미있는 링크 텍스트', '서술형 앵커 — "여기 클릭" 류 지양', 5, linkTextOk, 'Google'],
        ['서술형 URL', 'URL에 의미있는 단어 — ' + urlNote, 4, urlOk, 'Google']
      ],
      tech: [
        ['HTTPS 보안 연결', 'SSL 적용 — Google·네이버 모두 신뢰 신호', 6, isHttps, '공통'],
        ['검색로봇 수집 허용', 'robots.txt가 Googlebot·Yeti 차단 안 함', 6, crawlOk, '공통'],
        ['인덱싱 허용', 'meta robots noindex 미설정', 5, notNoindex, '공통'],
        ['Canonical 태그', '중복 URL 정규화 — 대표 주소 지정', 5, !!canonical, '공통'],
        ['Viewport(모바일)', '모바일 반응형 메타 — 모바일 우선 인덱싱', 4, hasViewport, '공통'],
        ['HTML lang 속성', '페이지 언어 명시 — 검색엔진 언어 인식', 4, !!lang, 'Google']
      ],
      search: [
        ['구조화 데이터', 'Schema.org JSON-LD — 리치결과 노출', 7, hasLd, 'Google'],
        ['Open Graph 태그', 'og:title·og:description — 공유 미리보기', 6, ogOk, '네이버'],
        ['sitemap.xml 선언', 'robots.txt에 Sitemap: 선언 — 수집 촉진', 4, hasSitemap, '공통'],
        ['파비콘', '검색결과에 표시되는 사이트 아이콘', 2, hasFavicon, 'Google'],
        ['robots.txt 존재', '크롤러 수집 규칙 파일 제공', 3, robotsTxtOk, '공통']
      ],
      speed: [
        ['성능 점수', 'Google Lighthouse 성능 점수 (정밀 분석 시 측정)', 3, null, 'Google'],
        ['텍스트 압축', 'gzip/brotli 압축 적용 여부', 3, null, 'Google'],
        ['이미지 최적화', 'WebP 형식·지연 로딩 적용 여부', 2, null, 'Google'],
        ['렌더링 최적화', 'CSS·JS 렌더링 차단 최소화', 2, null, 'Google']
      ]
    };

    return buildResult(url, domain, isHttps, isSPA, checks, null);
  }

  var CAT_DEF = [
    { key: 'content', label: '콘텐츠 & 메타', icon: '📝', color: '#533afd' },
    { key: 'tech', label: '기술·크롤링', icon: '⚙️', color: '#06b6d4' },
    { key: 'search', label: '검색 노출 강화', icon: '🔍', color: '#8b5cf6' },
    { key: 'speed', label: '속도 최적화', icon: '⚡', color: '#f59e0b' }
  ];

  function gradeFor(total, max) {
    var pct = max ? total / max : 0;
    if (pct >= 0.9) return { label: '플래티넘', color: '#7c3aed', desc: '최상위 SEO' };
    if (pct >= 0.8) return { label: '골드', color: '#d97706', desc: '상위 20%' };
    if (pct >= 0.7) return { label: '실버', color: '#64748b', desc: '개선 중' };
    if (pct >= 0.6) return { label: '브론즈', color: '#b45309', desc: '보통' };
    return { label: '개선필요', color: '#dc2626', desc: '즉시 조치 필요' };
  }

  function buildResult(url, domain, isHttps, isSPA, checks, psi) {
    var categories = CAT_DEF.map(function (cat) {
      var items = checks[cat.key].map(function (it) {
        return { name: it[0], desc: it[1], points: it[2], pass: it[3], source: it[4] };
      });
      var max = items.reduce(function (s, it) { return s + it.points; }, 0);
      var pending = items.some(function (it) { return it.pass === null; });
      var score = items.reduce(function (s, it) { return s + (it.pass === true ? it.points : 0); }, 0);
      return {
        key: cat.key, label: cat.label, icon: cat.icon, color: cat.color,
        max: max, score: score, pending: pending,
        pct: pending ? 0 : Math.round(score / max * 100), items: items
      };
    });
    var scored = categories.filter(function (c) { return !c.pending; });
    var baseTotal = scored.reduce(function (s, c) { return s + c.score; }, 0);
    var baseMax = scored.reduce(function (s, c) { return s + c.max; }, 0);
    var hasPSI = !!psi;
    var total = hasPSI ? categories.reduce(function (s, c) { return s + c.score; }, 0) : baseTotal;
    var max = hasPSI ? categories.reduce(function (s, c) { return s + c.max; }, 0) : baseMax;
    return {
      version: VERSION, url: url, domain: domain, isHttps: isHttps, isSPA: isSPA,
      categories: categories, baseTotal: baseTotal, baseMax: baseMax,
      total: total, max: max, hasPSI: hasPSI, psi: psi || null,
      grade: gradeFor(total, max)
    };
  }

  // ── PSI(Lighthouse) 결과 병합 → 속도 항목 채점 + 종합점수 갱신 ──
  function mergePSI(result, psiJson) {
    var audits = (psiJson.lighthouseResult && psiJson.lighthouseResult.audits) || {};
    var cats = (psiJson.lighthouseResult && psiJson.lighthouseResult.categories) || {};
    function pass(id) { var a = audits[id]; return !!(a && (a.score === 1 || a.score === null)); }
    var perf = Math.round((cats.performance ? cats.performance.score : 0) * 100);
    var speedItems = [
      ['성능 점수', 'Google Lighthouse 성능: ' + perf + '/100', 3, perf >= 90, 'Google'],
      ['텍스트 압축', 'gzip/brotli 압축 적용 여부', 3, pass('uses-text-compression'), 'Google'],
      ['이미지 최적화', 'WebP 형식·지연 로딩 적용 여부', 2, pass('uses-webp-images'), 'Google'],
      ['렌더링 최적화', 'CSS·JS 렌더링 차단 최소화', 2, pass('render-blocking-resources'), 'Google']
    ];
    var le = psiJson.loadingExperience, ole = psiJson.originLoadingExperience;
    var crux = null, src = (le && le.metrics) ? le : (ole && ole.metrics) ? ole : null;
    if (src) {
      var lcp = src.metrics.LARGEST_CONTENTFUL_PAINT_MS, cls = src.metrics.CUMULATIVE_LAYOUT_SHIFT_SCORE;
      crux = {
        origin: !(le && le.metrics),
        lcp: lcp ? { sec: +(lcp.percentile / 1000).toFixed(2), cat: lcp.category } : null,
        cls: cls ? { val: +(cls.percentile / 100).toFixed(3), cat: cls.category } : null,
        overall: src.overall_category || ''
      };
    }
    var checks = {};
    result.categories.forEach(function (c) {
      checks[c.key] = c.key === 'speed' ? speedItems
        : c.items.map(function (it) { return [it.name, it.desc, it.points, it.pass, it.source]; });
    });
    var merged = buildResult(result.url, result.domain, result.isHttps, result.isSPA, checks, {
      seo: Math.round((cats.seo ? cats.seo.score : 0) * 100),
      perf: perf,
      accessibility: Math.round((cats.accessibility ? cats.accessibility.score : 0) * 100),
      bestPractices: Math.round((cats['best-practices'] ? cats['best-practices'].score : 0) * 100),
      crux: crux
    });
    return merged;
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

  function bar(label, score, max, color, pending) {
    var pct = pending ? 0 : (max ? Math.round(score / max * 100) : 0);
    return '<div style="display:flex;align-items:center;gap:10px;margin:7px 0;font-size:13px">' +
      '<span style="width:120px;flex-shrink:0;color:#334155;font-weight:600">' + esc(label) + '</span>' +
      '<span style="flex:1;height:9px;background:#eef0f5;border-radius:9px;overflow:hidden">' +
      '<span style="display:block;height:100%;width:' + pct + '%;background:' + color + ';border-radius:9px;transition:width .8s ease"></span></span>' +
      '<span style="width:64px;text-align:right;font-weight:700;color:' + (pending ? '#9ca3af' : color) + '">' +
      (pending ? '정밀필요' : score + '/' + max) + '</span></div>';
  }

  function renderInfographic(result, opts) {
    opts = opts || {};
    var brand = opts.brand || '#533afd';
    var g = result.grade;
    var gauge = donut(result.total, result.max, g.color, g.label);
    var bars = result.categories.map(function (c) { return bar(c.label, c.score, c.max, c.color, c.pending); }).join('');

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
      var b = function (lbl, v, col) { return '<span style="background:#f4f6fa;border-radius:8px;padding:8px 12px;font-size:12px">' + lbl + ' <strong style="color:' + col + '">' + v + '</strong></span>'; };
      psiBadges = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">' +
        b('SEO', p.seo, '#4285F4') + b('성능', p.perf, p.perf >= 90 ? '#16a34a' : p.perf >= 50 ? '#d97706' : '#dc2626') +
        b('접근성', p.accessibility, '#06b6d4') + b('권장사항', p.bestPractices, '#8b5cf6') + '</div>';
      if (p.crux) {
        var cx = p.crux;
        psiBadges += '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:12px 14px;margin-top:10px;font-size:12px;color:#166534">' +
          '📊 실제 사용자 현장 데이터(CrUX' + (cx.origin ? ' · 도메인 누적' : '') + ') ' +
          (cx.lcp ? 'LCP <strong>' + cx.lcp.sec + 's (' + cx.lcp.cat + ')</strong> ' : '') +
          (cx.cls ? '· CLS <strong>' + cx.cls.val + ' (' + cx.cls.cat + ')</strong>' : '') + '</div>';
      }
    }

    return '<div class="seoeng" style="font-family:inherit;color:#0f172a">' +
      '<div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;padding-bottom:18px;border-bottom:1px solid #e3e8ee;margin-bottom:18px">' +
        '<div style="flex-shrink:0;text-align:center">' + gauge +
          '<div style="font-size:13px;font-weight:700;color:' + g.color + ';margin-top:2px">' + esc(g.label) + '</div>' +
          '<div style="font-size:11px;color:#94a3b8">' + esc(result.domain) + ' · ' + esc(g.desc) + '</div></div>' +
        '<div style="flex:1;min-width:220px">' + bars +
          (result.categories.some(function (c) { return c.pending; }) && !result.psi ?
            '<div style="font-size:11px;color:#9ca3af;margin-top:4px">※ 속도는 정밀 분석(PSI) 시 측정됩니다 (기본 90점 만점)</div>' : '') +
        '</div>' +
      '</div>' +
      psiBadges +
      '<div style="display:flex;gap:5px;margin:16px 0">' + scale + '</div>' +
      renderItems(result) +
      '<div style="background:#f4f6fa;border:1px solid #e3e8ee;border-radius:10px;padding:9px 13px;margin-top:14px;font-size:11px;color:#64748b;line-height:1.7">' +
        '📚 평가 기준: <a href="https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=ko" target="_blank" rel="noopener" style="color:#4285F4;font-weight:700">Google SEO 가이드</a> · ' +
        '<a href="https://searchadvisor.naver.com/guide" target="_blank" rel="noopener" style="color:#03C75A;font-weight:700">네이버 서치어드바이저</a> 기반 · 순위 보장 아님, 1차 데이터는 Search Console 확인 권장' +
      '</div></div>';
  }

  function renderItems(result) {
    return result.categories.map(function (c) {
      var rows = c.items.map(function (it) {
        var badge = it.source ? '<span style="font-size:9px;font-weight:700;padding:1px 5px;border-radius:4px;margin-left:5px;color:#fff;background:' + srcColor(it.source) + '">' + it.source + '</span>' : '';
        if (it.pass === null) {
          return '<div style="display:flex;gap:9px;align-items:flex-start;padding:7px 0;border-top:1px solid #f1f3f7">' +
            '<span style="flex-shrink:0;width:18px;height:18px;border-radius:50%;background:#f3f4f6;color:#9ca3af;font-size:11px;text-align:center;line-height:18px">?</span>' +
            '<span style="flex:1;font-size:13px;color:#9ca3af">' + esc(it.name) + badge + ' <span style="color:#b0b7c3">— ' + esc(it.desc) + '</span></span>' +
            '<span style="color:#9ca3af;font-size:12px">—/' + it.points + '</span></div>';
        }
        var ok = it.pass;
        return '<div style="display:flex;gap:9px;align-items:flex-start;padding:7px 0;border-top:1px solid #f1f3f7">' +
          '<span style="flex-shrink:0;width:18px;height:18px;border-radius:50%;font-size:11px;text-align:center;line-height:18px;color:#fff;background:' + (ok ? '#16a34a' : '#dc2626') + '">' + (ok ? '✓' : '✗') + '</span>' +
          '<span style="flex:1;font-size:13px"><strong style="font-weight:' + (ok ? 600 : 700) + '">' + esc(it.name) + '</strong>' + badge + ' <span style="color:#64748b">— ' + esc(it.desc) + '</span></span>' +
          '<span style="font-size:12px;font-weight:700;color:' + (ok ? '#16a34a' : '#dc2626') + '">' + (ok ? '+' + it.points : '0/' + it.points) + '</span></div>';
      }).join('');
      return '<div style="border:1px solid #e3e8ee;border-radius:12px;overflow:hidden;margin-bottom:12px">' +
        '<div style="display:flex;align-items:center;gap:9px;padding:11px 14px;background:#f8fafc">' +
          '<span>' + c.icon + '</span><span style="font-weight:700;font-size:14px">' + esc(c.label) + '</span>' +
          '<span style="margin-left:auto;font-weight:700;color:' + (c.pending ? '#9ca3af' : c.color) + '">' + (c.pending ? '정밀 분석 필요' : c.score + '/' + c.max + '점') + '</span></div>' +
        '<div style="padding:4px 14px 10px">' + rows + '</div></div>';
    }).join('');
  }

  return {
    version: VERSION,
    analyze: analyze,
    mergePSI: mergePSI,
    robotsAllows: robotsAllows,
    renderInfographic: renderInfographic,
    gradeFor: gradeFor
  };
});
