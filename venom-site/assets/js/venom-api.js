/* =========================================================
   VENOM 병원마케팅 — backend integration (design-agnostic)
   기존 베놈 백엔드(Vercel)에 붙는 재사용 모듈.
   어떤 오리지널 디자인의 HTML에도 그대로 연결됩니다.
   ========================================================= */
(function (w) {
  'use strict';

  // 배포된 베놈 백엔드 (같은 Vercel 프로젝트면 상대경로 '' 로 두면 됨)
  var API_BASE = w.VENOM_API_BASE || 'https://desktop-tutorial-chi-peach.vercel.app';
  var KAKAO = 'https://pf.kakao.com/_jxjxdcxj/chat';

  /* -------------------------------------------------------
     1) 상담 폼 → POST /api/contact
        폼에는 name 속성이 있는 input이 있어야 함.
        필수: hospital (병원명). 권장: name, phone, department, message
     ------------------------------------------------------- */
  function initContactForm(form, opts) {
    if (!form) return;
    opts = opts || {};
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = {};
      Array.prototype.forEach.call(form.querySelectorAll('[name]'), function (el) {
        if (el.name) data[el.name] = (el.value || '').trim();
      });
      if (!data.hospital && !data.name) {
        return say(form, 'err', '병원명 또는 성함을 입력해 주세요.');
      }
      // 백엔드 필수값 보정: hospital 없으면 name으로 대체
      if (!data.hospital) data.hospital = data.name;

      var btn = form.querySelector('[type="submit"]');
      var btnText = btn ? btn.textContent : '';
      if (btn) { btn.disabled = true; btn.dataset.label = btnText; btn.textContent = '전송 중…'; }

      fetch(API_BASE + '/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (r && r.result === 'ok') {
            form.reset();
            say(form, 'ok', '상담 신청이 완료됐습니다. 담당자가 24시간 내 연락드립니다.');
            if (opts.onSuccess) opts.onSuccess(data);
          } else { throw new Error('server'); }
        })
        .catch(function () {
          say(form, 'err', '전송 오류가 발생했습니다. <a href="' + KAKAO + '" target="_blank" rel="noopener">카카오톡</a>으로 문의해 주세요.');
        })
        .finally(function () {
          if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label || '상담 신청'; }
        });
    });
  }

  function say(form, kind, html) {
    var box = form.querySelector('[data-form-status]');
    if (!box) { box = document.createElement('div'); box.setAttribute('data-form-status', ''); form.appendChild(box); }
    box.className = 'form-status ' + kind;
    box.style.display = 'block';
    box.innerHTML = html;
  }

  /* -------------------------------------------------------
     2) 블로그 목록/상세 ← /content/blog-posts.json
        posts: [{ id, slug, title, date, category, excerpt, html|content, image }]
        발행(status==='published')만 노출. 필드는 방어적으로 처리.
     ------------------------------------------------------- */
  function loadPosts() {
    return fetch(API_BASE + '/content/blog-posts.json?_=' + Date.now())
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (d) {
        var arr = Array.isArray(d) ? d : (d && d.posts) || [];
        return arr.filter(function (p) { return !p.status || p.status === 'published'; });
      })
      .catch(function () { return []; });
  }

  function renderBlogList(container, opts) {
    if (!container) return;
    opts = opts || {};
    loadPosts().then(function (posts) {
      if (!posts.length) {
        container.innerHTML = '<p class="blog-empty">준비 중입니다. 곧 인사이트가 올라옵니다.</p>';
        return;
      }
      var limit = opts.limit || posts.length;
      container.innerHTML = posts.slice(0, limit).map(function (p) {
        var href = (opts.detailBase || 'blog.html?slug=') + encodeURIComponent(p.slug || p.id);
        return '' +
          '<a class="post-card" href="' + href + '">' +
          (p.image ? '<span class="post-thumb"><img src="' + esc(p.image) + '" alt="" loading="lazy"></span>' : '') +
          '<span class="post-meta">' + esc(p.category || '인사이트') + (p.date ? ' · ' + esc(fmtDate(p.date)) : '') + '</span>' +
          '<span class="post-title">' + esc(p.title || '') + '</span>' +
          (p.excerpt ? '<span class="post-excerpt">' + esc(p.excerpt) + '</span>' : '') +
          '</a>';
      }).join('');
    });
  }

  function renderBlogDetail(container, slug) {
    if (!container) return;
    loadPosts().then(function (posts) {
      var p = posts.filter(function (x) { return (x.slug || x.id) === slug; })[0];
      if (!p) { container.innerHTML = '<p class="blog-empty">글을 찾을 수 없습니다.</p>'; return; }
      container.innerHTML = '' +
        '<div class="post-head"><span class="post-meta">' + esc(p.category || '인사이트') +
        (p.date ? ' · ' + esc(fmtDate(p.date)) : '') + '</span>' +
        '<h1 class="post-h1">' + esc(p.title || '') + '</h1></div>' +
        (p.image ? '<img class="post-hero" src="' + esc(p.image) + '" alt="">' : '') +
        '<div class="post-body">' + (p.html || p.content || esc(p.excerpt || '')) + '</div>';
      document.title = (p.title || '블로그') + ' — 병원마케팅 베놈';
    });
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtDate(d) { try { var t = new Date(d); return t.getFullYear() + '.' + (t.getMonth() + 1) + '.' + t.getDate(); } catch (e) { return d; } }
  function getParam(k) { return new URLSearchParams(location.search).get(k); }

  w.VENOM = {
    initContactForm: initContactForm,
    renderBlogList: renderBlogList,
    renderBlogDetail: renderBlogDetail,
    loadPosts: loadPosts,
    getParam: getParam
  };
})(window);
