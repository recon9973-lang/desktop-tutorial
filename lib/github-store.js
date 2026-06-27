'use strict';

const https = require('https');

const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
const REPO  = process.env.GITHUB_REPO  || 'desktop-tutorial';
const BRANCH= process.env.GITHUB_BRANCH|| 'main';
const TOKEN = process.env.GITHUB_TOKEN;
const POSTS_PATH = 'venom-wordpress/preview/content/blog-posts.json';
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
        let data = '';
        res.on('data', c => (data += c));
        res.on('end', () => {
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
  const r = await ghRequest(sha ? 'PUT' : 'PUT', filePath, body);
  if (r.status !== 200 && r.status !== 201) {
    throw new Error(`GitHub PUT 실패 (${r.status}): ` + JSON.stringify(r.body).slice(0, 200));
  }
  return r.body;
}

/** 블로그 포스트 목록 읽기 */
async function getPosts() {
  const f = await getFile(POSTS_PATH);
  return f ? { sha: f.sha, posts: f.content } : { sha: null, posts: [] };
}

/** 블로그 포스트 추가/업데이트 후 저장 */
async function savePost(post) {
  const { sha, posts } = await getPosts();
  const idx = posts.findIndex(p => p.id === post.id);
  if (idx >= 0) posts[idx] = post;
  else posts.unshift(post);
  await putFile(POSTS_PATH, posts, sha, `auto: ${post.status === 'published' ? '발행' : '저장'} "${post.title}"`);
  return post;
}

/** 발행 로그 추가 */
async function appendLog(entry) {
  const f = await getFile(LOG_PATH);
  const logs = f ? f.content : [];
  logs.unshift({ ...entry, ts: new Date().toISOString() });
  if (logs.length > 200) logs.length = 200;
  await putFile(LOG_PATH, logs, f ? f.sha : null, 'auto: 포스팅 로그 업데이트');
}

module.exports = { getPosts, savePost, appendLog };
