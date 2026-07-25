#!/usr/bin/env node
// VENOM 용어사전 데이터 생성기
// assets/glossary.js 의 TERMS(위치 기반 튜플)를 순수 JSON(명명 필드)으로 추출한다.
// 사용: node scripts/gen-glossary-data.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(root, 'venom-wordpress/preview/assets/glossary.js');
const OUT = path.join(root, 'venom-wordpress/preview/assets/glossary-dist/glossary-data.json');

const src = fs.readFileSync(SRC, 'utf8');

// glossary.js 는 window(또는 this)에 Glossary 를 노출하는 IIFE.
// window 셰임을 주고 IIFE 를 실행해 TERMS/DICTS 를 캡처한다(로드 시 DOM 미접근).
globalThis.window = globalThis;
new Function(src)();
const G = globalThis.Glossary || (globalThis.window && globalThis.window.Glossary);
if (!G || !G.TERMS) { console.error('추출 실패: Glossary.TERMS 미노출'); process.exit(1); }

// CATS 는 로컬 변수 → 균형 중괄호 슬라이스 후 평가
function sliceObj(tok) {
  const i = src.indexOf(tok); const s = src.indexOf('{', i);
  let d = 0, j = s;
  for (; j < src.length; j++) { const c = src[j]; if (c === '{') d++; else if (c === '}') { d--; if (d === 0) break; } }
  return src.slice(s, j + 1);
}
const CATS = eval('(' + sliceObj('var CATS =') + ')');
const DICTS = G.DICTS;

const terms = G.TERMS.map((t) => {
  const x = t[5] || {};
  return {
    ko: t[0], en: t[1], def: t[2], category: t[3], dict: t[4] || 'seo',
    abbr: x.ac || null,
    detail: x.detail || null,
    example: x.ex || null,
    related: x.rel ? String(x.rel).split(';').map((s) => s.trim()).filter(Boolean) : [],
    sources: (x.src || []).map((s) => ({ label: s[0], url: s[1] })),
  };
});

const dicts = {};
Object.keys(DICTS).forEach((k) => { dicts[k] = { label: DICTS[k].label, abbr: DICTS[k].abbr, color: DICTS[k].color }; });
const categories = {};
Object.keys(CATS).forEach((k) => { categories[k] = { label: CATS[k].label, color: CATS[k].color, dict: CATS[k].dict }; });
const byDict = {};
terms.forEach((t) => { byDict[t.dict] = (byDict[t.dict] || 0) + 1; });

const out = {
  name: 'VENOM 용어사전 데이터',
  description: 'SEO·AI·마케팅·개발 용어사전. 타 사이트에서 자유 렌더링 가능한 순수 데이터.',
  version: '1.0.0',
  schema: {
    term: '{ ko, en, def, category, dict, abbr, detail, example, related[], sources[{label,url}] }',
    note: 'dict=seo|ai|marketing|dev, category=아래 categories 키',
  },
  counts: { total: terms.length, byDict },
  dicts,
  categories,
  terms,
};

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out, null, 2));
console.log(`✅ glossary-data.json 생성 — 총 ${terms.length}개 (${JSON.stringify(byDict)}), 카테고리 ${Object.keys(categories).length}`);
