// report.html → 인쇄용 PDF. 아티팩트 원본은 건드리지 않고, PDF를 뽑을 때만 인쇄 CSS를 주입한다.
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

// ESM 은 bare specifier 를 「이 파일 기준」으로 찾는다. 이 스크립트는 저장소 안에 있고
// playwright 는 전역/스크래치패드에만 설치돼 있으므로, 설치 경로를 직접 훑는다.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const req = createRequire(join(process.cwd(), 'x.js'));
let chromium;
for (const m of ['playwright-core', 'playwright',
                 '/opt/node22/lib/node_modules/playwright-core',
                 '/opt/node22/lib/node_modules/playwright']) {
  try {
    const mod = await import(pathToFileURL(req.resolve(m)).href);
    // playwright 는 CommonJS 라 named export 가 아니라 default 아래에 붙는다
    chromium = mod.chromium ?? mod.default?.chromium;
    if (chromium) break;
  } catch {}
}
if (!chromium) {
  console.error('playwright를 찾지 못했다. `npm i playwright-core` 후 그 디렉터리에서 실행할 것.');
  process.exit(1);
}

const SRC = resolve(process.argv[2] || 'report.html');
const OUT = resolve(process.argv[3] || '네이버_지역진료과_키워드분석_2026-09.pdf');
const body = readFileSync(SRC, 'utf8');
const tmp = mkdtempSync(join(tmpdir(), 'pdf-'));
const page_html = join(tmp, 'print.html');
writeFileSync(page_html, `<!doctype html><html data-theme="light"><head><meta charset="utf-8">
<style>html{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>${body}</body></html>`);

const PRINT_CSS = `
/* ── 지면 폭에 맞춰 본문을 펼친다 */
.wrap{max-width:none!important;padding:0!important}
.col{max-width:none!important}
body{font-size:12.5px!important;line-height:1.62}
p{margin:10px 0}

/* ── 인쇄에서 overflow:auto 는 내용을 잘라 버린다 */
.scroll,#trend-chart{overflow:visible!important}
#trend-chart svg{min-width:0!important}
#tip{display:none!important}

/* ── 페이지 나눔 */
section{break-before:page;break-inside:auto}
section:first-of-type,#method-warning{break-before:auto}
h1,h2,h3{break-after:avoid}
figure,.panel,.note,.warn,.finds,.sm{break-inside:avoid}
figcaption{break-before:avoid}
table{break-inside:auto;font-size:11.5px}
tr{break-inside:avoid}
thead{display:table-header-group}
thead th{position:static!important}

/* ── 표·히트맵을 지면 폭 안으로 */
.hm .cell{min-width:40px!important;padding:6px 3px;font-size:11px}
.hm th{font-size:9.5px}
.hm tbody th{font-size:12px}
th,td{padding:5px 6px}
.sm-grid{grid-template-columns:repeat(4,1fr)!important;gap:8px}

/* ── 본문 셀의 nowrap 이 표를 지면 밖으로 밀지 않도록 */
tr.sub td{white-space:normal!important;font-size:10px;line-height:1.5}
#tbl-top3{font-size:10.5px}
#tbl-top3 th,#tbl-top3 td{padding:4px 4px}
#tbl-top3 td:nth-child(3),#tbl-all td:first-child,#tbl-demand td:first-child{white-space:normal}

/* ── 상호작용 컨트롤은 현재 선택 상태만 정적으로 보이게 */
.ctrl button{cursor:default;padding:3px 8px;font-size:12px}
.ctrl{gap:10px 18px}
.dv-row{padding:2px 0;font-size:12.5px}
.dv-head{padding:12px 0 5px}

header{padding:0 0 26px}
h1{font-size:38px!important}
.standfirst{font-size:15px}
.meta dd{font-size:12.5px}
footer{break-inside:avoid}
details{break-inside:avoid}
details:not([open]) > summary{list-style:none}
`;

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ viewport: { width: 900, height: 1200 } });
const errs = []; p.on('pageerror', e => errs.push(String(e)));
await p.goto('file://' + page_html, { waitUntil: 'networkidle' });
await p.waitForTimeout(1800);
if (errs.length) { console.error('JS ERRORS:', errs); process.exit(1); }

// 접힌 <details>(방법·한계)는 인쇄본에서 모두 펼친다
await p.evaluate(() => document.querySelectorAll('details').forEach(d => d.open = true));

// 표 머리글의 긴 연월 범위는 인쇄 지면에서 열 너비를 지배한다. 축약형으로 바꿔 폭을 회수한다.
await p.evaluate(() => {
  const short = { '2023.09–2024.08': '’23.9–’24.8', '2024.09–2025.08': '’24.9–’25.8',
                  '2025.09–2026.08': '’25.9–’26.8' };
  for (const th of document.querySelectorAll('th'))
    for (const [long, s] of Object.entries(short))
      if (th.innerHTML.includes(long)) th.innerHTML = th.innerHTML.replace(long, s);
});
await p.emulateMedia({ media: 'print', colorScheme: 'light' });
await p.addStyleTag({ content: PRINT_CSS });
await p.waitForTimeout(700);

const foot = `<div style="width:100%;font-size:8px;font-family:sans-serif;color:#6d7a75;
  padding:0 12mm;display:flex;justify-content:space-between;">
  <span>네이버 데이터랩 검색어트렌드 · 2023.09–2026.08 · 수집 2026-09-09</span>
  <span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;

await p.pdf({
  path: OUT, format: 'A4', printBackground: true,
  margin: { top: '12mm', bottom: '15mm', left: '12mm', right: '12mm' },
  displayHeaderFooter: true, headerTemplate: '<div></div>', footerTemplate: foot,
});
await b.close();
console.log('PDF written:', OUT);
