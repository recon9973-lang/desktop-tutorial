// 단일 파일 인터랙티브 데모(demo.html) 생성 — 실제 data/*.json + 엔진을 인라인.
// 사용: node scripts/build-demo.mjs [출력경로]   (기본: ./demo.html)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const r = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'));

const DATA = {
  ingredients: r('ingredients.json').ingredients,
  concerns: r('concerns.json').concerns,
  interactions: r('interactions.json'),
  rules: r('recommendation_rules.json'),
  evidence: r('evidence.json').evidence,
  meds: r('med_dur_map.json').map,
};

const tpl = fs.readFileSync(path.join(__dirname, 'demo-template.html'), 'utf8');
const html = tpl.replace('__DATA__', JSON.stringify(DATA));

const out = process.argv[2] || path.join(ROOT, 'demo.html');
fs.writeFileSync(out, html);
console.log('✓ wrote', out, '(', (html.length / 1024 | 0) + 'KB )');
