// GROUND 인스타 커버 합성기 — 배나미 사진(테마 단색 배경 내장)을 full-bleed로 깔고
// 왼쪽 여백에 형광펜 훅·두들·배지·스와이프를 얹는다. 누끼 매팅이 없어 머리카락이 완벽하다.
// 샌드박스는 외부 CDN 접근이 막혀 합성 불가 → GitHub Actions 러너에서 실행.
// 입력: persona-nami/ig/cover-manifest.json  [{post,id,photo,dark,hookHtml}]
// 출력: persona-nami/ig/<post>.png (1080x1080)  env: CHROME_BIN
import fs from "node:fs";
import { execFileSync } from "node:child_process";

const MAN = "persona-nami/ig/cover-manifest.json";
const CHROME = process.env.CHROME_BIN || "chromium-browser";
const LIME = "#C7F24E", EM = "#12574F", INK = "#14201d";

const spark = (w, style, col) => `<svg width="${w}" height="${w}" viewBox="0 0 100 100" style="${style}"><path d="M50 2 C56 38 62 44 98 50 C62 56 56 62 50 98 C44 62 38 56 2 50 C38 44 44 38 50 2Z" fill="${col}"/></svg>`;
const squig = (w, style, col) => `<svg width="${w}" height="${Math.round(w*0.5)}" viewBox="0 0 120 60" style="${style}"><path d="M6 40 Q 24 6 42 34 T 78 34 T 114 30" stroke="${col}" fill="none" stroke-width="9" stroke-linecap="round"/></svg>`;

function coverHtml(it, photoDataUri) {
  const dark = it.dark;
  const text = dark ? "#ffffff" : INK;
  const hl = dark ? LIME : EM;
  const hlText = dark ? INK : "#ffffff";
  const badgeBg = dark ? LIME : EM;
  const badgeText = dark ? INK : "#ffffff";
  const doodle = dark ? LIME : EM;
  // 왼쪽 텍스트 가독성용 은은한 스크림(어두운 사진=검정, 밝은 사진=흰색 방향).
  const scrim = dark
    ? "linear-gradient(90deg, rgba(0,0,0,.28) 0%, rgba(0,0,0,.10) 34%, transparent 55%)"
    : "linear-gradient(90deg, rgba(255,255,255,.30) 0%, rgba(255,255,255,.10) 34%, transparent 55%)";
  return `<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Noto Sans CJK KR','Noto Sans KR','Apple SD Gothic Neo',sans-serif;}
html,body{width:1080px;height:1080px;overflow:hidden;}
.wrap{position:relative;width:1080px;height:1080px;background:#eee;}
.photo{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:75% 20%;}
.scrim{position:absolute;inset:0;background:${scrim};}
.badge{position:absolute;top:46px;left:52px;background:${badgeBg};color:${badgeText};font-size:28px;font-weight:800;padding:12px 24px;border-radius:40px;letter-spacing:.3px;}
.hook{position:absolute;left:56px;top:180px;right:496px;color:${text};font-size:80px;font-weight:900;line-height:1.42;letter-spacing:-2px;text-shadow:${dark ? "0 2px 14px rgba(0,0,0,.35)" : "0 2px 12px rgba(255,255,255,.5)"};}
.hook mark{margin:6px 0;display:inline-block;}
.hook mark,.hl{background:${hl};color:${hlText};padding:0 14px;border-radius:8px;box-decoration-break:clone;-webkit-box-decoration-break:clone;}
.swipe{position:absolute;left:56px;bottom:60px;display:flex;align-items:center;gap:12px;color:${text};font-size:29px;font-weight:800;}
.swipe .arw{width:58px;height:58px;border-radius:50%;background:${hl};color:${hlText};display:flex;align-items:center;justify-content:center;font-size:32px;}
.d1{position:absolute;top:150px;left:60px;transform:rotate(-10deg);}
.d2{position:absolute;bottom:230px;left:66px;transform:rotate(8deg);}
</style></head><body><div class="wrap">
<img class="photo" src="${photoDataUri}">
<div class="scrim"></div>
<div class="d1">${spark(56,'',doodle)}</div><div class="d2">${squig(104,'',doodle)}</div>
<div class="badge">GROUND 🌿</div>
<div class="hook">${it.hookHtml}</div>
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
  const buf = await download(it.photo, `/tmp/${it.post}-src.png`);
  const dataUri = `data:image/png;base64,${buf.toString("base64")}`;
  const hp = `/tmp/${it.post}.html`;
  fs.writeFileSync(hp, coverHtml(it, dataUri));
  execFileSync(CHROME, ["--headless=new", "--no-sandbox", "--hide-scrollbars",
    `--screenshot=persona-nami/ig/${it.post}.png`, "--window-size=1080,1080", hp], { stdio: "pipe" });
  console.log(`✓ ${it.post} (${it.id}) 합성 완료`);
  ok++;
}
console.log(`${ok}/${items.length} covers built`);

// 부가: 원본 그대로 저장할 참고 이미지(합성 없음). persona-nami/ig/raw-fetch.json = [{url, out}].
// 샌드박스는 생성 CDN egress가 막혀 있어, 러너에서 내려받아 저장소에 저장한다(예: nami-body.png 교체).
const RAW = "persona-nami/ig/raw-fetch.json";
if (fs.existsSync(RAW)) {
  const raws = JSON.parse(fs.readFileSync(RAW, "utf8"));
  for (const r of raws) {
    await download(r.url, r.out);
    console.log(`✓ raw 저장: ${r.out}`);
  }
}
