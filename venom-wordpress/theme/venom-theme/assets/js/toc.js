/**
 * Venom Theme — toc.js
 * 우측 TOC (목차) 자동 생성 + 스크롤 연동 하이라이트
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    buildTOC();
    initTOCScroll();
  });

  function buildTOC() {
    const content   = document.querySelector('.page-content');
    const tocList   = document.getElementById('tocList');
    if (!content || !tocList) return;

    const headings  = content.querySelectorAll('h2, h3, h4');
    if (!headings.length) return;

    headings.forEach((h, i) => {
      if (!h.id) h.id = 'section-' + i;

      const depth = parseInt(h.tagName.slice(1)) - 1; // h2→1, h3→2, h4→3
      const li    = document.createElement('li');
      li.className = `toc-item depth-${depth}`;
      li.dataset.id = h.id;

      const a    = document.createElement('a');
      a.href     = '#' + h.id;
      a.textContent = h.textContent;
      a.addEventListener('click', e => {
        e.preventDefault();
        document.getElementById(h.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });

      li.appendChild(a);
      tocList.appendChild(li);
    });
  }

  function initTOCScroll() {
    const items = document.querySelectorAll('.toc-item[data-id]');
    if (!items.length) return;

    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          items.forEach(i => i.classList.remove('active'));
          const active = document.querySelector(`.toc-item[data-id="${entry.target.id}"]`);
          if (active) {
            active.classList.add('active');
            // 사이드바 내 스크롤 동기화
            active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          }
        }
      });
    }, { rootMargin: '-10% 0px -70% 0px', threshold: 0 });

    document.querySelectorAll('.page-content h2, .page-content h3, .page-content h4')
      .forEach(h => io.observe(h));
  }
})();
