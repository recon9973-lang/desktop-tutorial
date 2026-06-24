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
  });

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
      if (y > 80) {
        header.style.boxShadow = 'rgba(0,55,112,0.12) 0 4px 20px';
      } else {
        header.style.boxShadow = 'rgba(0,55,112,0.08) 0 1px 3px';
      }
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
})();
