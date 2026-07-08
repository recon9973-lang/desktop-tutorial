/* MERIDIAN® — interactions (vanilla, dependency-free) */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(pointer: fine)').matches;

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

  /* ---- Scroll reveal ---- */
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('[data-reveal]').forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll('[data-reveal]').forEach(function (el) { el.classList.add('in'); });
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
