/* ── 골든 링 로딩 (RingLoader) ───────────────────────────────────────────────
   컨테이너의 기존 내용(결과 스켈레톤·표)을 blur(10px)+거의 검정 스크림(.rl-scrim)으로 깔고, 그 위 오버레이에 링(screen 블렌드·경과초) + 한 줄 캡션만 띄운다.
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

  // 영상 요소 못(pool) — 통이 지워져 재마운트될 때마다 <video> 를 새로 만들면 파일을 다시 받고
  // 디코더를 다시 세우느라 그동안 링이 정지 사진으로 서 있는다. 진단 3단계가 딱 그 자리다
  // (index.html 의 `if(stage===1||stage===3) el.innerHTML=''`).
  //   [실측 2026-09-10 · 크로뮴 · 캐시 없음 · 4G]
  //     1단계 마운트   링이 돌기까지 210ms   평상시 한 칸(49.9ms)의 4배
  //     3단계 재마운트 링이 돌기까지 224ms   평상시 한 칸의 4배     ← 「이어지는 지점에서 멈칫」
  //     2단계 캡션만   끊김 24ms            멀쩡 — 재마운트가 아닌 것이 증거다
  //   사파리·아이폰은 H.264 디코더를 새로 세워야 해서 이보다 더 걸린다.
  // 그래서 버리지 않고 못에 넣었다가 다시 꺼내 쓴다. 받아 둔 데이터가 남아 있어 즉시 돈다.
  // 로더가 동시에 둘 뜰 수 있어(진단 본문 + AI 노출 매트릭스) 못은 둘까지 잡아 둔다.
  var pool = [];
  function takeVideo(){
    var v = pool.pop();
    if (v) return v;
    v = document.createElement('video');
    v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true;
    v.setAttribute('playsinline', ''); v.setAttribute('muted', '');
    v.preload = 'auto'; v.setAttribute('aria-hidden', 'true');
    // 등속 순환 소스 — 원본은 15초짜리 「한 번 재생용」 인트로 렌더라 앞 1.7초·뒤 0.3초가
    // 거의 정지해 있었다(한 바퀴의 13%). 그래서 링이 서다가 톡 튀고 다시 출발했다.
    // 프레임을 「이동량이 일정하도록」 다시 골라(361 → 164프레임 6.834초) 등속으로 만들었다.
    //   ① 멈추는 칸이 없다 — 164칸 전부 움직인다(가장 느린 칸도 가장 빠른 칸의 0.39배).
    //   ② 되감기 한 칸이 정상 한 칸의 1.4배까지 내려왔다(원본은 그 자리 정상 한 칸의 11배).
    //   ③ 정지 구간을 걷어내 파일이 오히려 작아졌다(webm 800KB → 461KB).
    // 고른 프레임은 전부 원본 프레임 그대로다(프레임 해시 164개 대조 · 보간·색공간 왕복 없음).
    // 원본 15초 소스로 되돌리려면 -loop 를 뺀 ring-sq.webm / ring-sq.mp4 로 바꾸면 된다.
    // **mp4 를 먼저 적는다.** 브라우저는 틀 수 있는 첫 source 를 고른다.
    // 예전엔 webm(VP9)이 먼저였는데, iOS 17 부터 사파리가 VP9 을 「틀 수는 있다」고 답한다 —
    // 그런데 아이폰에 VP9 하드웨어 디코더는 없어서 640×640 을 **CPU 로** 푼다. 그러면 배터리와
    // 다른 일에 밀려 주기적으로 칸을 거른다. mp4 는 H.264 High 3.1 이라 모든 아이폰이 칩으로
    // 푼다. 크롬·안드로이드도 H.264 는 칩으로 푼다.
    // **그림은 한 픽셀도 안 바뀐다** — 같은 164칸을 담은 같은 영상이고, 둘 다 등속 41.7ms 다
    // (webm·mp4 둘 다 확인). 값은 내려받기 471KB → 601KB, 130KB 더.
    // 되돌리기: 아래 두 source 순서를 도로 바꾸면 된다.
    v.innerHTML = '<source src="' + ASSET + 'ring-sq-loop.mp4" type="video/mp4"><source src="' + ASSET + 'ring-sq-loop.webm" type="video/webm">';
    // 표시 전환은 「진짜 그림이 있을 때」만. 듣는 자리는 만들 때 한 번만 건다(재사용해도 안 쌓인다).
    var mark = function(){
      if (!(v.videoWidth > 0)) return;
      v.classList.add('playing');
      var d = v.parentNode; if (d && d.classList) d.classList.add('live');
    };
    v.__rlMark = mark;
    v.addEventListener('playing', mark); v.addEventListener('loadeddata', mark);
    return v;
  }
  function releaseVideo(v){
    if (!v) return;
    try { v.pause(); } catch (e) {}
    if (v.parentNode) v.parentNode.removeChild(v);
    v.classList.remove('playing');
    if (pool.length < 2) pool.push(v);
  }
  // 미리 받아 둔다 — 첫 마운트의 210ms 도 없애려면 사장님이 진단 폼을 만질 때 불러 준다.
  function warm(){
    if (REDUCED || pool.length) return;
    var v = takeVideo();
    try { v.load(); } catch (e) {}
    pool.push(v);
  }

  /* ── 멈춤 감시 ───────────────────────────────────────────────────────────
     사장님이 세 번 «시작 1초 · 끝 1초 멈춤» 을 말씀하셨는데 크로뮴에서는 재현이 안 된다
     (시작 2ms · 되감기 1.63배 · webm/mp4 둘 다 등속 164칸 41.7ms · 블러 전환 33ms).
     남은 자리는 전부 이 방이 못 재는 곳이다 — 아이폰 저전력 모드(영상 자동재생을 막는다),
     사파리 VP9 소프트웨어 디코딩, 순환 이음매.

     그래서 **원인을 가리지 않는다.** 링이 실제로 멈췄는지만 본다: 재생 머리가 안 나아가면
     멈춘 것이다. 멈추면 영상을 접고 셰이더로 넘긴다 — 셰이더는 시간을 넣으면 그 순간을
     계산해 내므로 **멈출 수 있는 지점 자체가 없다**(내려받기도 디코더도 없다).

     **다만 아무 때나 갈아타지 않는다.** 셰이더는 나란히 놓으면 확실히 못하다 — 실 가닥이
     줄고(단면 봉우리 8.8 → 0.7) 같은 틴트 아래에서 더 흐리다. 잠깐 멈칫할 때마다 갈아타면
     **한 번 멈칫한 대가로 남은 내내 못한 링**을 보게 된다. 그건 손해다.

     그래서 조건을 하나로 좁혔다 — **영상이 한 프레임도 못 낸 경우.** 아이폰 저전력 모드가
     자동재생을 막는 자리가 여기다. 그때 대안은 「멈춘 링」이 아니라 정지 사진 한 장이
     14초에 한 바퀴 뻣뻣하게 도는 것이고, 거기서는 셰이더가 분명히 낫다.
     한 번이라도 제대로 돌기 시작했으면 중간에 멈칫해도 **그대로 둔다.**
     되돌리기: 이 블록과 mount() 안의 watchStall(st) 한 줄을 지우면 끝이다. */
  var SHADER_SRC = '/assets/ring-shader.js';
  var NEVER_MS = 1600;  // 이만큼 지나도 첫 프레임이 없으면 「못 트는 것」이다(늦는 것이 아니라).

  function loadShader(cb){
    if (global_RingShader()) return cb();
    var s = document.createElement('script');
    s.src = SHADER_SRC; s.async = true;
    s.onload = function(){ cb(); };
    s.onerror = function(){ /* 못 받으면 그냥 둔다 — 지금보다 나빠지지 않는다 */ };
    document.head.appendChild(s);
  }
  function global_RingShader(){ return window.RingShader && window.RingShader.make; }

  function toShader(st){
    loadShader(function(){
      if (!global_RingShader() || !st.overlay || !st.overlay.isConnected) return;
      var disc = st.overlay.querySelector('.rl-disc');
      if (!disc || disc.querySelector('canvas')) return;
      var c = document.createElement('canvas');
      c.setAttribute('aria-hidden', 'true');
      disc.appendChild(c);
      var r = window.RingShader.make(c, {});
      if (!r) { disc.removeChild(c); return; }
      r.start();
      st.shader = r;
      c.classList.add('playing');
      disc.classList.add('live');
      // 영상은 접는다 — 멈춘 그림이 셰이더 위에 겹쳐 밝기를 더하면 안 된다.
      if (st.video) { try { st.video.pause(); } catch (e) {} st.video.classList.remove('playing'); }
    });
  }

  function watchStall(st){
    if (REDUCED || !st.video) return;
    var v = st.video, waited = 0;
    st.stall = setInterval(function(){
      if (!st.overlay || !st.overlay.isConnected || st.shader) { clearInterval(st.stall); st.stall = null; return; }
      // 한 프레임이라도 나왔으면 영상은 「틀 수 있는 것」이다 — 감시를 접고 그대로 둔다.
      if (v.currentTime > 0 || v.classList.contains('playing')) { clearInterval(st.stall); st.stall = null; return; }
      if (document.hidden) { waited = 0; return; }   // 탭이 뒤로 가 있으면 안 트는 게 맞다
      waited += 200;
      if (waited >= NEVER_MS) { clearInterval(st.stall); st.stall = null; toShader(st); }
    }, 200);
  }

  function buildOverlay(st){
    var ov = document.createElement('div'); ov.className = 'rl-overlay';
    ov.setAttribute('role', 'status'); ov.setAttribute('aria-live', 'polite');
    var disc = document.createElement('div'); disc.className = 'rl-disc';
    // 정지 사진(포스터)을 깔지 않는다 — 사장님 오더. 영상이 뜨기 전 잠깐이라도 「멈춘 링」을
    // 보이느니 아무것도 안 보이는 편이 낫다. 진단 페이지를 열 때 영상을 미리 받아 두므로
    // 그 잠깐은 19ms 다(실측·4G·캐시 없음). 못 뜨면 1.6초 뒤 셰이더가 대신 돈다.
    var scrim = document.createElement('div'); scrim.className = 'rl-scrim'; scrim.setAttribute('aria-hidden', 'true');
    if (!REDUCED) {
      var v = takeVideo();
      disc.appendChild(v);
      // 못에서 꺼낸 것은 이미 받아 둔 상태다 — 곧바로 보이게 넘긴다.
      v.__rlMark();
      st.video = v;
    }
    var sec = document.createElement('div'); sec.className = 'rl-sec';
    sec.innerHTML = '<span data-sec>0</span><small>SEC</small>';
    disc.appendChild(sec);
    var cap = document.createElement('p'); cap.className = 'rl-cap'; cap.setAttribute('data-cap', '');
    ov.appendChild(disc); ov.appendChild(cap);
    st.scrim = scrim; st.overlay = ov; st.cap = cap; st.secEl = sec.firstChild;
  }

  function clearTimers(st){
    if (st.timer) clearInterval(st.timer);
    if (st.leaveTimer) clearTimeout(st.leaveTimer);
    if (st.stall) clearInterval(st.stall);
    if (st.shader) { try { st.shader.stop(); } catch (e) {} st.shader = null; }
    st.timer = st.leaveTimer = st.stall = null;
  }
  function teardownNow(host){
    var st = host._rl; if (!st) return;
    clearTimers(st);
    releaseVideo(st.video);
    if (st.scrim && st.scrim.parentNode) st.scrim.parentNode.removeChild(st.scrim);
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
    host.appendChild(st.scrim); host.appendChild(st.overlay);   // 스크림 → 오버레이 순(DOM 순서 = 쌓임 순, z-index 없음)
    host.classList.add('rl-host', 'rl-' + flow);
    host._rl = st;
    st.cap.textContent = opts.caption || '';
    st.secEl.textContent = String(Math.floor((Date.now() - st.t0) / 1000));
    st.timer = setInterval(function(){
      if (!st.overlay.isConnected) { clearInterval(st.timer); return; }   // innerHTML 로 지워져도 타이머 누수 없음
      st.secEl.textContent = String(Math.floor((Date.now() - st.t0) / 1000));
    }, 250);
    if (st.video) { try { var p = st.video.play(); if (p && p.catch) p.catch(function(){}); } catch (e) {} }
    watchStall(st);   // 링이 실제로 멈추면 셰이더로 넘긴다(위 머리말)
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
    if (html != null) { host.innerHTML = html; host.appendChild(st.scrim); host.appendChild(st.overlay); }  // 결과를 먼저 깔고(블러 상태) 그 위에서 페이드아웃
    // 페이드아웃 300ms 동안은 계속 돌게 둔다 — 여기서 세우면 사라지는 내내 정지 화면이다.
    host.classList.add('rl-leaving');   // 오버레이 페이드아웃 + 블러 0 (300ms)
    st.leaveTimer = setTimeout(function(){ if (host._rl === st) teardownNow(host); }, REDUCED ? 0 : 300);
  }

  window.RingLoader = { mount: mount, caption: caption, done: done, warm: warm };
})();
