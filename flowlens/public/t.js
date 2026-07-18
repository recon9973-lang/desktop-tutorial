/*
 * FlowLens 추적 SDK (t.js)
 * 설치: <script async src="https://app.flowlens.kr/t.js" data-site="SITE_KEY"></script>
 *
 * 개인정보 보호 원칙 (코드 레벨):
 *  - input/textarea/select/[type=password] 의 value 는 절대 읽지 않는다.
 *  - 클릭 대상 라벨 텍스트는 전송 전에 이메일/전화/카드/주민번호 패턴을 마스킹한다.
 *  - 좌표는 절대 픽셀이 아니라 문서 대비 0~1 상대값으로만 저장한다.
 *  - IP/쿠키 개인식별을 사용하지 않는다. 세션 구분은 sessionStorage 기반.
 */
(function () {
  "use strict";

  // 봇 제외
  if (navigator.webdriver) return;

  // 추적 거부 신호 존중 (법무 4.4): GPC / DNT / opt-out 시 수집 중단
  if (navigator.globalPrivacyControl === true) return;
  var _dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
  if (_dnt === "1" || _dnt === "yes") return;
  try {
    if (localStorage.getItem("fl_optout") === "1") return;
  } catch (e) {}

  // 스크립트 태그 확보: async 스크립트나 GTM 맞춤HTML 주입 시 document.currentScript가 null이 된다.
  // 그 경우 t.js를 로드한 script 태그를 직접 찾는다.
  var script = document.currentScript;
  if (!script) {
    var cands = document.querySelectorAll('script[src*="/t.js"]');
    script = cands.length ? cands[cands.length - 1] : null;
  }

  // siteKey는 여러 경로로 읽는다(설치 방식별 호환):
  //  1) data-site 속성 (직접 <head> 삽입)
  //  2) window.FLOWLENS_SITE 전역변수
  //  3) 스크립트 URL의 ?site= 쿼리 (GTM은 data-* 속성을 제거하므로 이 방식 권장)
  var siteKey = (script && script.getAttribute && script.getAttribute("data-site")) || window.FLOWLENS_SITE || "";
  if (!siteKey && script && script.src) {
    try { siteKey = new URL(script.src).searchParams.get("site") || ""; } catch (e) {}
  }
  if (!siteKey) {
    console.warn("[FlowLens] siteKey를 찾지 못했습니다. 설치 코드에 data-site 또는 ?site= 를 확인하세요.");
    return;
  }

  // 수집 엔드포인트: 스크립트가 로드된 오리진 기준 (못 찾으면 현재 페이지 오리진)
  var origin;
  try { origin = (script && script.src) ? new URL(script.src).origin : location.origin; }
  catch (e) { origin = location.origin; }
  var COLLECT_URL = origin + "/api/collect";

  // ---- 세션 관리 (개인 식별 아님) ----
  var SESSION_TTL = 30 * 60 * 1000; // 30분 무활동 만료
  function getSessionKey() {
    try {
      var raw = sessionStorage.getItem("_fl_sess");
      var now = Date.now();
      if (raw) {
        var s = JSON.parse(raw);
        if (now - s.t < SESSION_TTL) {
          s.t = now;
          sessionStorage.setItem("_fl_sess", JSON.stringify(s));
          return s.k;
        }
      }
      var key = "s_" + Math.random().toString(36).slice(2) + now.toString(36);
      sessionStorage.setItem("_fl_sess", JSON.stringify({ k: key, t: now }));
      return key;
    } catch (e) {
      // sessionStorage 불가 시 임시 키
      return "s_ephemeral_" + Math.random().toString(36).slice(2);
    }
  }
  var sessionKey = getSessionKey();

  // ---- 디바이스 판별 ----
  function device() {
    var w = window.innerWidth;
    if (w < 768) return "MOBILE";
    if (w < 1024) return "TABLET";
    return "DESKTOP";
  }

  // ---- 유입 채널 (referrer 기반, 간단 분류) ----
  function channel() {
    var r = document.referrer || "";
    if (!r) return "direct";
    try {
      var h = new URL(r).hostname;
      if (/google|naver|daum|bing|yahoo/.test(h) && /search|\/search/.test(r)) return "search";
      if (/google|naver|daum|bing/.test(h)) return "search";
      if (/facebook|instagram|youtube|tiktok|twitter|x\.com|linkedin/.test(h)) return "social";
      if (/googlesyndication|doubleclick|adservice/.test(h)) return "ad";
      return "referral";
    } catch (e) {
      return "referral";
    }
  }

  // ---- 개인정보 마스킹 ----
  var MASK_PATTERNS = [
    /[\w.+-]+@[\w-]+\.[\w.-]+/g, // email
    /\b\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b/g, // phone
    /\b(?:\d[ -]?){13,16}\b/g, // card
    /\b\d{6}[-\s]?\d{7}\b/g, // 주민번호
  ];
  function mask(text) {
    if (!text) return "";
    var t = String(text).slice(0, 80);
    for (var i = 0; i < MASK_PATTERNS.length; i++) t = t.replace(MASK_PATTERNS[i], "***");
    return t.trim();
  }

  // 클릭 대상 라벨: 입력요소 value는 절대 읽지 않는다.
  function labelOf(el) {
    if (!el) return "";
    var tag = (el.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") {
      // value 미접근. 타입/aria만.
      return "[" + (el.getAttribute("type") || tag) + "]";
    }
    // contenteditable(리치 에디터·일부 검색창·채팅 입력)에 방문자가 친 글이 textContent로 새는 것 방지.
    // isContentEditable 은 편집영역의 자식(span 등)에서도 true → 값을 읽지 않고 자리표시만.
    if (el.isContentEditable) return "[edit]";
    // 고객이 지정한 안전 라벨(data-fl-label) 우선, 없으면 aria-label/텍스트
    var txt = el.getAttribute("data-fl-label") || el.getAttribute("aria-label") || el.textContent || el.getAttribute("alt") || "";
    return mask(txt);
  }

  // 고객이 수집 제외로 지정한 영역([data-fl-ignore], .fl-sensitive)
  // 조상 6단계만 보면 깊은 DOM에서 수집제외가 무시된다("무조건 미수집" 약속 위반) → 뿌리까지 확인.
  // 상한 40은 비정상적으로 깊은 트리에서의 폭주만 막는 안전장치(정상 페이지는 훨씬 얕다).
  function isIgnored(el) {
    var n = el;
    for (var i = 0; i < 40 && n && n !== document.body; i++) {
      if (n.getAttribute && (n.getAttribute("data-fl-ignore") !== null || (n.classList && n.classList.contains("fl-sensitive")))) return true;
      n = n.parentElement;
    }
    return false;
  }

  function isPasswordArea(el) {
    var n = el;
    for (var i = 0; i < 3 && n; i++) {
      if (n.tagName === "INPUT" && n.getAttribute("type") === "password") return true;
      n = n.parentElement;
    }
    return false;
  }

  function isInteractive(el) {
    var n = el;
    for (var i = 0; i < 4 && n; i++) {
      var tag = (n.tagName || "").toLowerCase();
      if (tag === "a" || tag === "button" || tag === "input" || tag === "select" || tag === "textarea") return true;
      if (n.getAttribute && (n.getAttribute("role") === "button" || n.onclick)) return true;
      n = n.parentElement;
    }
    return false;
  }

  // 팝업·플로팅 배너처럼 화면에 고정된 레이어 안인가.
  // 고정 레이어의 클릭을 문서 좌표(pageY = clientY + scrollY)로 환산하면, 같은 "닫기" 버튼이
  // 스크롤 위치에 따라 히트맵의 전혀 다른 곳에 찍힌다(맨 위에서 닫으면 9% 지점, 중간에서 닫으면 99% 지점).
  // 그러면 뒤에 있는 콘텐츠의 클릭 수가 부풀려지고 히트맵이 오염되므로 좌표를 보내지 않는다.
  function inFixedLayer(el) {
    var n = el;
    for (var i = 0; i < 8 && n && n.nodeType === 1 && n !== document.body; i++) {
      var pos = "";
      try { pos = window.getComputedStyle(n).position; } catch (e) {}
      if (pos === "fixed" || pos === "sticky") return true;
      n = n.parentElement;
    }
    return false;
  }

  // 문서 대비 상대 좌표 (0~1)
  function relCoords(e) {
    var docW = Math.max(document.documentElement.scrollWidth, window.innerWidth);
    var docH = Math.max(document.documentElement.scrollHeight, window.innerHeight);
    return {
      xRel: Math.min(1, Math.max(0, (e.pageX || 0) / docW)),
      yRel: Math.min(1, Math.max(0, (e.pageY || 0) / docH)),
    };
  }

  // referrer는 호스트명만 (전체 URL·query 미전송)
  function referrerHost() {
    try {
      return document.referrer ? new URL(document.referrer).hostname.slice(0, 120) : "";
    } catch (e) {
      return "";
    }
  }
  // URL은 query/hash 제거 (개인정보 유입 차단)
  function cleanUrl() {
    return (location.origin + location.pathname).slice(0, 300);
  }

  // ---- 이벤트 큐 + 전송 ----
  var queue = [];
  var base = {
    site: siteKey,
    session: sessionKey,
    device: device(),
    referrer: referrerHost(),
    channel: channel(),
  };

  function push(type, data) {
    var ev = {
      type: type,
      url: cleanUrl(),
      path: location.pathname.slice(0, 200),
      vw: window.innerWidth,
      vh: window.innerHeight,
      ts: Date.now(),
    };
    if (data) for (var k in data) ev[k] = data[k];
    queue.push(ev);
    if (queue.length >= 20) flush();
  }

  function flush(useBeacon) {
    queueMoves(); // 모아둔 마우스 경로를 함께 전송
    if (queue.length === 0) return;
    var payload = { site: base.site, session: base.session, device: base.device, referrer: base.referrer, channel: base.channel, events: queue.splice(0, queue.length) };
    var body = JSON.stringify(payload);
    try {
      if (useBeacon && navigator.sendBeacon) {
        navigator.sendBeacon(COLLECT_URL, new Blob([body], { type: "application/json" }));
      } else {
        fetch(COLLECT_URL, { method: "POST", body: body, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(function () {});
      }
    } catch (e) {}
  }

  var flushTimer = setInterval(function () { flush(false); }, 5000);

  // ---- 이벤트 리스너 ----
  // page_view
  push("page_view");

  // 스크롤 (throttle 250ms) + 최대 도달률
  var maxScroll = 0, scrollTick = 0;
  window.addEventListener(
    "scroll",
    function () {
      var now = Date.now();
      if (now - scrollTick < 250) return;
      scrollTick = now;
      var docH = document.documentElement.scrollHeight - window.innerHeight;
      var pct = docH > 0 ? Math.round(((window.scrollY || 0) / docH) * 100) : 0;
      if (pct > maxScroll) maxScroll = pct;
      push("scroll", { scrollPct: Math.min(100, pct) });
    },
    { passive: true }
  );

  // 클릭 + rage/dead click 판정
  var recentClicks = [];
  document.addEventListener(
    "click",
    function (e) {
      var el = e.target;
      if (isPasswordArea(el) || isIgnored(el)) return; // 비밀번호·수집제외 영역은 미수집

      var c = relCoords(e);
      var now = Date.now();
      // rage click: 400ms 내 근접 위치 3회+
      recentClicks.push({ x: c.xRel, y: c.yRel, t: now });
      recentClicks = recentClicks.filter(function (r) { return now - r.t < 500; });
      var near = recentClicks.filter(function (r) { return Math.abs(r.x - c.xRel) < 0.05 && Math.abs(r.y - c.yRel) < 0.05; });
      var isRage = near.length >= 3;

      var interactive = isInteractive(el);
      var type = isRage ? "rage_click" : !interactive ? "dead_click" : "click";
      // 고정 레이어(팝업 등)의 클릭은 문서 좌표가 무의미하므로 좌표 없이 보낸다.
      // 좌표가 없으면 히트맵 조회(xRel not null)에서 자동 제외되고, 클릭 수·라벨은 그대로 남는다.
      if (inFixedLayer(el)) {
        push(type, { scrollPct: maxScroll, targetLabel: labelOf(el), meta: '{"fixed":1}' });
      } else {
        push(type, { xRel: c.xRel, yRel: c.yRel, scrollPct: maxScroll, targetLabel: labelOf(el) });
      }
    },
    true
  );

  // 마우스 이동 (throttle 90ms). 낱개 이벤트로 보내면 세션당 수백 건이 쌓여 저장·전송 비용이 급증하므로,
  // 좌표를 버퍼에 모아 "경로 1건(move_path)"으로 묶어 보낸다. (0~1000 정수 좌표로 양자화)
  var ptTick = 0;
  var movBuf = [];
  document.addEventListener(
    "pointermove",
    function (e) {
      var now = Date.now();
      if (now - ptTick < 90) return;
      ptTick = now;
      var c = relCoords(e);
      if (!c) return;
      movBuf.push(Math.round(c.xRel * 1000) + "," + Math.round(c.yRel * 1000));
      if (movBuf.length >= 400) queueMoves(); // 너무 길어지지 않게 끊어 보냄
    },
    { passive: true }
  );

  // 버퍼에 쌓인 이동 좌표를 경로 1건으로 큐에 넣는다 (flush 직전에 호출).
  function queueMoves() {
    if (!movBuf.length) return;
    var pts = movBuf.join("|");
    movBuf = [];
    queue.push({
      type: "move_path",
      url: cleanUrl(),
      path: location.pathname.slice(0, 200),
      vw: window.innerWidth,
      vh: window.innerHeight,
      ts: Date.now(),
      pts: pts,
    });
  }

  // 폼 (입력값은 절대 미수집, focus/submit 신호만)
  document.addEventListener(
    "focusin",
    function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") {
        if (isPasswordArea(e.target) || isIgnored(e.target)) return;
        push("form_focus", { targetLabel: labelOf(e.target) });
      }
    },
    true
  );
  document.addEventListener(
    "submit",
    function () { push("form_submit"); },
    true
  );

  // ---- CTA 노출 (핵심 행동 유도 요소가 뷰포트에 들어오면 1회 cta_view) ----
  // 이 값(cta_view / page_view = ctaViewRate)이 "mobile-cta" 개선제안의 근거이므로 오탐이 곧 오진이다.
  // 과거에는 "button, a.btn, .cta, [data-cta]"만 봤다. .btn/.cta 클래스 관례를 쓰지 않는 사이트에서는
  // 진짜 CTA("여행문의" 등 평범한 <a>)를 전부 놓치고 헤더의 30x25 검색 아이콘만 잡혀,
  // 노출률이 늘 100%(=문제 없음)로 나와 제안이 영원히 뜨지 않았다. 그래서 텍스트·크기로 판정한다.
  // 영어는 반드시 단어 경계(\b)로 감쌀 것. 없으면 "Facebook"의 book, "restart"의 start 가 걸려
  // 푸터 SNS 링크까지 CTA로 오인한다. 한국어는 단어 경계 개념이 없어 부분일치로 둔다.
  var CTA_TEXT = /예약|문의|신청|상담|구매|결제|주문|접수|가입|등록|무료|시작|바로가기|다운로드|견적|장바구니|\b(?:reserve|book|buy|order|apply|contact|sign\s?up|get\s?started|download|quote|demo|start)\b/i;
  var CTA_MIN_W = 60; // 아이콘 버튼(예: 검색 돋보기)을 CTA로 오인하지 않기 위한 최소 크기
  var CTA_MIN_H = 24;
  var CTA_MAX = 40; // 관찰 대상 상한 (성능 보호)
  var CTA_SEL =
    "button, a[href], [role=button], input[type=submit], input[type=button], [data-cta], [data-fl-cta], .cta, .btn";

  function ctaText(el) {
    // input의 value는 읽지 않는다(개인정보 원칙). submit 버튼은 아래에서 별도 처리.
    var t = el.getAttribute("data-fl-label") || el.getAttribute("aria-label") || el.textContent || "";
    return t.replace(/\s+/g, " ").trim();
  }

  function isCta(el) {
    // 1) 의도가 명시된 것은 무조건 인정 (.cta 는 "이게 CTA다"라는 선언이므로 신뢰한다)
    if (el.getAttribute("data-cta") !== null || el.getAttribute("data-fl-cta") !== null) return true;
    if (el.classList && el.classList.contains("cta")) return true;
    // 2) 클릭 가능한 요소만
    var tag = (el.tagName || "").toLowerCase();
    var type = (el.getAttribute("type") || "").toLowerCase();
    var clickable =
      tag === "button" ||
      (tag === "a" && el.getAttribute("href") !== null) ||
      el.getAttribute("role") === "button" ||
      (tag === "input" && (type === "submit" || type === "button"));
    if (!clickable) return false;
    // 3) 제출 버튼은 그 자체가 전환 행동이므로 문구를 보지 않는다
    if (type === "submit") return true;
    // 4) 아이콘·장식 배제: 너무 작거나(=아이콘) 글자가 없으면 CTA로 보지 않는다
    var r = el.getBoundingClientRect();
    if (r.width < CTA_MIN_W || r.height < CTA_MIN_H) return false;
    var txt = ctaText(el);
    if (!txt) return false;
    // 5) 행동 유도 문구일 때만 CTA.
    //    .btn 을 근거로 쓰면 안 된다 — 로그인·쿠키동의 버튼에도 똑같이 붙는 범용 스타일 클래스라
    //    전부 CTA로 잡혀 노출률이 부풀고, 그러면 mobile-cta 제안이 다시 영원히 안 뜬다.
    return CTA_TEXT.test(txt);
  }

  var ctaIo = null;
  var ctaMo = null;
  var ctaObserved = new WeakSet(); // 중복 observe 방지
  var ctaViewed = new WeakSet(); // 노출 1회만 기록
  var ctaCount = 0;
  var ctaPending = []; // 화면엔 들어왔지만 팝업에 가려져 아직 "봤다"고 할 수 없는 것

  // IntersectionObserver는 "화면 영역 안에 있나"만 보고 "실제로 눈에 보이나"는 보지 않는다.
  // 그래서 팝업이 새까맣게 덮고 있는 CTA도 노출 100%로 잡힌다 → 노출률이 부풀고 mobile-cta 제안이
  // 영영 안 뜬다. 요소 중심점에 실제로 뭐가 있는지 확인해서 가려졌는지 판별한다.
  function ctaVisibleAt(el) {
    var r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    var x = Math.min(Math.max(r.left + r.width / 2, 1), window.innerWidth - 1);
    var y = Math.min(Math.max(r.top + r.height / 2, 1), window.innerHeight - 1);
    var top;
    try { top = document.elementFromPoint(x, y); } catch (e) { return true; } // 확인 불가면 보인 것으로 (과소집계 방지)
    if (!top) return false;
    // 자기 자신·자손(내부 span 등)·조상이 잡히면 가려지지 않은 것.
    // 판정이 애매하면 "보였다" 쪽으로 기운다 — 과소집계는 없는 문제를 있다고 하는 오진을 만든다.
    return el === top || el.contains(top) || top.contains(el);
  }

  // IO의 threshold 0.6과 같은 기준을 직접 계산 (재확인용. IO는 다시 안 터지므로)
  function ctaInView(el) {
    var r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    var visW = Math.max(0, Math.min(r.right, window.innerWidth) - Math.max(r.left, 0));
    var visH = Math.max(0, Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 0));
    return (visW * visH) / (r.width * r.height) >= 0.6;
  }

  function ctaFire(el) {
    ctaViewed.add(el);
    push("cta_view", { targetLabel: labelOf(el) });
    if (ctaIo) ctaIo.unobserve(el); // 1회면 충분
  }

  // 팝업을 닫으면 그제서야 보이게 된다. IO는 스크롤이 없으면 다시 안 터지므로 주기적으로 재확인한다.
  // 대기 중인 게 없으면 즉시 반환하므로 평소 비용은 사실상 0.
  function ctaRecheck() {
    if (!ctaPending.length) return;
    var still = [];
    for (var i = 0; i < ctaPending.length; i++) {
      var el = ctaPending[i];
      if (ctaViewed.has(el)) continue;
      if (!ctaInView(el)) { still.push(el); continue; } // 화면 밖으로 나감 → 계속 대기
      if (ctaVisibleAt(el)) ctaFire(el);
      else still.push(el); // 아직 가려져 있음
    }
    ctaPending = still;
  }

  function scanCtas() {
    if (!ctaIo || ctaCount >= CTA_MAX) return;
    var els = document.querySelectorAll(CTA_SEL);
    for (var i = 0; i < els.length && ctaCount < CTA_MAX; i++) {
      var el = els[i];
      if (ctaObserved.has(el) || isIgnored(el) || !isCta(el)) continue;
      ctaObserved.add(el);
      ctaCount++;
      ctaIo.observe(el);
    }
    // 상한에 도달하면 더 볼 필요가 없다
    if (ctaCount >= CTA_MAX && ctaMo) ctaMo.disconnect();
  }

  try {
    ctaIo = new IntersectionObserver(
      function (entries) {
        for (var i = 0; i < entries.length; i++) {
          var en = entries[i];
          if (!en.isIntersecting || ctaViewed.has(en.target)) continue;
          if (ctaVisibleAt(en.target)) {
            ctaFire(en.target);
          } else if (ctaPending.indexOf(en.target) < 0) {
            ctaPending.push(en.target); // 팝업 등에 가려짐 → 닫히면 그때 기록
          }
        }
      },
      { threshold: 0.6 }
    );
    // 가려져 대기 중인 CTA를 다시 확인 (팝업이 닫히는 시점을 잡는다)
    setInterval(ctaRecheck, 2000);

    scanCtas();
    // GTM은 페이지 초반에 스크립트를 넣기도 한다. 그 시점엔 DOM이 비어 있어 위 스캔이 0건일 수 있으므로
    // DOM 완성 시점과 로드 완료 시점에 다시 훑는다.
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scanCtas);
    window.addEventListener("load", scanCtas);
    // 비동기로 나중에 그려지는 버튼도 관찰 (과도한 스캔을 막으려 디바운스)
    var ctaTick = 0;
    ctaMo = new MutationObserver(function () {
      clearTimeout(ctaTick);
      ctaTick = setTimeout(scanCtas, 500);
    });
    ctaMo.observe(document.documentElement, { childList: true, subtree: true });
    // 30초 뒤에는 레이아웃이 안정됐다고 보고 감시를 끈다 (배터리·CPU 보호)
    setTimeout(function () {
      if (ctaMo) ctaMo.disconnect();
    }, 30000);
  } catch (e) {}

  // ---- 모바일 제스처 (탭은 click으로 이미 수집됨. 여기서는 더블탭/줌/스와이프) ----
  function relXY(px, py) {
    var docW = Math.max(document.documentElement.scrollWidth, window.innerWidth);
    var docH = Math.max(document.documentElement.scrollHeight, window.innerHeight);
    return { xRel: Math.min(1, Math.max(0, px / docW)), yRel: Math.min(1, Math.max(0, py / docH)) };
  }
  function touchDist(t1, t2) {
    var dx = t1.pageX - t2.pageX, dy = t1.pageY - t2.pageY;
    return Math.sqrt(dx * dx + dy * dy);
  }
  var swipeStart = null; // {x,y,t}
  var pinch = null; // {startDist,lastDist,mx,my}
  var lastTapT = 0, lastTapX = 0, lastTapY = 0;

  document.addEventListener(
    "touchstart",
    function (e) {
      if (isPasswordArea(e.target) || isIgnored(e.target)) { swipeStart = null; pinch = null; return; }
      if (e.touches.length === 1) {
        var t = e.touches[0];
        swipeStart = { x: t.pageX, y: t.pageY, t: Date.now() };
      } else if (e.touches.length === 2) {
        var a = e.touches[0], b = e.touches[1];
        pinch = { startDist: touchDist(a, b), lastDist: touchDist(a, b), mx: (a.pageX + b.pageX) / 2, my: (a.pageY + b.pageY) / 2 };
        swipeStart = null;
      }
    },
    { passive: true }
  );
  document.addEventListener(
    "touchmove",
    function (e) {
      if (pinch && e.touches.length === 2) pinch.lastDist = touchDist(e.touches[0], e.touches[1]);
    },
    { passive: true }
  );
  document.addEventListener(
    "touchend",
    function (e) {
      // 핀치 줌 종료
      if (pinch && e.touches.length < 2) {
        var ratio = pinch.startDist > 0 ? pinch.lastDist / pinch.startDist : 1;
        var c = relXY(pinch.mx, pinch.my);
        if (ratio > 1.15) push("zoom", { xRel: c.xRel, yRel: c.yRel, meta: '{"dir":"in"}' });
        else if (ratio < 0.85) push("zoom", { xRel: c.xRel, yRel: c.yRel, meta: '{"dir":"out"}' });
        pinch = null;
        return;
      }
      // 단일 터치: 스와이프 또는 더블탭
      if (swipeStart) {
        var ch = e.changedTouches[0];
        if (ch) {
          var dx = ch.pageX - swipeStart.x, dy = ch.pageY - swipeStart.y;
          var adx = Math.abs(dx), ady = Math.abs(dy);
          if (Math.max(adx, ady) >= 40) {
            var dir = adx > ady ? (dx > 0 ? "right" : "left") : dy > 0 ? "down" : "up";
            var s = relXY(swipeStart.x, swipeStart.y);
            push("swipe", { xRel: s.xRel, yRel: s.yRel, meta: '{"dir":"' + dir + '"}' });
          } else {
            // 이동이 작으면 탭 → 더블탭 판정
            var now = Date.now();
            if (now - lastTapT < 300 && Math.abs(ch.pageX - lastTapX) < 40 && Math.abs(ch.pageY - lastTapY) < 40) {
              var d = relXY(ch.pageX, ch.pageY);
              push("double_tap", { xRel: d.xRel, yRel: d.yRel });
              lastTapT = 0;
            } else {
              lastTapT = now; lastTapX = ch.pageX; lastTapY = ch.pageY;
            }
          }
        }
        swipeStart = null;
      }
    },
    { passive: true }
  );

  // 이탈 시 flush + session_end
  function endFlush() {
    push("session_end", { scrollPct: maxScroll });
    flush(true);
  }
  window.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") flush(true); });
  window.addEventListener("pagehide", endFlush);
  window.addEventListener("beforeunload", endFlush);

  // 전역 API (수동 전환 이벤트, opt-out)
  window.flowlens = {
    track: function (name, meta) { push("conversion", { targetLabel: mask(name), meta: JSON.stringify(meta || {}) }); flush(false); },
    // 방문자가 추적을 거부. 이후 큐 비우고 전송 중단(다음 로드부터 완전 미수집).
    optOut: function () {
      try { localStorage.setItem("fl_optout", "1"); } catch (e) {}
      queue.length = 0;
      clearInterval(flushTimer);
    },
    optIn: function () { try { localStorage.removeItem("fl_optout"); } catch (e) {} },
  };
})();
