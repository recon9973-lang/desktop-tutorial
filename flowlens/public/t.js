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
    // 고객이 지정한 안전 라벨(data-fl-label) 우선, 없으면 aria-label/텍스트
    var txt = el.getAttribute("data-fl-label") || el.getAttribute("aria-label") || el.textContent || el.getAttribute("alt") || "";
    return mask(txt);
  }

  // 고객이 수집 제외로 지정한 영역([data-fl-ignore], .fl-sensitive)
  function isIgnored(el) {
    var n = el;
    for (var i = 0; i < 6 && n; i++) {
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
      push(type, { xRel: c.xRel, yRel: c.yRel, scrollPct: maxScroll, targetLabel: labelOf(el) });
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

  // CTA 노출 (버튼/주요 링크가 뷰포트에 들어오면 1회 cta_view)
  try {
    var seen = new WeakSet();
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting && !seen.has(en.target)) {
            seen.add(en.target);
            push("cta_view", { targetLabel: labelOf(en.target) });
          }
        });
      },
      { threshold: 0.6 }
    );
    // 대표 CTA 후보: 버튼, 주요 링크
    document.querySelectorAll("button, a.btn, .cta, [data-cta]").forEach(function (el) { io.observe(el); });
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
