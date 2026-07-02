'use strict';

const { generatePost } = require('../lib/post-generator');
const { generateAndSaveImage } = require('../lib/image-generator');
const { savePost, savePostEn, appendLog, getPosts, getJsonFile, saveJsonFile } = require('../lib/github-store');
const { translatePostToEnglish } = require('../lib/translate');
const { updateSitemap } = require('../lib/sitemap-builder');
const TC = require('../lib/topic-cluster'); // M1: 토픽 클러스터(빈칸 우선 발행)
const linker = require('../lib/internal-linker'); // M2: 관련글 자동주입(opt-in)

const CLUSTERS_PATH = 'venom-wordpress/preview/content/clusters.json';

const DEFAULT_SETTINGS = {
  enabled: false,
  schedules: [],
  categories: ['geo'],
  keywords: ['병원 GEO마케팅'],
  regions: [],
  extra: '',
};

// 오늘 날짜(KST) YYYY-MM-DD
function kstDateStr() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' })).toISOString().slice(0, 10);
}

// 오늘(KST)에 해당하는 스케줄 객체 반환(없으면 null). 레거시 dailyCount도 흡수.
function getTodaySchedule(settings) {
  const todayStr = kstDateStr();
  if (Array.isArray(settings.schedules) && settings.schedules.length) {
    for (const s of settings.schedules) {
      if (s.from && s.to && todayStr >= s.from && todayStr <= s.to) return s;
    }
    return null;
  }
  if (settings.dailyCount) return { dailyCount: parseInt(settings.dailyCount) || 1, timeMode: 'same', time: '09:00' };
  return null;
}

function _pad2(n) { return String(n).padStart(2, '0'); }
function _hmToMin(hm) { const a = String(hm || '09:00').split(':'); return (parseInt(a[0]) || 0) * 60 + (parseInt(a[1]) || 0); }
function _minToHM(min) { min = ((min % 1440) + 1440) % 1440; return _pad2(Math.floor(min / 60)) + ':' + _pad2(min % 60); }

// 결정적 PRNG — 같은 날엔 폴링마다 동일한 랜덤 슬롯이 나오도록(슬롯 도래 판정 일관성).
function _hashStr(s) { let h = 2166136261 >>> 0; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function _mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// 현재 시각(KST) HH:MM
function kstNowHM() {
  const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  return _pad2(d.getHours()) + ':' + _pad2(d.getMinutes());
}

// 발행 개수만큼 시각(HH:MM) 배열 산출 — instant/same/random/individual. 항상 시간 오름차순 정렬(슬롯 도래 판정용).
// seedStr(보통 오늘 KST 날짜)로 random을 결정적으로 만들어 폴링마다 동일한 결과 보장.
function computePublishTimes(sched, count, seedStr) {
  const mode = (sched && sched.timeMode) || 'same';
  const out = [];
  if (mode === 'instant') {
    // 즉시 발행: 슬롯을 자정으로 두어 크론이 도는 즉시 전부 도래 처리
    for (let i = 0; i < count; i++) out.push('00:00');
    return out;
  }
  if (mode === 'random') {
    let a = _hmToMin(sched.randStart || '09:00'), b = _hmToMin(sched.randEnd || '18:00');
    if (b < a) { const t = a; a = b; b = t; }
    const rnd = _mulberry32(_hashStr(String(seedStr || '') + '|' + a + '|' + b + '|' + count));
    for (let i = 0; i < count; i++) out.push(_minToHM(a + Math.floor(rnd() * (b - a + 1))));
  } else if (mode === 'individual') {
    const arr = Array.isArray(sched.times) ? sched.times : [];
    for (let i = 0; i < count; i++) out.push(arr[i] || arr[arr.length - 1] || sched.time || '09:00');
  } else { // same
    const t = (sched && sched.time) || '09:00';
    for (let i = 0; i < count; i++) out.push(t);
  }
  out.sort(); // HH:MM 문자열 정렬 = 시간 오름차순
  return out;
}

// 오늘(KST) 날짜 + HH:MM → UTC ISO 타임스탬프
function kstPublishAtISO(hm) {
  return new Date(`${kstDateStr()}T${hm}:00+09:00`).toISOString();
}

function authCheck(req) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false; // cron secret 없으면 무조건 차단
  return (req.headers['authorization'] || '') === `Bearer ${secret}`;
}

