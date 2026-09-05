/* ── 골든 링 로딩 (RingLoader) ───────────────────────────────────────────────
   컨테이너의 기존 내용(결과 스켈레톤·표)을 blur(10px)+스크림으로 깔고, 가운데 링 원반(경과초) + 아래 한 줄 캡션만 띄운다.
   API
     RingLoader.mount(el, {flow:'seo'|'aeo', caption})   — 이미 떠 있으면 캡션만 갱신(경과초 유지). 내용이 지워진 뒤 재호출해도 경과초는 이어진다.
     RingLoader.caption(el, text)                        — 단계 갱신 = 캡션 교체
     RingLoader.done(el[, html])                         — (html 있으면 먼저 채우고) 300ms 페이드아웃 + 블러 해제 → 제거
   되돌리기: index.html 의 <link>·<script defer> 두 줄 삭제. 이 파일과 /assets/ring/ 만 격리돼 있다. */
(function(){
  'use strict';
  var ASSET = '/assets/ring/';
  var REDUCED = false;
  try { REDUCED = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) {}

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // 언더레이가 비어 있을 때만: 흐려질 최소 스켈레톤(수치 없음)
  function skeleton(flow){
    if (flow === 'aeo') {
      return '<div class="rl-sk"><div class="rl-sk-box"><div class="rl-sk-line w60"></div></div>'
        + '<div class="rl-sk-box"><div class="rl-sk-line w80"></div><div class="rl-sk-line"></div><div class="rl-sk-line w45"></div><div class="rl-sk-line w80"></div></div></div>';
    }
    var rows = ['콘텐츠 & 메타', '기술·크롤링', '신뢰·전문성', '검색 노출 강화', '콘텐츠 최적화', '보안', '속도'], w = [78, 64, 52, 70, 61, 88, 0];
    return '<div class="rl-sk">' + rows.map(function(r, i){ return '<div class="rl-sk-row">' + esc(r) + '<span class="rl-sk-bar"><i style="width:' + w[i] + '%"></i></span><em>—</em></div>'; }).join('') + '</div>';
  }

  function buildOverlay(st){
    var ov = document.createElement('div'); ov.className = 'rl-overlay';
    ov.setAttribute('role', 'status'); ov.setAttribute('aria-live', 'polite');
    var disc = document.createElement('div'); disc.className = 'rl-disc';
    disc.innerHTML = '<img class="still" src="' + ASSET + 'ring-sq.jpg" alt="" aria-hidden="true">';
    if (!REDUCED) {
      var v = document.createElement('video');
      v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true; v.setAttribute('playsinline', ''); v.setAttribute('muted', '');
      v.preload = 'auto'; v.setAttribute('aria-hidden', 'true');
      v.innerHTML = '<source src="' + ASSET + 'ring-sq.webm" type="video/webm"><source src="' + ASSET + 'ring-sq.mp4" type="video/mp4">';
      var ok = function(){ if (v.videoWidth > 0) v.classList.add('playing'); };
      v.addEventListener('playing', ok); v.addEventListener('loadeddata', ok);
      disc.appendChild(v);
      st.video = v;
    }
    var sec = document.createElement('div'); sec.className = 'rl-sec';
    sec.innerHTML = '<span data-sec>0</span><small>SEC</small>';
    disc.appendChild(sec);
    var cap = document.createElement('p'); cap.className = 'rl-cap'; cap.setAttribute('data-cap', '');
    ov.appendChild(disc); ov.appendChild(cap);
    st.overlay = ov; st.cap = cap; st.secEl = sec.firstChild;
  }

  function clearTimers(st){
    if (st.timer) clearInterval(st.timer);
    if (st.leaveTimer) clearTimeout(st.leaveTimer);
    st.timer = st.leaveTimer = null;
  }
  function teardownNow(host){
    var st = host._rl; if (!st) return;
    clearTimers(st);
    if (st.video) { try { st.video.pause(); } catch (e) {} }
    if (st.overlay && st.overlay.parentNode) st.overlay.parentNode.removeChild(st.overlay);
    host.classList.remove('rl-host', 'rl-seo', 'rl-aeo', 'rl-leaving');
    host._rl = null;
  }

  function mount(host, opts){
    if (!host) return null;
    opts = opts || {};
    var flow = opts.flow === 'aeo' ? 'aeo' : 'seo';
    var prev = host._rl;
    // 떠 있는 채로 재호출: 캡션·flow만 갱신
    if (prev && !prev.leaving && prev.overlay.isConnected) {
      host.classList.remove('rl-seo', 'rl-aeo'); host.classList.add('rl-' + flow);
      if (opts.caption != null) prev.cap.textContent = opts.caption;
      return host;
    }
    var st = { host: host, flow: flow, t0: (prev && !prev.leaving) ? prev.t0 : Date.now() }; // 내용이 지워져 재마운트되면 경과초 유지
    if (prev) teardownNow(host);
    if (!host.firstElementChild) host.innerHTML = skeleton(flow);
    buildOverlay(st);
    host.appendChild(st.overlay);
    host.classList.add('rl-host', 'rl-' + flow);
    host._rl = st;
    st.cap.textContent = opts.caption || '';
    st.secEl.textContent = String(Math.floor((Date.now() - st.t0) / 1000));
    st.timer = setInterval(function(){
      if (!st.overlay.isConnected) { clearInterval(st.timer); return; }   // innerHTML 로 지워져도 타이머 누수 없음
      st.secEl.textContent = String(Math.floor((Date.now() - st.t0) / 1000));
    }, 250);
    if (st.video) { try { var p = st.video.play(); if (p && p.catch) p.catch(function(){}); } catch (e) {} }
    return host;
  }

  function caption(host, text){
    var st = host && host._rl; if (!st || st.leaving) return;
    st.cap.textContent = text == null ? '' : String(text);
  }

  function done(host, html){
    if (!host) return;
    var st = host._rl;
    if (!st) { if (html != null) host.innerHTML = html; return; }
    if (st.leaving) { if (html != null) { host.innerHTML = html; teardownNow(host); } return; }
    st.leaving = true;
    if (st.timer) clearInterval(st.timer);
    if (html != null) { host.innerHTML = html; host.appendChild(st.overlay); }  // 결과를 먼저 깔고(블러 상태) 그 위에서 페이드아웃
    if (st.video) { try { st.video.pause(); } catch (e) {} }
    host.classList.add('rl-leaving');   // 오버레이 페이드아웃 + 블러 0 (300ms)
    st.leaveTimer = setTimeout(function(){ if (host._rl === st) teardownNow(host); }, REDUCED ? 0 : 300);
  }

  window.RingLoader = { mount: mount, caption: caption, done: done };
})();
