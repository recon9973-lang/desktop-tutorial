/**
 * Venom Theme — main.js
 */
(function () {
  'use strict';

  /* ── Lucide 아이콘 초기화 ─────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) lucide.createIcons();

    initMobileMenu();
    initBackToTop();
    initHeaderScroll();
    initSitemapHighlight();
    initAnimateOnScroll();
    initContactForm();
    initCountUp();
    initHeroFx();
    initMagnetic();
  });

  const REDUCE = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FINE   = window.matchMedia('(pointer: fine)').matches;

  /* ── 모바일 메뉴 ──────────────────────────── */
  function initMobileMenu() {
    const btn     = document.getElementById('hamburgerBtn');
    const menu    = document.getElementById('mobileMenu');
    const overlay = document.getElementById('mobileOverlay');
    const close   = document.getElementById('mobileMenuClose');
    if (!btn) return;

    function openMenu() {
      menu.classList.add('open');
      overlay.classList.add('open');
      btn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }
    function closeMenu() {
      menu.classList.remove('open');
      overlay.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    btn.addEventListener('click', openMenu);
    close.addEventListener('click', closeMenu);
    overlay.addEventListener('click', closeMenu);
    document.addEventListener('keydown', e => e.key === 'Escape' && closeMenu());
  }

  /* ── 헤더 스크롤 효과 ─────────────────────── */
  function initHeaderScroll() {
    const header = document.getElementById('siteHeader');
    if (!header) return;
    let last = 0;
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      header.classList.toggle('scrolled', y > 40);
      last = y;
    }, { passive: true });
  }

  /* ── 맨 위로 버튼 ─────────────────────────── */
  function initBackToTop() {
    const btn = document.getElementById('backToTop');
    if (!btn) return;
    window.addEventListener('scroll', () => {
      btn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  /* ── 좌측 사이트맵 현재 위치 강조 ───────────── */
  function initSitemapHighlight() {
    const links = document.querySelectorAll('.sitemap-l1 a, .sitemap-l2 a, .sitemap-l3 a');
    const path  = window.location.pathname;
    links.forEach(a => {
      try {
        const href = new URL(a.href).pathname;
        if (href === path || (href !== '/' && path.startsWith(href))) {
          a.classList.add('active');
        }
      } catch (_) {}
    });
  }

  /* ── 스크롤 시 요소 등장 애니메이션 ──────────── */
  function initAnimateOnScroll() {
    const els = document.querySelectorAll('.service-card, .ai-card, .pricing-card, .blog-card, .process-step, .testimonial-card');
    if (!els.length) return;

    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('animate-in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });

    els.forEach(el => {
      el.style.opacity = '0';
      io.observe(el);
    });
  }

  /* ── 문의 폼 AJAX 제출 ────────────────────── */
  function initContactForm() {
    const form = document.getElementById('venomContactForm');
    if (!form) return;

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      const msg = document.getElementById('formMessage');
      btn.disabled = true;
      btn.textContent = '전송 중...';

      const data = new FormData(form);
      data.append('action', 'venom_contact');
      data.append('nonce', venomData.nonce);

      try {
        const res  = await fetch(venomData.ajaxUrl, { method: 'POST', body: data });
        const json = await res.json();
        if (json.success) {
          msg.textContent = json.data.message;
          msg.style.color = 'var(--color-primary)';
          form.reset();
        } else {
          msg.textContent = json.data.message || '오류가 발생했습니다. 다시 시도해 주세요.';
          msg.style.color = 'var(--color-ruby)';
        }
      } catch (_) {
        msg.textContent = '네트워크 오류가 발생했습니다.';
        msg.style.color = 'var(--color-ruby)';
      } finally {
        btn.disabled = false;
        btn.textContent = '상담 신청하기';
        msg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  }

  /* ── 숫자 카운트업 (히어로 스탯) ──────────────── */
  function initCountUp() {
    const nums = document.querySelectorAll('.stat-number[data-count]');
    if (!nums.length || REDUCE) {
      nums.forEach(el => { el.firstChild && (el.firstChild.textContent = el.getAttribute('data-count')); });
      return;
    }
    const run = el => {
      const target = parseFloat(el.getAttribute('data-count')) || 0;
      const dec = target % 1 !== 0 ? 1 : 0;
      const suffix = el.querySelector('.stat-suffix');
      const dur = 1500;
      let s = null;
      const step = ts => {
        if (!s) s = ts;
        const p = Math.min(1, (ts - s) / dur);
        const e = 1 - Math.pow(1 - p, 3);
        el.childNodes[0].textContent = (target * e).toFixed(dec);
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      void suffix;
    };
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (en.isIntersecting && !en.target.dataset.done) {
          en.target.dataset.done = '1'; run(en.target); io.unobserve(en.target);
        }
      });
    }, { threshold: 0.6 });
    nums.forEach(el => io.observe(el));
  }

  /* ── 히어로: ECG→성장곡선 캔버스 + 흑백↔컬러 ──── */
  function initHeroFx() {
    // 흑백 → 컬러 (뷰에 들어올 때마다 반복)
    const media = document.querySelector('.hero-visual');
    if (media && 'IntersectionObserver' in window && !REDUCE) {
      new IntersectionObserver(es => {
        es.forEach(e => media.classList.toggle('color', e.isIntersecting));
      }, { threshold: 0.15 }).observe(media);
    } else if (media) {
      media.classList.add('color');
    }

    // ECG 캔버스
    const cv = document.getElementById('venomEcg');
    if (!cv || REDUCE) return;
    const ctx = cv.getContext('2d');
    const DPR = Math.min(2, window.devicePixelRatio || 1);
    let W, H, t = 0;
    const size = () => {
      const r = cv.getBoundingClientRect();
      W = r.width; H = r.height;
      cv.width = W * DPR; cv.height = H * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    };
    size(); window.addEventListener('resize', size);
    const beat = x => {
      if (x < 0.12) return Math.sin(x / 0.12 * Math.PI) * 0.08;
      if (x < 0.18) return -0.06;
      if (x < 0.22) return 0.95 * ((x - 0.18) / 0.04);
      if (x < 0.27) return 0.95 - 1.25 * ((x - 0.22) / 0.05);
      if (x < 0.32) return -0.30 + 0.30 * ((x - 0.27) / 0.05);
      if (x < 0.55) return Math.sin((x - 0.32) / 0.23 * Math.PI) * 0.14;
      return 0;
    };
    const draw = () => {
      t += 0.0045;
      ctx.clearRect(0, 0, W, H);
      const mid = H * 0.62, amp = H * 0.30;
      const grad = ctx.createLinearGradient(0, 0, W, 0);
      grad.addColorStop(0, 'rgba(255,74,28,0)');
      grad.addColorStop(0.15, '#12756b');
      grad.addColorStop(0.85, '#ff4a1c');
      grad.addColorStop(1, 'rgba(255,74,28,0)');
      ctx.lineWidth = 2; ctx.strokeStyle = grad; ctx.beginPath();
      const pts = Math.floor(W);
      for (let i = 0; i <= pts; i++) {
        const fx = i / W;
        const b = ((fx * 2) + t) % 1;
        const rise = (fx - 0.5) * amp * 0.7;
        const y = mid - beat(b) * amp - rise;
        i === 0 ? ctx.moveTo(i, y) : ctx.lineTo(i, y);
      }
      ctx.stroke();
      const lead = ((0.999 * 2) + t) % 1;
      const ly = mid - beat(lead) * amp - (0.5 * amp * 0.7);
      ctx.fillStyle = '#ff4a1c'; ctx.beginPath(); ctx.arc(W - 2, ly, 3.5, 0, 7); ctx.fill();
      requestAnimationFrame(draw);
    };
    draw();
  }

  /* ── 마그네틱 버튼 (데스크톱) ─────────────────── */
  function initMagnetic() {
    if (!FINE || REDUCE) return;
    document.querySelectorAll('.btn-primary, .btn-lg').forEach(btn => {
      btn.addEventListener('pointermove', e => {
        const r = btn.getBoundingClientRect();
        const mx = e.clientX - (r.left + r.width / 2);
        const my = e.clientY - (r.top + r.height / 2);
        btn.style.transform = 'translate(' + mx * 0.2 + 'px,' + (my * 0.2) + 'px)';
      });
      btn.addEventListener('pointerleave', () => { btn.style.transform = ''; });
    });
  }
})();