const SETTINGS_PATH = 'venom-wordpress/preview/content/posting-settings.json';

async function loadSettings() {
  // 1순위: GitHub에서 설정 파일 직접 조회 (HTTP 자기호출보다 실패 지점이 적다)
  try {
    const f = await getJsonFile(SETTINGS_PATH, null);
    if (f && f.content && typeof f.content.enabled === 'boolean') {
      return { ...f.content, _source: 'github' };
    }
  } catch {}
  // 2순위: 자체 API 경유 (구 방식 유지)
  try {
    const f = (typeof fetch !== 'undefined') ? fetch : null;
    if (f) {
      const baseUrl = process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000';
      const r = await f(`${baseUrl}/api/posting-settings`, {
        headers: { Authorization: `Bearer ${process.env.ADMIN_SECRET || ''}` },
      });
      if (r.ok) return { ...(await r.json()), _source: 'self-api' };
    }
  } catch {}
  return { ...DEFAULT_SETTINGS, _source: 'fallback-default' };
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    return res.status(405).json({ error: 'POST/GET only' });
  }
  if (!authCheck(req)) return res.status(401).json({ error: '인증 실패' });

  const settings = await loadSettings();
  if (!settings.enabled) {
    // _source가 fallback-default면 "설정을 못 읽어서" 꺼진 것으로 보이는 상태 — 원인 구분용으로 노출
    return res.status(200).json({ ok: true, skipped: true, reason: '자동 포스팅 비활성화 상태', settingsSource: settings._source || 'unknown' });
  }

  const results = [];
  const todaySched = getTodaySchedule(settings);
  if (!todaySched) {
    return res.status(200).json({ ok: true, skipped: true, reason: '오늘은 발행 스케줄이 없습니다.' });
  }
  const todayStr = kstDateStr();
  const count = Math.max(1, parseInt(todaySched.dailyCount) || 1);
  // 오늘의 발행 슬롯 시각(시간 오름차순). random은 날짜 시드로 결정적 → 폴링마다 동일.
  const slots = computePublishTimes(todaySched, count, todayStr);
  const nowHM = kstNowHM();
  const dueCount = slots.filter(t => t <= nowHM).length; // 지금까지 도래한 슬롯 수
  if (dueCount === 0) {
    return res.status(200).json({ ok: true, skipped: true, reason: '아직 도래한 발행 시각이 없습니다.', now: nowHM, slots });
  }

  // M1 클러스터 모드(opt-in): clusters.json의 빈칸을 무작위 키워드보다 우선 채운다.
  const clusterMode = settings.mode === 'cluster' || settings.clusterMode === true;
  let clustersObj = null, clustersDirty = false;
  if (clusterMode) {
    try { clustersObj = (await getJsonFile(CLUSTERS_PATH, { clusters: [] })).content || { clusters: [] }; }
    catch (e) { clustersObj = { clusters: [] }; }
  }

  // 오늘 이미 발행된 '스케줄' 글 수 — 폴링 멱등성(중복/재발행 방지)
  let publishedToday = 0;
  try {
    const { posts } = await getPosts();
    publishedToday = (posts || []).filter(p => p.scheduledDate === todayStr).length;
  } catch (e) {
    return res.status(200).json({ ok: true, skipped: true, reason: 'getPosts 실패 — 중복 방지 위해 이번 실행 건너뜀', error: e.message });
  }

  // 한 번 호출에서 최대 발행 수(함수 타임아웃 방지). 못 채운 슬롯은 다음 폴링이 따라잡음.
  const MAX_PER_RUN = 3;
  const toPublish = Math.min(Math.min(count, dueCount) - publishedToday, MAX_PER_RUN);
  if (toPublish <= 0) {
    return res.status(200).json({ ok: true, skipped: true, reason: '도래한 슬롯 모두 발행 완료', now: nowHM, dueCount, publishedToday });
  }

  for (let k = 0; k < toPublish; k++) {
    const slotIdx = publishedToday + k;       // 다음 미발행 슬롯
    // 즉시 발행 슬롯('00:00')은 표기용 발행 시각을 실제 발행 시점으로 기록
    const slotTime = ((todaySched.timeMode === 'instant') ? nowHM : slots[slotIdx]) || nowHM;
    const cats = settings.categories || ['geo'];
    const keywords = settings.keywords || ['병원마케팅'];
    const regions = settings.regions || [];

    let category = cats[slotIdx % cats.length];
    let keyword = keywords[slotIdx % keywords.length];
    let region = regions.length ? regions[slotIdx % regions.length] : '';

    // 클러스터 빈칸이 있으면 그 하위주제를 우선 발행(없으면 기존 로테이션 유지)
    let clusterPick = null;
    if (clusterMode && clustersObj) {
      let gap = TC.nextGap(clustersObj);
      // 빈칸 소진 시 자동확장(opt-in): 다음 필러로 새 클러스터 설계
      if (!gap && settings.clusterAutoExpand) {
        try {
          const { researchKeywords } = require('../lib/keyword-research');
          const pillars = (settings.clusterPillars && settings.clusterPillars.length) ? settings.clusterPillars : keywords;
          const pillar = pillars[slotIdx % pillars.length];
          const cid = TC.slugId(category, region, pillar);
          const exists = (clustersObj.clusters || []).some((c) => c.id === cid);
          if (!exists) {
            const r = await researchKeywords(pillar, { region });
            const cluster = TC.buildCluster({ category, region, pillar, related: r.related, questions: r.questions, size: 6 });
            clustersObj = TC.upsertCluster(clustersObj, cluster);
            clustersDirty = true;
            gap = TC.nextGap(clustersObj);
          }
        } catch (e) { console.warn('[cron] 클러스터 자동확장 실패(무시):', e.message); }
      }
      if (gap) { category = gap.category; keyword = gap.kw; region = gap.region || region; clusterPick = gap; }
    }

    try {
      const post = await generatePost({ category, keyword, region, extra: settings.extra });

      // 예약 시각이 도래해 '지금 실제 발행'. scheduledDate로 당일 멱등성 보장.
      post.scheduledDate = todayStr;
      post.scheduledTime = slotTime;
      post.publishAt = kstPublishAtISO(slotTime);
      post.date = todayStr;

      // 이미지 1~2장 생성: 1번째=본문 최상단 히어로, 2번째=첫 h2 뒤 본문 삽입
      let imageError = null;
      try {
        const imgUrls = [];
        const safe = (s) => String(s || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
        const LOGO = 'https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/logo_venomad_hospital%20marketing.png';
        const fig = (url, cap, alt) => `<figure style="position:relative;margin:24px 0 32px;border-radius:12px;overflow:hidden">`
          + `<img src="${url}" alt="${safe(alt || post.title)}" style="width:100%;height:auto;display:block" loading="lazy">`
          + `<img src="${LOGO}" alt="병원마케팅 베놈 로고" style="position:absolute;right:14px;bottom:36px;width:104px;height:auto;opacity:.95;filter:drop-shadow(0 2px 8px rgba(0,0,0,.45))">`
          + `<figcaption style="font-size:12px;color:#888;text-align:center;padding:8px">${cap}</figcaption>`
          + `</figure>`;

        // 1·2번째 이미지를 병렬 생성(타임아웃 여유 확보) — 서로 다른 파일명이라 충돌 없음
        const [img1, img2] = await Promise.all([
          generateAndSaveImage(post.imagePrompt, post.id, 0, post.title),
          generateAndSaveImage(post.imagePrompt, post.id, 1, post.title),
        ]);
        if (img1 && img1.url) {
          imgUrls.push(img1.url);
          post.html = fig(img1.url, '© 병원마케팅 베놈', `${post.title} | 병원마케팅 베놈`) + post.html;
        } else if (img1 && img1.error) {
          imageError = img1.error;
        }

        // 2번째 이미지(베스트 에포트) — 실패해도 무시
        if (img2 && img2.url) {
          imgUrls.push(img2.url);
          const second = fig(img2.url, '병원마케팅 베놈 — 데이터 기반 전략', `${post.title} 데이터 분석 | 병원마케팅 베놈`);
          // 첫 번째 </h2> 뒤에 삽입, 없으면 본문 끝에 추가
          const h2End = post.html.indexOf('</h2>');
          post.html = h2End > -1
            ? post.html.slice(0, h2End + 5) + second + post.html.slice(h2End + 5)
            : post.html + second;
        }

        if (imgUrls.length) post.images = imgUrls;
      } catch (imgErr) {
        imageError = imgErr.message;
        console.warn('[cron] 이미지 생성 예외:', imgErr.message);
      }
      if (imageError) console.warn('[cron] 이미지 생성 실패:', imageError);

      const logBase = {
        id: post.id,
        title: post.title,
        tokenUsage: post.tokenUsage || null,
        imageGenerated: !!(post.images && post.images.length),
        imageError: imageError || undefined,
      };

      if (post.publishable) {
        // 의료광고 검증 통과 + 콘텐츠 오류 없음 → 즉시 발행
        // M2(opt-in): 발행 전 관련글 내부링크 블록을 자연스럽게 주입(과최적화 방지 규칙 내장)
        if (settings.autoInternalLinks) {
          try {
            const { posts: existing } = await getPosts();
            const { suggestions } = linker.suggestLinks(existing.concat([post]), { perPost: 3 });
            const mine = suggestions.find((s) => s.id === post.id);
            if (mine && mine.links.length) post.html = linker.injectRelatedBlock(post.html, mine.links);
          } catch (e) { console.warn('[cron] 내부링크 주입 실패(무시):', e.message); }
        }
        post.status = 'published';
        await savePost(post);
        // 방안 A: 발행 글의 영문 번역본도 생성·저장(실패해도 한글 발행엔 영향 없음)
        try {
          const enPost = await translatePostToEnglish(post);
          await savePostEn(enPost);
        } catch (trErr) {
          await appendLog({ action: 'cron-en-fail', id: post.id, error: trErr.message });
        }
        const action = post.autoFixed ? 'cron-publish-fixed' : 'cron-publish';
        await appendLog({ action, ...logBase, autoFixed: post.autoFixed });
        // 클러스터 모드: 발행된 글을 해당 하위주제 빈칸에 채움
        if (clusterPick) {
          clustersObj = TC.fillSubtopic(clustersObj, clusterPick.clusterId, clusterPick.kw, post.id);
          clustersDirty = true;
        }
        results.push({ ok: true, id: post.id, title: post.title, autoFixed: post.autoFixed, cluster: clusterPick ? clusterPick.clusterId : undefined });
      } else {
        // 금지어 잔존 또는 콘텐츠 오류(깨짐·잘림 등) → 검수 대기
        post.status = 'review';
        await savePost(post);
        const reason = !post.validation.pass ? '의료광고 검수 필요' : '콘텐츠 오류 검수 필요';
        await appendLog({
          action: 'cron-review', ...logBase,
          forbidden: post.validation.forbidden,
          contentErrors: (post.contentErrors || []).map(e => e.msg),
        });
        results.push({
          ok: false, id: post.id, title: post.title, reason,
          forbidden: post.validation.forbidden,
          contentErrors: (post.contentErrors || []).map(e => e.msg),
        });
      }
    } catch (e) {
      results.push({ ok: false, error: e.message, category, keyword });
    }
  }

  // 클러스터 변경 저장(빈칸 채움)
  if (clusterMode && clustersDirty) {
    try { await saveJsonFile(CLUSTERS_PATH, clustersObj, 'auto(growthops): 클러스터 빈칸 채움'); }
    catch (e) { console.warn('[cron] 클러스터 저장 실패(무시):', e.message); }
  }

  // 사이트맵 자동 갱신
  try {
    const { posts: allPosts } = await getPosts();
    await updateSitemap(allPosts);
  } catch (e) {
    console.warn('[cron] sitemap 갱신 실패(무시):', e.message);
  }

  return res.status(200).json({ ok: true, published: results.filter(r => r.ok).length, ran: results.length, dueCount, publishedBefore: publishedToday, now: nowHM, results });
};
