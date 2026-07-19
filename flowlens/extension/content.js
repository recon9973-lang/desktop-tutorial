// FlowLens 히트맵 오버레이 콘텐츠 스크립트.
// 현재 페이지 문서 크기에 맞춰 캔버스를 덮고, FlowLens /api/overlay에서
// 클릭 좌표(0~1 상대값)를 받아 실제 페이지 위에 열지도로 그린다.
(function () {
  if (window.__flOverlayInit) return; // 중복 주입 방지 (리스너는 1회만)
  window.__flOverlayInit = true;

  const CANVAS_ID = "__flowlens_heat_canvas";

  function palette(t) {
    const stops = [
      [0.0, [59, 130, 246]],
      [0.35, [34, 197, 94]],
      [0.65, [234, 179, 8]],
      [1.0, [239, 68, 68]],
    ];
    for (let i = 1; i < stops.length; i++) {
      if (t <= stops[i][0]) {
        const [t0, c0] = stops[i - 1];
        const [t1, c1] = stops[i];
        const f = (t - t0) / (t1 - t0);
        return [0, 1, 2].map((k) => Math.round(c0[k] + (c1[k] - c0[k]) * f));
      }
    }
    return stops[stops.length - 1][1];
  }

  function draw(points) {
    remove();
    const w = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, window.innerWidth);
    const h = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, window.innerHeight);
    const canvas = document.createElement("canvas");
    canvas.id = CANVAS_ID;
    canvas.width = w;
    canvas.height = h;
    canvas.style.cssText = `position:absolute;left:0;top:0;width:${w}px;height:${h}px;pointer-events:none;z-index:2147483000;`;
    document.body.appendChild(canvas);
    const ctx = canvas.getContext("2d");
    const radius = Math.max(20, w * 0.02);

    for (const p of points) {
      const px = p.x * w;
      const py = p.y * h;
      const g = ctx.createRadialGradient(px, py, 0, px, py, radius);
      g.addColorStop(0, "rgba(0,0,0,0.10)");
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
    }
    const img = ctx.getImageData(0, 0, w, h);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const a = d[i + 3];
      if (a === 0) continue;
      const [r, gg, b] = palette(Math.min(1, a / 255));
      d[i] = r;
      d[i + 1] = gg;
      d[i + 2] = b;
      d[i + 3] = Math.min(210, 60 + a * 1.6);
    }
    ctx.putImageData(img, 0, 0);
  }

  // 스크롤맵: 도달 밴드를 페이지 위에 반투명 가로 띠로 그리고 평균 폴드 라인 표시
  function drawScroll(bands, avgFold) {
    remove();
    const w = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, window.innerWidth);
    const h = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, window.innerHeight);
    const layer = document.createElement("div");
    layer.id = CANVAS_ID;
    layer.style.cssText = `position:absolute;left:0;top:0;width:${w}px;height:${h}px;pointer-events:none;z-index:2147483000;`;
    for (const b of bands) {
      const t = b.pct / 100;
      const strip = document.createElement("div");
      const r = 255, g = Math.round(120 + (1 - t) * 110), bl = Math.round(60 + (1 - t) * 150);
      strip.style.cssText = `position:absolute;left:0;width:100%;top:${b.from}%;height:10%;background:rgba(${r},${g},${bl},${0.18 + t * 0.5});border-bottom:1px solid rgba(255,255,255,.4);display:flex;align-items:center;justify-content:flex-end;padding-right:12px;font:600 12px -apple-system,sans-serif;color:#20242e;`;
      strip.textContent = `${b.from}~${b.to}% · ${b.pct}% 도달`;
      layer.appendChild(strip);
    }
    // 평균 폴드 라인
    const foldTop = Math.min(h - 2, avgFold || 800);
    const fold = document.createElement("div");
    fold.style.cssText = `position:absolute;left:0;width:100%;top:${foldTop}px;border-top:2px dashed #12141d;`;
    fold.innerHTML = `<span style="position:absolute;right:12px;top:-11px;background:#12141d;color:#fff;font:600 11px sans-serif;padding:2px 8px;border-radius:6px;">Average Fold ≈ ${avgFold}px</span>`;
    layer.appendChild(fold);
    document.body.appendChild(layer);
  }

  function remove() {
    const el = document.getElementById(CANVAS_ID);
    if (el) el.remove();
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type !== "FL_TOGGLE") return;
    if (document.getElementById(CANVAS_ID)) {
      remove();
      sendResponse({ on: false });
      return;
    }
    const mode = msg.mode || "heat";
    // token: 사이트별 비밀 토큰 (쿠키는 SameSite=Lax라 확장에서 전달되지 않으므로 토큰으로 인증)
    const u = `${msg.origin}/api/overlay?site=${encodeURIComponent(msg.siteKey)}&token=${encodeURIComponent(msg.token || "")}&path=${encodeURIComponent(location.pathname)}&mode=${mode}&gesture=${msg.gesture}&period=${msg.period || 0}&device=${encodeURIComponent(msg.device || "DESKTOP")}`;
    fetch(u)
      .then((r) => r.json())
      .then((data) => {
        if (!data.ok) {
          sendResponse({ on: false, count: 0 });
          return;
        }
        if (mode === "scroll") {
          drawScroll(data.bands || [], data.avgFold || 800);
          sendResponse({ on: true });
        } else {
          draw(data.points || []);
          sendResponse({ on: true, count: data.count });
        }
      })
      .catch(() => sendResponse({ on: false, count: 0 }));
    return true; // 비동기 응답
  });
})();
