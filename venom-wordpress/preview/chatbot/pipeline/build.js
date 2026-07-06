'use strict';

/**
 * 의료광고심의 도우미 챗봇 — 데이터 파이프라인 (RAG 지식베이스 빌드)
 *
 * 입력(승인된 원천 자료):
 *   - data/sources/medical-ad-casebook.md           (복지부 사례집 2판, 2024.12)
 *   - ../../lib/medical-ad-validator.js              (금지표현 검증기)
 *
 * 출력(data/kb/):
 *   - knowledge-base.json   조항·사례를 청킹한 RAG 검색 단위 + 메타데이터(출처·근거조항·태그)
 *   - qa-seed.json          사례집 핵심 Q&A → 질의응답 시드(오더 2번 "질문 수집"의 출발점)
 *   - forbidden-rules.json  금지어/위험어 + 안전 대체표현(검증기 + 사례집 매핑표 통합) → 문구 자가진단 룰엔진
 *   - retrieval-index.json  키워드 역색인(임베딩 없이도 동작하는 하이브리드 검색의 키워드 축)
 *   - manifest.json         빌드 산출물 요약(카운트·시각)
 *
 * 실행:  node pipeline/build.js
 * 특징: 외부 API·네트워크 불필요(결정론적). 임베딩 생성은 별도 단계(embed.js, 추후)에서 부착.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');            // .../chatbot
const SRC_DIR = path.join(ROOT, 'data', 'sources');
const KB_DIR = path.join(ROOT, 'data', 'kb');
const CASEBOOK = path.join(SRC_DIR, 'medical-ad-casebook.md');
const VALIDATOR = path.join(ROOT, '..', 'lib', 'medical-ad-validator.js');

// 빌드 시각(파이프라인 결정론 유지를 위해 인자/환경으로 주입 가능, 없으면 현재시각)
const BUILT_AT = process.env.BUILD_TS || new Date().toISOString();

// ── 유틸 ──────────────────────────────────────────────────────────
function slugify(s, i) {
  const base = s.replace(/[^0-9A-Za-z가-힣]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
  return (base || 'chunk') + '-' + String(i).padStart(3, '0');
}

// 근거 조항 추출: "제56조", "제56조 제2항 제1호", "제3조의5", "시행령 제24조" 등
function extractLegalRefs(text) {
  const refs = new Set();
  const re = /(시행령\s*|시행규칙\s*)?제\s*\d+조(의\s*\d+)?(\s*제\s*\d+항)?(\s*제\s*\d+호)?/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    refs.add(m[0].replace(/\s+/g, ' ').trim());
  }
  // 법률명 힌트
  const laws = [];
  if (/표시\W*광고/.test(text)) laws.push('표시광고법');
  if (/의료법/.test(text)) laws.push('의료법');
  return { refs: [...refs], laws: [...new Set(laws)] };
}

// 태그 부여(검색 필터·라우팅용)
function tagChunk(title, text) {
  const t = title + '\n' + text;
  const tags = new Set();
  if (/금지되는 의료광고|제\d+호/.test(t)) tags.add('금지유형');
  if (/사전심의|제57조|심의필|심의대상|자율심의/.test(t)) tags.add('사전심의');
  if (/표시\W*광고/.test(t)) tags.add('표시광고법');
  if (/체크리스트|점검/.test(t)) tags.add('체크리스트');
  if (/Q&A|Q\s*&\s*A|핵심 Q/.test(t)) tags.add('QA');
  if (/대체 표현|안전 대체|금지\/위험 표현/.test(t)) tags.add('대체표현');
  if (/성형|미용|피부|치과|한의|정형|안과|전문병원|필러|임플란트/.test(t)) tags.add('진료과목');
  if (/외국인환자/.test(t)) tags.add('외국인환자');
  if (/정의|주체|전제/.test(t)) tags.add('총칙');
  if (tags.size === 0) tags.add('일반');
  return [...tags];
}

// 한국어/영숫자 토큰(2자 이상) + 조항 토큰
function tokenize(text) {
  const tokens = new Set();
  const re = /[가-힣]{2,}|[A-Za-z]{2,}|\d+호|\d+조|\d+항/g;
  let m;
  while ((m = re.exec(text)) !== null) tokens.add(m[0].toLowerCase());
  return [...tokens];
}

// ── 1) 사례집 → 청크 ──────────────────────────────────────────────
function buildChunks(md) {
  const lines = md.split(/\r?\n/);
  const chunks = [];
  let h2 = '', h3 = '', buf = [], curTitle = '';
  let idx = 0;

  function flush() {
    const body = buf.join('\n').trim();
    if (!body && !curTitle) { buf = []; return; }
    // 섹션 안에 "**제N호 ...**" 금지유형이 여러 개면 호(號) 단위로 분리
    const hoSplit = splitByHo(body);
    const parts = hoSplit.length ? hoSplit : [{ label: '', text: body }];
    for (const p of parts) {
      const title = [h2, h3, p.label].filter(Boolean).join(' › ');
      const text = (p.label ? `**${p.label}**\n` : '') + p.text;
      if (!text.trim()) continue;
      const legal = extractLegalRefs(title + '\n' + text);
      chunks.push({
        id: slugify(p.label || h3 || h2, idx++),
        title,
        h2, h3,
        source: 'mohw-casebook-2024-12',
        sourceTitle: '복지부 의료광고 사례·체크리스트 2판(2024.12)',
        legalRefs: legal.refs,
        laws: legal.laws,
        tags: tagChunk([h3, p.label].filter(Boolean).join(' '), text), // H2 문서제목 제외(오탐 방지)
        text: text.trim(),
        chars: text.trim().length,
      });
    }
    buf = [];
  }

  for (const line of lines) {
    const m2 = line.match(/^##\s+(.*)$/);
    const m3 = line.match(/^###\s+(.*)$/);
    if (m2) { flush(); h2 = m2[1].trim(); h3 = ''; curTitle = h2; continue; }
    if (m3) { flush(); h3 = m3[1].trim(); curTitle = h3; continue; }
    buf.push(line);
  }
  flush();
  return chunks;
}

// "**제N호 ...**" 볼드 마커로 본문을 호 단위 분리
function splitByHo(body) {
  const marker = /\*\*(제\d+호[^*]*)\*\*/g;
  const idxs = [];
  let m;
  while ((m = marker.exec(body)) !== null) idxs.push({ label: m[1].trim(), at: m.index, end: marker.lastIndex });
  if (idxs.length < 2) return [];
  const parts = [];
  // 첫 마커 이전 서두는 별도 인트로 청크로 보존
  const intro = body.slice(0, idxs[0].at).trim();
  if (intro) parts.push({ label: '', text: intro });
  for (let i = 0; i < idxs.length; i++) {
    const start = idxs[i].end;
    const stop = i + 1 < idxs.length ? idxs[i + 1].at : body.length;
    parts.push({ label: idxs[i].label, text: body.slice(start, stop).trim() });
  }
  return parts;
}

