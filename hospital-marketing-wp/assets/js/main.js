/* ===== MediMarketing Main JS ===== */
(function () {
  'use strict';

  /* ---- Lucide icons init ---- */
  if (window.lucide) lucide.createIcons();

  /* ---- Header scroll effect ---- */
  const header = document.getElementById('site-header');
  if (header) {
    const onScroll = () => {
      header.classList.toggle('scrolled', window.scrollY > 60);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---- Mobile nav toggle ---- */
  const mobileToggle = document.getElementById('mobile-toggle');
  const mobileNav    = document.getElementById('mobile-nav');
  if (mobileToggle && mobileNav) {
    mobileToggle.addEventListener('click', () => {
      const open = mobileNav.classList.toggle('open');
      mobileToggle.setAttribute('aria-expanded', open);
      mobileNav.setAttribute('aria-hidden', !open);
      mobileToggle.classList.toggle('active', open);
      document.body.style.overflow = open ? 'hidden' : '';
    });

    /* Mobile sub-accordion */
    mobileNav.querySelectorAll('.mobile-sub-toggle').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        const item = btn.closest('.mobile-nav-item');
        item.classList.toggle('open');
      });
    });
  }

  /* ---- FAQ accordion ---- */
  document.querySelectorAll('.faq-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const item   = trigger.closest('.faq-item');
      const body   = item.querySelector('.faq-body');
      const isOpen = item.classList.contains('open');

      /* close all siblings */
      const list = item.closest('.faq-list');
      if (list) {
        list.querySelectorAll('.faq-item.open').forEach(el => {
          el.classList.remove('open');
          const b = el.querySelector('.faq-body');
          if (b) b.style.maxHeight = '0';
        });
      }

      if (!isOpen) {
        item.classList.add('open');
        if (body) body.style.maxHeight = body.scrollHeight + 'px';
      }
    });
  });

  /* ---- TOC auto-generate from h2/h3 ---- */
  const tocList    = document.getElementById('toc-list');
  const contentMain = document.getElementById('content-main');
  if (tocList && contentMain) {
    const headings = contentMain.querySelectorAll('h2, h3');
    headings.forEach((h, i) => {
      if (!h.id) h.id = 'section-' + i;
      const li = document.createElement('li');
      li.className = h.tagName === 'H3' ? 'toc-sub' : '';
      li.innerHTML = `<a href="#${h.id}" class="toc-link">${h.textContent}</a>`;
      tocList.appendChild(li);
    });

    /* TOC active on scroll */
    const tocLinks = tocList.querySelectorAll('.toc-link');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          tocLinks.forEach(a => a.classList.remove('active'));
          const active = tocList.querySelector(`a[href="#${entry.target.id}"]`);
          if (active) active.classList.add('active');
        }
      });
    }, { rootMargin: '-20% 0% -70% 0%' });

    headings.forEach(h => observer.observe(h));
  }

  /* ---- Quick nav smooth scroll ---- */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.getElementById(a.getAttribute('href').slice(1));
      if (!target) return;
      e.preventDefault();
      const offset = 80;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });

  /* ---- Scroll-reveal animation ---- */
  const revealEls = document.querySelectorAll('.fade-up');
  if (revealEls.length) {
    const revealObs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          revealObs.unobserve(e.target);
        }
      });
    }, { threshold: 0.1 });
    revealEls.forEach(el => revealObs.observe(el));
  }

  /* ---- Contact form AJAX ---- */
  const contactForm = document.getElementById('contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = contactForm.querySelector('[type=submit]');
      const msg = document.getElementById('form-message');
      btn.disabled = true;
      btn.textContent = '전송 중...';

      try {
        const res = await fetch(window.mmAjax?.url || '/wp-admin/admin-ajax.php', {
          method: 'POST',
          body: new FormData(contactForm),
        });
        const data = await res.json();
        if (data.success) {
          msg.textContent = '✅ 상담 신청이 완료되었습니다. 1~2 영업일 내 연락드리겠습니다.';
          msg.style.color = 'var(--primary)';
          contactForm.reset();
        } else {
          throw new Error(data.data || '오류가 발생했습니다.');
        }
      } catch (err) {
        msg.textContent = '❌ ' + err.message;
        msg.style.color = '#ef4444';
      } finally {
        btn.disabled = false;
        btn.textContent = '상담 신청하기';
      }
    });
  }

  /* ---- Stats counter animation ---- */
  const counters = document.querySelectorAll('.stat-num[data-target]');
  if (counters.length) {
    const countObs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el     = entry.target;
        const target = parseInt(el.dataset.target, 10);
        const suffix = el.dataset.suffix || '';
        let start = 0;
        const step = Math.ceil(target / 60);
        const tick = () => {
          start = Math.min(start + step, target);
          el.textContent = start.toLocaleString() + suffix;
          if (start < target) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        countObs.unobserve(el);
      });
    }, { threshold: 0.5 });
    counters.forEach(c => countObs.observe(c));
  }

})();
