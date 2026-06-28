'use strict';

const https = require('https');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';

// 실제 바이트(매직 넘버)로 이미지 포맷을 감지해 올바른 확장자/Content를 정한다.
// 외부 의존성(sharp·WASM) 없이 OpenAI가 준 바이트를 그대로 저장 → 빌드/런타임 안전.
function detectExt(buf) {
  if (buf.length >= 12 && buf.subarray(0, 4).toString('ascii') === 'RIFF'
      && buf.subarray(8, 12).toString('ascii') === 'WEBP') return 'webp';
  if (buf.length >= 3 && buf[0] === 0xFF && buf[1] === 0xD8 && buf[2] === 0xFF) return 'jpg';
  if (buf.length >= 8 && buf[0] === 0x89 && buf[1] === 0x50 && buf[2] === 0x4E && buf[3] === 0x47) return 'png';
  return 'png'; // 알 수 없으면 png로 저장(안전)
}

// 항상 { url, githubPath, error } 형태로 반환 — 실패 시 error에 사유를 담아
// 호출부(API 응답)에서 화면에 표시할 수 있게 한다(조용한 실패 방지).
async function generateAndSaveImage(prompt, postId, index = 0, title = '') {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return { url: null, githubPath: null, error: 'OPENAI_API_KEY 미설정(Vercel 환경변수)' };

  const fullPrompt = `Professional Korean hospital marketing photography. ${prompt}. Clean, modern, trustworthy aesthetic. No text overlay. High quality realistic photo style. Bright, professional lighting.`;

  // 이미지 생성 → base64 → GitHub 저장 (sharp 의존 제거 — Lambda 네이티브 바이너리 호환 문제 방지)
  // 모델 폴백 체인: 설정 모델 → gpt-image-1 → dall-e-3 → dall-e-2 순으로 시도.
  // gpt-image-1은 OpenAI 조직 인증(verification) 필요 → 미인증 계정은 403.
  // dall-e-2는 인증 없이 거의 모든 계정에서 동작 → 최종 폴백.
  const configured = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1';
  const chain = [configured, 'gpt-image-1', 'dall-e-3', 'dall-e-2']
    .filter((m, i, arr) => arr.indexOf(m) === i); // 중복 제거(순서 유지)

  let dalle = { b64: null, error: '' };
  const tried = [];
  for (const model of chain) {
    dalle = await callDallE(apiKey, fullPrompt, model);
    if (dalle.b64) break;
    tried.push(`${model}: ${dalle.error || '실패'}`);
  }
  if (!dalle.b64) {
    return { url: null, githubPath: null, error: '이미지 생성 실패(모든 모델) — ' + tried.join(' | ') };
  }

  // OpenAI가 준 바이트를 그대로 저장(변환 없음 — 외부 의존성 0).
  // gpt-image-1엔 JPEG 출력을 요청해 PNG 대비 ~75% 작게 받고, 실제 바이트로 확장자 결정.
  const imgBuffer = Buffer.from(dalle.b64, 'base64');
  const ext = detectExt(imgBuffer);

  // 파일명은 반드시 ASCII만 사용. 한글이 들어가면 GitHub API 요청 경로에서
  // "Request path contains unescaped characters" 오류로 저장이 실패함.
  // 제목의 영문/숫자만 추출해 슬러그로 쓰고, 항상 고유한 postId를 앞에 붙여 충돌 방지.
  const asciiSlug = String(title || '').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
  const base = asciiSlug ? `${postId}-${asciiSlug}` : String(postId);
  const filename = index === 0 ? `${base}.${ext}` : `${base}-${index}.${ext}`;
  const githubPath = `venom-wordpress/preview/content/images/${filename}`;
  const saved = await saveToGitHub(imgBuffer, githubPath);
  if (!saved.ok) return { url: null, githubPath: null, error: 'GitHub 저장 실패: ' + (saved.error || '') };

  // GitHub raw URL로 직접 서빙 → Vercel 재배포 없이 즉시 표시 (배포 한도와 무관)
  const rawUrl = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/venom-wordpress/preview/content/images/${encodeURIComponent(filename)}`;
  return { url: rawUrl, githubPath, error: null };
}

function callDallE(apiKey, prompt, modelOverride) {
  // 기본 모델을 gpt-image-1로 (dall-e-3는 2026년 폐기됨). 환경변수/인자로 override 가능.
  const model = modelOverride || process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1';
  const reqBody = {
    model,
    prompt,
    n: 1,
    size: '1024x1024', // 세 모델(gpt-image-1/dall-e-3/dall-e-2) 모두 공통 지원
  };
  if (model === 'dall-e-3') {
    // dall-e-3: response_format + quality(standard|hd) 지원
    reqBody.response_format = 'b64_json';
    reqBody.quality = 'standard';
  } else if (model === 'dall-e-2') {
    // dall-e-2: response_format만 지원, quality 파라미터 없음(보내면 400 오류)
    reqBody.response_format = 'b64_json';
  } else {
    // gpt-image 계열: 항상 b64 반환(response_format 미지원), quality는 low|medium|high|auto
    reqBody.quality = process.env.OPENAI_IMAGE_QUALITY || 'medium';
    // JPEG 출력 요청 → PNG 대비 ~75% 작게(웹/SEO 유리). webp는 버그로 PNG 둔갑하므로 jpeg 사용.
    reqBody.output_format = 'jpeg';
    reqBody.output_compression = Number(process.env.OPENAI_IMAGE_COMPRESSION) || 80;
  }
  const body = JSON.stringify(reqBody);

  // { b64, error } 반환
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.openai.com',
      path: '/v1/images/generations',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const data = Buffer.concat(chunks).toString('utf8');
        try {
          const json = JSON.parse(data);
          if (json.error) return resolve({ b64: null, error: `${res.statusCode} ${json.error.message || json.error.code || ''}`.trim() });
          const b64 = json.data?.[0]?.b64_json;
          resolve(b64 ? { b64, error: null } : { b64: null, error: `HTTP ${res.statusCode} 응답에 이미지 데이터 없음` });
        } catch (e) {
          resolve({ b64: null, error: `응답 파싱 실패(HTTP ${res.statusCode})` });
        }
      });
    });
    req.on('error', (e) => resolve({ b64: null, error: '네트워크 오류: ' + e.message }));
    req.setTimeout(55000, () => { req.destroy(); resolve({ b64: null, error: 'DALL-E 타임아웃(55초)' }); });
    req.write(body);
    req.end();
  });
}

// 경로 각 세그먼트를 URL 인코딩(한글·공백 등으로 인한 "unescaped characters" 오류 방지).
// 슬래시는 보존하고 파일/폴더명만 인코딩한다.
function encodePath(filePath) {
  return filePath.split('/').map(encodeURIComponent).join('/');
}

// GitHub Contents API GET — 기존 파일 sha 조회(없으면 null). 덮어쓰기에 필요.
function getExistingSha(filePath) {
  const TOKEN = process.env.GITHUB_TOKEN;
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${encodePath(filePath)}?ref=${BRANCH}`,
      method: 'GET',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')).sha || null); }
        catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(15000, () => { req.destroy(); resolve(null); });
    req.end();
  });
}

