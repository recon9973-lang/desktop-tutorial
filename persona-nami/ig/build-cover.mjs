// GROUND 인스타 커버 합성기 — 배나미 누끼(투명 PNG)를 단색 배경 카드뉴스로 합성한다.
// 샌드박스는 외부 CDN 접근이 막혀 합성 불가 → GitHub Actions 러너에서 실행.
// 입력: persona-nami/ig/cover-manifest.json  [{post,id,theme,hookHtml,cutout,pos}]
// 출력: persona-nami/ig/<post>.png (1080x1080)
// env: CHROME_BIN(헤드리스 크롬 경로)
import fs from "node:fs";
import { execFileSync } from "node:child_process";

const MAN = "persona-nami/ig/cover-manifest.json";
const CHROME = process.env.CHROME_BIN || "chromium-browser";
const LIME = "#C7F24E", EM = "#12574F", INK = "#14201d", CREAM = "#F4F1E8";

// 테마별 배경/글자/하이라이트 색.
const THEMES = {
  emerald: { bg: `radial-gradient(130% 120% at 26% 16%,#17685e 0%,${EM} 55%,#0b3a34 100%)`, text: "#ffffff", hl: LIME, hlText: INK, badgeBg: LIME, badgeText: INK, doodle: LIME },
  cream:   { bg: CREAM, text: INK, hl: LIME, hlText: INK, badgeBg: EM, badgeText: "#fff", doodle: EM },
  lime:    { bg: `linear-gradient(135deg,#d6f56a 0%,${LIME} 60%,#a9e02f 100%)`, text: INK, hl: EM, hlText: "#fff", badgeBg: EM, badgeText: "#fff", doodle: EM }
};

const spark = (w, style, col) => `<svg width="${w}" height="${w}" viewBox="0 0 100 100" style="${style}"><path d="M50 2 C56 38 62 44 98 50 C62 56 56 62 50 98 C44 62 38 56 2 50 C38 44 44 38 50 2Z" fill="${col}"/></svg>`;
const squig = (w, style, col) => `<svg width="${w}" height="${Math.round(w*0.5)}" viewBox="0 0 120 60" style="${style}"><path d="M6 40 Q 24 6 42 34 T 78 34 T 114 30" stroke="${col}" fill="none" stroke-width="9" stroke-linecap="round"/></svg>`;

function coverHtml(t, hookHtml, cutoutDataUri) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Noto Sans CJK KR','Noto Sans KR','Apple SD Gothic Neo',sans-serif;}
html,body{width:1080px;height:1080px;overflow:hidden;}
.wrap{position:relative;width:1080px;height:1080px;background:${t.bg};}
.cut{position:absolute;right:-30px;bottom:0;height:96%;filter:drop-shadow(-8px 0 24px rgba(0,0,0,.18));}
.badge{position:absolute;top:46px;left:52px;background:${t.badgeBg};color:${t.badgeText};font-size:28px;font-weight:800;padding:12px 24px;border-radius:40px;letter-spacing:.3px;}
.hook{position:absolute;left:56px;top:200px;right:360px;color:${t.text};font-size:88px;font-weight:900;line-height:1.14;letter-spacing:-3px;}
.hook mark, .hl{background:${t.hl};color:${t.hlText};padding:0 14px;border-radius:8px;box-decoration-break:clone;-webkit-box-decoration-break:clone;}
.swipe{position:absolute;left:56px;bottom:60px;display:flex;align-items:center;gap:12px;color:${t.text};font-size:29px;font-weight:800;}
.swipe .arw{width:58px;height:58px;border-radius:50%;background:${t.hl};color:${t.hlText};display:flex;align-items:center;justify-content:center;font-size:32px;}
.d1{position:absolute;top:150px;left:60px;transform:rotate(-10deg);}
.d2{position:absolute;bottom:230px;left:70px;transform:rotate(8deg);}
</style></head><body><div class="wrap">
<img class="cut" src="${cutoutDataUri}">
<div class="d1">${spark(58,'',t.doodle)}</div><div class="d2">${squig(110,'',t.doodle)}</div>
<div class="badge">GROUND 🌿</div>
<div class="hook">${hookHtml}</div>
<div class="swipe">넘겨보기 <span class="arw">→</span></div>
</div></body></html>`;
}

async function download(url, out) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download ${res.status}: ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(out, buf);
  return buf;
}

const items = JSON.parse(fs.readFileSync(MAN, "utf8"));
let ok = 0;
for (const it of items) {
  const theme = THEMES[it.theme] || THEMES.emerald;
  const cutPath = `/tmp/${it.post}-cut.png`;
  const buf = await download(it.cutout, cutPath);
  const dataUri = `data:image/png;base64,${buf.toString("base64")}`;
  const html = coverHtml(theme, it.hookHtml, dataUri);
  const hp = `/tmp/${it.post}.html`;
  fs.writeFileSync(hp, html);
  execFileSync(CHROME, ["--headless=new", "--no-sandbox", "--hide-scrollbars",
    `--screenshot=persona-nami/ig/${it.post}.png`, "--window-size=1080,1080", hp], { stdio: "pipe" });
  console.log(`✓ ${it.post} (${it.id}) 합성 완료`);
  ok++;
}
console.log(`${ok}/${items.length} covers built`);