// ── 2) 핵심 Q&A 추출 ─────────────────────────────────────────────
function buildQaSeed(md) {
  const qa = [];
  // "### 6. 핵심 Q&A" 섹션만 대상
  const secMatch = md.match(/###\s*6\.[^\n]*Q&A[\s\S]*?(?=\n###\s|\n---\n|$)/);
  const sec = secMatch ? secMatch[0] : '';
  const re = /^\s*(\d+)\.\s+\*\*(.+?)\*\*\s*[—\-–]\s*(.+)$/gm;
  let m;
  while ((m = re.exec(sec)) !== null) {
    const question = m[2].trim();
    const answer = m[3].trim();
    const legal = extractLegalRefs(question + ' ' + answer);
    qa.push({
      id: 'qa-' + String(m[1]).padStart(3, '0'),
      question,
      answer,
      source: 'mohw-casebook-2024-12',
      legalRefs: legal.refs,
      tags: tagChunk(question, answer),
      origin: 'casebook',
    });
  }
  return qa;
}

// ── 3) 금지표현 룰 통합(검증기 + 사례집 §7 매핑표) ───────────────
function buildForbiddenRules(md) {
  let validator = { FORBIDDEN: [], RISKY: [] };
  try { validator = require(VALIDATOR); } catch (e) { /* 파이프라인 단독 실행 대비 */ }

  // 사례집 §7 표: | 금지/위험 표현 | 근거 유형 | 안전 대체 방향 |
  const casebookMap = [];
  const tableSec = md.match(/###\s*7\.[\s\S]*?(?=\n---\n|$)/);
  if (tableSec) {
    const rows = tableSec[0].split('\n').filter(l => /^\|/.test(l));
    for (const row of rows) {
      const cols = row.split('|').map(c => c.trim()).filter((_, i, a) => i > 0 && i < a.length - 1);
      if (cols.length < 3) continue;
      if (/금지\/위험 표현|^-+$|:?-+:?/.test(cols[0])) continue; // 헤더/구분선
      casebookMap.push({ expression: cols[0], basis: cols[1], saferDirection: cols[2] });
    }
  }

  return {
    updated: BUILT_AT,
    note: '문구 자가진단 룰엔진. lib/medical-ad-validator.js(검증기)와 사례집 §7 대체표현을 통합. 실제 판정 시 교육맥락 제외 휴리스틱(전수검사 스킬) 병행 권장.',
    forbidden: validator.FORBIDDEN || [],
    risky: validator.RISKY || [],
    casebookReplacements: casebookMap,
    counts: {
      forbidden: (validator.FORBIDDEN || []).length,
      risky: (validator.RISKY || []).length,
      casebookReplacements: casebookMap.length,
    },
  };
}

// ── 추가 소스 통합(data/sources/extra/*.md) — 협회 자료·심의기준·가이드라인·시행규칙 ──
function sourceMeta(file) {
  if (file.startsWith('assoc-')) return { tag: '협회자료', label: assocLabel(file) };
  if (file.startsWith('guide-exemption')) return { tag: '심의기준', label: '사전심의 예외 — 심의 없이 게재 가능한 정보성 콘텐츠(의료법 제57조 제3항·심의기준 제3조)' };
  if (file.startsWith('guide-56')) return { tag: '조문원문', label: '의료법 제56조 제2항 — 금지 의료광고 유형·정확한 호수 매핑' };
  if (file.startsWith('guide-ad-subject')) return { tag: '심의기준', label: '의료광고의 주체 — 대행사 대행 가능 여부(의료법 제56조 제1항·제27조 제3항)' };
  if (file.startsWith('guide-compare')) return { tag: '심의기준', label: '비교·비방광고 금지 — 정확한 근거 제56조 제2항 제4·5호' };
  if (file.startsWith('guideline-')) return { tag: '심의기준', label: '의료광고 공통 심의기준(2019.11.19, 3개 협회 공통)' };
  if (file.startsWith('enforcement-rule')) return { tag: '조문원문', label: '의료법 시행규칙 — 의료광고 관련(2026.6.12)' };
  return { tag: '일반', label: file };
}
function assocLabel(f) {
  const org = /dental/.test(f) ? '대한치과의사협회' : /kma|의사/.test(f) ? '대한의사협회' : /han|한의/.test(f) ? '대한한의사협회' : '자율심의기구';
  const kind = /faq/.test(f) ? 'FAQ' : /procedure/.test(f) ? '심의절차' : /target/.test(f) ? '심의대상' : /fees/.test(f) ? '심의수수료' : /documents/.test(f) ? '구비서류' : /reconsider/.test(f) ? '재심의청구' : /device/.test(f) ? '의료기기 광고 심의' : '심의안내';
  return `${org} 의료광고심의 — ${kind}`;
}
function buildExtraChunks() {
  const dir = path.join(SRC_DIR, 'extra');
  if (!fs.existsSync(dir)) return [];
  const out = [];
  let gid = 0;
  for (const file of fs.readdirSync(dir).filter(f => /\.(md|txt)$/.test(f)).sort()) {
    const raw = fs.readFileSync(path.join(dir, file), 'utf8');
    const { tag, label } = sourceMeta(file);
    const srcId = file.replace(/\.(md|txt)$/, '');
    const paras = raw.split(/\n{2,}/).map(s => s.replace(/^#+\s*/, '').trim()).filter(Boolean);
    let buf = '';
    const flush = () => {
      const text = buf.trim();
      buf = '';
      if (text.length < 40) return;
      const legal = extractLegalRefs(text);
      out.push({
        id: 'extra-' + slugify(srcId, gid++),
        title: label, h2: label, h3: '',
        source: srcId, sourceTitle: label,
        legalRefs: legal.refs, laws: legal.laws,
        tags: [...new Set([...tagChunk(label, text), tag])],
        text, chars: text.length,
      });
    };
    for (const p of paras) {
      if (buf && (buf.length + p.length) > 1100) flush();
      buf += (buf ? '\n\n' : '') + p;
    }
    flush();
  }
  return out;
}

// ── 4) 키워드 역색인 ─────────────────────────────────────────────
function buildIndex(chunks) {
  const inverted = {};   // token -> [chunkId,...]
  for (const c of chunks) {
    const toks = tokenize(c.title + '\n' + c.text + '\n' + c.legalRefs.join(' '));
    for (const t of toks) {
      (inverted[t] || (inverted[t] = [])).push(c.id);
    }
  }
  return {
    updated: BUILT_AT,
    method: 'keyword-inverted (하이브리드 검색의 키워드 축; 벡터 임베딩은 embed.js에서 부착)',
    tokenCount: Object.keys(inverted).length,
    inverted,
  };
}

// ── 조문 원문 통합(statutes.json, status=ok일 때만) ──────────────
function buildStatuteChunks() {
  const p = path.join(SRC_DIR, 'statutes.json');
  if (!fs.existsSync(p)) return [];
  let doc; try { doc = JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return []; }
  if (doc.status !== 'ok' || !Array.isArray(doc.statutes)) return [];
  return doc.statutes.map((s, i) => {
    const legal = extractLegalRefs(`${s.law} ${s.article} ${s.text}`);
    const tags = tagChunk(s.article + ' ' + s.title, s.text);
    tags.push('조문원문');
    return {
      id: 'statute-' + slugify(s.article, i),
      title: `${s.law} ${s.article}(${s.title})`,
      h2: '의료법 조문 원문', h3: `${s.article} ${s.title}`,
      source: 'law.go.kr', sourceTitle: `국가법령정보센터 ${s.law} ${s.article}`,
      legalRefs: legal.refs.length ? legal.refs : [`${s.article}`],
      laws: ['의료법'],
      tags: [...new Set(tags)],
      text: s.text.trim(),
      chars: s.text.trim().length,
    };
  });
}

// ── 실행 ─────────────────────────────────────────────────────────
function main() {
  if (!fs.existsSync(CASEBOOK)) {
    console.error('원천 자료 없음:', CASEBOOK);
    process.exit(1);
  }
  const md = fs.readFileSync(CASEBOOK, 'utf8');
  fs.mkdirSync(KB_DIR, { recursive: true });

  const chunks = buildChunks(md);
  chunks.push(...buildStatuteChunks());  // 수집된 조문 원문(있으면) 통합
  chunks.push(...buildExtraChunks());    // 협회 자료·심의기준·가이드라인·시행규칙 통합
  const kb = {
    updated: BUILT_AT,
    schema: 'venom-medical-ad-chatbot/kb@1',
    description: '의료광고심의 도우미 챗봇 RAG 지식베이스(청크 단위). 각 청크는 출처·근거조항·태그 메타데이터 포함.',
    sources: ['mohw-casebook-2024-12'],
    chunkCount: chunks.length,
    chunks,
  };
  const qa = buildQaSeed(md);
  const rules = buildForbiddenRules(md);
  const index = buildIndex(chunks);

  const write = (name, obj) => fs.writeFileSync(path.join(KB_DIR, name), JSON.stringify(obj, null, 2) + '\n', 'utf8');
  write('knowledge-base.json', kb);
  write('qa-seed.json', { updated: BUILT_AT, count: qa.length, items: qa });
  write('forbidden-rules.json', rules);
  write('retrieval-index.json', index);

  // 태그 분포 집계(품질 확인용)
  const tagDist = {};
  for (const c of chunks) for (const t of c.tags) tagDist[t] = (tagDist[t] || 0) + 1;
  const legalRefCount = new Set(chunks.flatMap(c => c.legalRefs)).size;

  const manifest = {
    builtAt: BUILT_AT,
    inputs: { casebook: path.relative(ROOT, CASEBOOK) },
    outputs: {
      'knowledge-base.json': { chunks: chunks.length, legalRefsDistinct: legalRefCount, tagDist },
      'qa-seed.json': { items: qa.length },
      'forbidden-rules.json': rules.counts,
      'retrieval-index.json': { tokens: index.tokenCount },
    },
    next: ['embed.js(임베딩 부착)', '조문 전문 수집(law.go.kr)', '협회 심의기준·FAQ 수집', 'Q&A 10,000 증강'],
  };
  write('manifest.json', manifest);

  console.log('✅ 데이터 파이프라인 빌드 완료');
  console.log(JSON.stringify(manifest.outputs, null, 2));

  // 빌드 게이트: 골드 회귀 검사(기대 근거가 검색 상위에 포함되는지) 자동 실행.
  // 실패하면 비정상 종료 → 근거 누락 상태의 KB가 조용히 배포되는 것을 차단.
  try {
    const { execFileSync } = require('child_process');
    console.log('\n── 골드 회귀 검사 ──');
    execFileSync(process.execPath, [path.join(__dirname, 'audit-gold.js')], { stdio: 'inherit' });
  } catch (e) {
    console.error('❌ 골드 회귀 검사 실패 — 위 실패 케이스의 근거·동의어·검색을 보강하세요.');
    process.exit(1);
  }
}

main();
