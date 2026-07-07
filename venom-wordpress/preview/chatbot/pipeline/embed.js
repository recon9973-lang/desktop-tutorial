'use strict';

/**
 * 임베딩 파이프라인 — 지식베이스 청크를 벡터로 임베딩해 data/kb/embeddings.json 생성.
 * 생성되면 retriever가 자동으로 하이브리드 검색(키워드+벡터)으로 전환한다.
 *
 * 실행:  OPENAI_API_KEY=... node pipeline/embed.js
 * 키 없으면: 안내 후 종료(키워드 검색은 계속 동작). 벡터 없이도 서비스 무중단.
 *
 * 모듈로 require하면 embedText(text) 제공 → API가 질의 임베딩에 사용.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const KB_DIR = path.resolve(__dirname, '..', 'data', 'kb');
const MODEL = process.env.OPENAI_EMBED_MODEL || 'text-embedding-3-small';

/**
 * OpenAI 임베딩 1건 요청.
 * @param {string} text
 * @returns {Promise<number[]>}
 */
function embedText(text) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return Promise.reject(new Error('OPENAI_API_KEY 없음'));
  const body = JSON.stringify({ model: MODEL, input: text.slice(0, 8000) });
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'api.openai.com', path: '/v1/embeddings', method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try {
          const json = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          if (json.error) return reject(new Error(json.error.message));
          resolve(json.data[0].embedding);
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.setTimeout(30000, () => { req.destroy(); reject(new Error('임베딩 타임아웃')); });
    req.write(body); req.end();
  });
}

async function main() {
  if (!process.env.OPENAI_API_KEY) {
    console.log('ℹ️  OPENAI_API_KEY 미설정 → 임베딩 생성을 건너뜁니다.');
    console.log('    키워드 검색(동의어 확장 포함)은 정상 동작합니다.');
    console.log('    키 설정 후 다시 실행하면 embeddings.json 생성 → 하이브리드 검색 자동 활성화.');
    return;
  }
  const kb = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'knowledge-base.json'), 'utf8'));
  const vectors = {};
  let dim = 0;
  for (let i = 0; i < kb.chunks.length; i++) {
    const c = kb.chunks[i];
    const v = await embedText(`${c.title}\n${c.text}`);
    vectors[c.id] = v; dim = v.length;
    process.stdout.write(`\r  임베딩 ${i + 1}/${kb.chunks.length}`);
  }
  const out = { method: 'openai', model: MODEL, dim, count: Object.keys(vectors).length, vectors };
  fs.writeFileSync(path.join(KB_DIR, 'embeddings.json'), JSON.stringify(out) + '\n', 'utf8');
  console.log(`\n✅ embeddings.json 생성 (${out.count}개 · dim ${dim}) → 하이브리드 검색 활성화`);
}

if (require.main === module) main().catch(e => { console.error('embed 실패:', e.message); process.exit(1); });

module.exports = { embedText, MODEL };