// { ok, error } 반환. 같은 경로 파일이 있으면 sha로 덮어쓰기.
async function saveToGitHub(buffer, filePath) {
  const TOKEN = process.env.GITHUB_TOKEN;
  if (!TOKEN) return { ok: false, error: 'GITHUB_TOKEN 미설정(Vercel 환경변수)' };

  const sha = await getExistingSha(filePath);
  const payload = {
    message: `auto: 포스트 이미지 ${filePath.split('/').pop()}`,
    content: buffer.toString('base64'),
    branch: BRANCH,
  };
  if (sha) payload.sha = sha; // 기존 파일 덮어쓰기
  const body = JSON.stringify(payload);

  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${encodePath(filePath)}`,
      method: 'PUT',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        if (res.statusCode === 200 || res.statusCode === 201) return resolve({ ok: true, error: null });
        let msg = `HTTP ${res.statusCode}`;
        try { const j = JSON.parse(Buffer.concat(chunks).toString('utf8')); if (j.message) msg += ` ${j.message}`; } catch {}
        resolve({ ok: false, error: msg });
      });
    });
    req.on('error', (e) => resolve({ ok: false, error: '네트워크 오류: ' + e.message }));
    req.setTimeout(30000, () => { req.destroy(); resolve({ ok: false, error: 'GitHub 저장 타임아웃(30초)' }); });
    req.write(body);
    req.end();
  });
}

module.exports = { generateAndSaveImage };
