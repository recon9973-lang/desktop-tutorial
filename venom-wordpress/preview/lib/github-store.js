'use strict';

const https = require('https');

const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
const REPO  = process.env.GITHUB_REPO  || 'desktop-tutorial';
const BRANCH= process.env.GITHUB_BRANCH|| 'main';
const TOKEN = process.env.GITHUB_TOKEN;
const POSTS_PATH = 'venom-wordpress/preview/content/blog-posts.json';
const EN_POSTS_PATH = 'venom-wordpress/preview/content/blog-posts-en.json';
const LOG_PATH   = 'venom-wordpress/preview/content/posting-log.json';

function ghRequest(method, path, body) {
  if (!TOKEN) throw new Error('GITHUB_TOKEN 환경변수가 없습니다.');
  const payload = body ? JSON.stringify(body) : undefined;
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: 'api.github.com',
        path: `/repos/${OWNER}/${REPO}/contents/${path}`,
        method,
        headers: {
          'Authorization': `token ${TOKEN}`,
          'User-Agent': 'venom-autopost/1.0',
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json',
          ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
        },
      },
      (res) => {
        // Buffer로 모아 UTF-8 디코딩 (멀티바이트 한글 깨짐 방지)
        const chunks = [];
        res.on('data', c => chunks.push(c));
        res.on('end', () => {
          const data = Buffer.concat(chunks).toString('utf8');
          try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
          catch(e) { resolve({ status: res.statusCode, body: data }); }
        });
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function getFile(filePath) {
  const r = await ghRequest('GET', filePath);
  if (r.status === 404) return null;
  if (r.status !== 200) throw new Error('GitHub GET 실패: ' + r.status);
  return {
    sha: r.body.sha,
    content: JSON.parse(Buffer.from(r.body.content, 'base64').toString('utf8')),
  };
}

async function putFile(filePath, content, sha, message) {
  const encoded = Buffer.from(JSON.stringify(content, null, 2)).toString('base64');
  const body = { message, content: encoded, branch: BRANCH };
  if (sha) body.sha = sha;
  const r = await ghRequest('PUT', filePath, body);
  if (r.status !== 200 && r.status !== 201) {
    const err = new Error(`GitHub PUT 실패 (${r.status}): ` + JSON.stringify(r.body).slice(0, 200));
    err.status = r.status; // 409=SHA 충돌(동시 쓰기), 422=sha 누락(파일 이미 존재) — 호출부에서 구분
    throw err;
  }
  return r.body;
}

/** 파일 삭제 (락 해제 등). sha 필수. */
async function deleteFile(filePath, sha, message) {
  const r = await ghRequest('DELETE', filePath, { message: message || `chore: delete ${filePath}`, sha, branch: BRANCH });
  if (r.status !== 200) {
    const err = new Error(`GitHub DELETE 실패 (${r.status})`);
    err.status = r.status;
    throw err;
  }
  return true;
}

function _sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

/**
 * 동시 쓰기 충돌(409) 해결기 — read-modify-write 작업 전체를 재시도한다.
 * 재시도마다 파일을 다시 읽으므로 다른 작성자의 변경을 흡수(병합)한 뒤 내 변경을 다시 얹는다.
 * upsert(id 기준) 구조라 재적용해도 중복이 생기지 않는다.
 */
async function withConflictRetry(op, tries) {
  const max = tries || 4;
  for (let i = 0; ; i++) {
    try { return await op(); }
    catch (e) {
      if (e && e.status === 409 && i < max - 1) {
        await _sleep(250 + Math.floor(Math.random() * 400) * (i + 1)); // 지터 백오프
        continue;
      }
      throw e;
    }
  }
}

/** 블로그 포스트 목록 읽기 */
async function getPosts() {
  const f = await getFile(POSTS_PATH);
  return f ? { sha: f.sha, posts: f.content } : { sha: null, posts: [] };
}

/** 블로그 포스트 추가/업데이트 후 저장 — 동시 쓰기 충돌 시 재읽기·병합·재시도 */
async function savePost(post) {
  return withConflictRetry(async () => {
    const { sha, posts } = await getPosts();
    const idx = posts.findIndex(p => p.id === post.id);
    if (idx >= 0) posts[idx] = post;
    else posts.unshift(post);
    await putFile(POSTS_PATH, posts, sha, `auto: ${post.status === 'published' ? '발행' : '저장'} "${post.title}"`);
    return post;
  });
}

/** 영문 블로그 포스트 추가/업데이트 후 저장 (방안 A) — 충돌 재시도 */
async function savePostEn(post) {
  return withConflictRetry(async () => {
    const f = await getFile(EN_POSTS_PATH);
    const posts = f ? f.content : [];
    const sha = f ? f.sha : null;
    const idx = posts.findIndex(p => p.id === post.id);
    if (idx >= 0) posts[idx] = post;
    else posts.unshift(post);
    await putFile(EN_POSTS_PATH, posts, sha, `auto(en): "${post.title}"`);
    return post;
  });
}

/** 블로그 포스트 실제 삭제 — 충돌 재시도 */
async function deletePost(id) {
  return withConflictRetry(async () => {
    const { sha, posts } = await getPosts();
    const filtered = posts.filter(p => p.id !== id);
    if (filtered.length === posts.length) return false; // 없던 글
    await putFile(POSTS_PATH, filtered, sha, `auto: 삭제 "${id}"`);
    return true;
  });
}

/** 발행 로그 추가 — 충돌 재시도 */
async function appendLog(entry) {
  return withConflictRetry(async () => {
    const f = await getFile(LOG_PATH);
    const logs = f ? f.content : [];
    logs.unshift({ ...entry, ts: new Date().toISOString() });
    if (logs.length > 200) logs.length = 200;
    await putFile(LOG_PATH, logs, f ? f.sha : null, 'auto: 포스팅 로그 업데이트');
  });
}

/**
 * 발행 작업 락 — 파일 생성의 원자성(이미 있으면 422)을 잠금으로 사용.
 * 반환: { sha } (획득) | null (다른 작업 진행 중).
 * ttlMs 초과된 낡은 락은 탈취한다(타임아웃으로 죽은 실행의 락 방치 방지).
 */
async function acquireLock(filePath, ttlMs) {
  const payload = { ts: new Date().toISOString(), pid: process.pid };
  try {
    const r = await putFile(filePath, payload, null, 'lock: 발행 작업 잠금');
    return { sha: r.content && r.content.sha };
  } catch (e) {
    if (e.status !== 422 && e.status !== 409) throw e;
    const f = await getFile(filePath).catch(() => null);
    if (!f) return null; // 방금 해제됨 — 경합 회피, 다음 폴링에 양보
    const age = Date.now() - new Date((f.content && f.content.ts) || 0).getTime();
    if (age > (ttlMs || 10 * 60 * 1000)) {
      try {
        const r2 = await putFile(filePath, payload, f.sha, 'lock: 만료된 잠금 탈취');
        return { sha: r2.content && r2.content.sha };
      } catch { return null; } // 탈취 경합 패배
    }
    return null;
  }
}

/** 락 해제 — 실패해도 치명적이지 않음(만료 탈취로 자가 회복). */
async function releaseLock(filePath, sha) {
  try { await deleteFile(filePath, sha, 'lock: 발행 작업 잠금 해제'); return true; }
  catch (e) {
    // sha가 달라졌으면(탈취됨) 내 락이 아니므로 건드리지 않는다
    if (e.status === 409 || e.status === 404) return false;
    throw e;
  }
}

/**
 * 범용 JSON 파일 읽기 (없으면 fallback 반환).
 * GrowthOps(아웃리치 CRM, 클러스터, 스냅샷 등) 신규 데이터 파일 공용.
 * @returns {{ sha: string|null, content: any }}
 */
async function getJsonFile(filePath, fallback) {
  const f = await getFile(filePath);
  return f ? { sha: f.sha, content: f.content } : { sha: null, content: fallback };
}

/** 범용 JSON 파일 저장(생성/갱신). sha 없으면 새로 만든다. — 충돌 재시도 */
async function saveJsonFile(filePath, content, message) {
  return withConflictRetry(async () => {
    const f = await getFile(filePath).catch(() => null);
    return putFile(filePath, content, f ? f.sha : null, message || `chore: update ${filePath}`);
  });
}

module.exports = {
  getPosts, savePost, savePostEn, appendLog, deletePost,
  getFile, putFile, deleteFile, getJsonFile, saveJsonFile,
  withConflictRetry, acquireLock, releaseLock,
};
