/* MERIDIAN® — interactions (vanilla, dependency-free) */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(pointer: fine)').matches;

  /* ---- Intro preloader: black + text, then curtain slides up ---- */
  var pl = document.querySelector('.preloader');
  if (pl) {
    var seen = false;
    try { seen = sessionStorage.getItem('venomIntro') === '1'; } catch (e) {}
    if (reduce || seen) {
      pl.classList.add('hidden');
    } else {
      document.body.classList.add('intro-lock');
      try { sessionStorage.setItem('venomIntro', '1'); } catch (e) {}
      var finish = function () {
        pl.classList.add('done');
        document.body.classList.remove('intro-lock');
        window.scrollTo(0, 0);
        setTimeout(function () { pl.classList.add('hidden'); }, 1100);
      };
      // hold the intro ~1.6s after the window finishes loading
      if (document.readyState === 'complete') {
        setTimeout(finish, 1600);
      } else {
        window.addEventListener('load', function () { setTimeout(finish, 1600); });
        // safety cap so the intro never gets stuck
        setTimeout(finish, 4000);
      }
    }
  }

  /* ---- Sticky header: hide on scroll-down, solid after hero ---- */
  var header = document.querySelector('.site-header');
  var lastY = 0;
  function onScroll() {
    var y = window.scrollY;
    if (header) {
      header.classList.toggle('solid', y > 40);
      if (y > lastY && y > 400 && !document.body.classList.contains('menu-open')) {
        header.classList.add('hide');
      } else {
        header.classList.remove('hide');
      }
    }
    lastY = y;
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ---- Menu overlay ---- */
  var menuBtn = document.querySelector('.menu-btn');
  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      document.body.classList.toggle('menu-open');
    });
    document.querySelectorAll('.overlay nav a').forEach(function (a) {
      a.addEventListener('click', function () { document.body.classList.remove('menu-open'); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') document.body.classList.remove('menu-open');
    });
  }

  /* ---- Scroll reveal / mask / desat + count-up ---- */
  function runCount(el) {
    var target = parseFloat(el.getAttribute('data-count')) || 0;
    var suf = el.getAttribute('data-suffix') || '';
    var dur = 1500, s = null;
    function step(ts) {
      if (!s) s = ts;
      var p = Math.min(1, (ts - s) / dur);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * e) + suf;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var revealSel = '[data-reveal],[data-mask],[data-desat]';
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.14, rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll(revealSel).forEach(function (el) { io.observe(el); });

    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && !en.target.dataset.done) {
          en.target.dataset.done = '1'; runCount(en.target); co.unobserve(en.target);
        }
      });
    }, { threshold: 0.6 });
    document.querySelectorAll('[data-count]').forEach(function (el) { co.observe(el); });
  } else {
    document.querySelectorAll(revealSel).forEach(function (el) { el.classList.add('in'); });
    document.querySelectorAll('[data-count]').forEach(function (el) {
      el.textContent = (el.getAttribute('data-count') || '') + (el.getAttribute('data-suffix') || '');
    });
  }

  /* ---- Parallax (scroll-linked translate on .parallax > .p-media) ---- */
  var pxEls = Array.prototype.slice.call(document.querySelectorAll('.parallax'));
  if (pxEls.length && !reduce) {
    var pTick = false;
    function px() {
      var vh = window.innerHeight;
      pxEls.forEach(function (el) {
        var m = el.querySelector('.p-media'); if (!m) return;
        var r = el.getBoundingClientRect();
        if (r.bottom < -140 || r.top > vh + 140) return;
        var prog = (r.top + r.height / 2 - vh / 2) / vh;
        var y = Math.max(-1, Math.min(1, prog)) * -40;
        m.style.transform = 'translate3d(0,' + y.toFixed(1) + 'px,0) scale(1.2)';
      });
      pTick = false;
    }
    window.addEventListener('scroll', function () { if (!pTick) { pTick = true; requestAnimationFrame(px); } }, { passive: true });
    window.addEventListener('resize', px);
    px();
  }

  /* ---- Accordion ---- */
  document.querySelectorAll('.acc-item .acc-q').forEach(function (q) {
    q.addEventListener('click', function () {
      var item = q.closest('.acc-item');
      var open = item.classList.contains('open');
      item.parentElement.querySelectorAll('.acc-item.open').forEach(function (o) {
        if (o !== item) o.classList.remove('open');
      });
      item.classList.toggle('open', !open);
      q.setAttribute('aria-expanded', String(!open));
    });
  });

  /* ---- Magnetic buttons (fine pointer only) ---- */
  if (fine && !reduce) {
    document.querySelectorAll('.btn').forEach(function (btn) {
      var strength = 0.35;
      btn.addEventListener('pointermove', function (e) {
        var r = btn.getBoundingClientRect();
        var mx = e.clientX - (r.left + r.width / 2);
        var my = e.clientY - (r.top + r.height / 2);
        btn.style.transform = 'translate(' + mx * strength + 'px,' + (my * strength - 2) + 'px)';
      });
      btn.addEventListener('pointerleave', function () { btn.style.transform = ''; });
    });
  }

  /* ---- Project hover image reveal (desktop) ---- */
  var reveal = document.querySelector('.proj-reveal');
  var revealPh = reveal ? reveal.querySelector('.ph') : null;
  if (reveal && fine && !reduce) {
    document.querySelectorAll('.proj').forEach(function (p) {
      p.addEventListener('pointerenter', function () {
        if (revealPh) revealPh.className = 'ph ' + (p.getAttribute('data-ph') || 'warm');
        reveal.classList.add('on');
      });
      p.addEventListener('pointermove', function (e) {
        reveal.style.left = e.clientX + 'px';
        reveal.style.top = e.clientY + 'px';
      });
      p.addEventListener('pointerleave', function () { reveal.classList.remove('on'); });
    });
  }

  /* ---- Project navigation ---- */
  document.querySelectorAll('.proj[data-href]').forEach(function (p) {
    p.addEventListener('click', function () { window.location.href = p.getAttribute('data-href'); });
  });

  /* ---- Custom cursor ---- */
  if (fine && !reduce) {
    var cur = document.createElement('div');
    cur.className = 'cursor';
    document.body.appendChild(cur);
    var cx = 0, cy = 0, tx = 0, ty = 0;
    window.addEventListener('pointermove', function (e) { tx = e.clientX; ty = e.clientY; });
    (function loop() {
      cx += (tx - cx) * 0.2; cy += (ty - cy) * 0.2;
      cur.style.transform = 'translate(' + cx + 'px,' + cy + 'px) translate(-50%,-50%)';
      requestAnimationFrame(loop);
    })();
    document.querySelectorAll('a,button,.proj,.btn').forEach(function (el) {
      el.addEventListener('pointerenter', function () { cur.classList.add('grow'); });
      el.addEventListener('pointerleave', function () { cur.classList.remove('grow'); });
    });
  }

  /* ---- Newsletter (front-end only demo) ---- */
  var form = document.querySelector('.form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('.btn');
      if (btn) { btn.textContent = 'Subscribed ✓'; btn.disabled = true; }
    });
  }
})();
