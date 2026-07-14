// GROUND(@ground_geo) 인스타그램 — 큐에서 "다음 1개"만 발행하고 큐를 갱신한다.
// GitHub Actions 러너에서 실행(샌드박스는 graph.facebook.com egress 차단).
// 필요 env: TOKEN(=IG 액세스 토큰), GITHUB_SHA(체크아웃 커밋). 선택: IG_ID.
// 이미지 공개 URL은 현재 커밋 SHA로 jsDelivr에서 서빙 → image_url 로 그대로 사용.
import fs from "node:fs";

const QUEUE = "persona-nami/ig/queue.json";
const REPO = "recon9973-lang/desktop-tutorial";
const GV = "v21.0";
const BASE = `https://graph.facebook.com/${GV}`;

const TOKEN = process.env.TOKEN;
const SHA = process.env.GITHUB_SHA;
if (!TOKEN) { console.error("::error::TOKEN(IG_TOKEN) 이 없습니다."); process.exit(1); }
if (!SHA) { console.error("::error::GITHUB_SHA 가 없습니다."); process.exit(1); }

const q = JSON.parse(fs.readFileSync(QUEUE, "utf8"));
const IG = process.env.IG_ID || q.igId;

const next = q.posts.find((p) => !p.published);
if (!next) { console.log("큐에 발행할 게시물이 없습니다. (모두 발행 완료)"); process.exit(0); }

// images 배열(2장 이상)이면 캐러셀(카드뉴스), 아니면 단일 사진.
const rel = (Array.isArray(next.images) && next.images.length >= 2) ? next.images : [next.img];
const urls = rel.map((p) => `https://cdn.jsdelivr.net/gh/${REPO}@${SHA}/${p}`);
const caption = fs.readFileSync(next.cap, "utf8").trim();
const isCarousel = urls.length >= 2;
console.log(`발행 시도: ${next.id} — ${next.hook} (${isCarousel ? "캐러셀 " + urls.length + "장" : "단일"})`);
urls.forEach((u, i) => console.log(`  [${i + 1}] ${u}`));

async function j(res) { const t = await res.text(); try { return JSON.parse(t); } catch { return { raw: t }; } }

// 컨테이너 상태가 FINISHED 될 때까지 폴링(사진은 대개 즉시).
async function waitFinished(id) {
  for (let i = 0; i < 12; i++) {
    const st = await j(await fetch(`${BASE}/${id}?fields=status_code&access_token=${TOKEN}`));
    if (st.status_code === "FINISHED") return true;
    if (st.status_code === "ERROR") { console.error("::error::컨테이너 처리 오류: " + JSON.stringify(st)); process.exit(1); }
    await new Promise((res) => setTimeout(res, 3000));
  }
  return true; // 상태 미확정이어도 발행 시도(단일 이미지 관대 처리)
}

let cid;
if (isCarousel) {
  // 1) 자식 컨테이너들 생성(is_carousel_item=true, 캡션 없음)
  const childIds = [];
  for (const u of urls) {
    const cf = new URLSearchParams();
    cf.set("image_url", u);
    cf.set("is_carousel_item", "true");
    cf.set("access_token", TOKEN);
    const cr = await j(await fetch(`${BASE}/${IG}/media`, { method: "POST", body: cf }));
    if (!cr.id) { console.error("::error::자식 컨테이너 실패: " + JSON.stringify(cr)); process.exit(1); }
    childIds.push(cr.id);
  }
  await Promise.all(childIds.map(waitFinished));
  // 2) 캐러셀 부모 컨테이너(children + caption)
  const pf = new URLSearchParams();
  pf.set("media_type", "CAROUSEL");
  pf.set("children", childIds.join(","));
  pf.set("caption", caption);
  pf.set("access_token", TOKEN);
  const pr = await j(await fetch(`${BASE}/${IG}/media`, { method: "POST", body: pf }));
  if (!pr.id) { console.error("::error::캐러셀 컨테이너 실패: " + JSON.stringify(pr)); process.exit(1); }
  cid = pr.id;
} else {
  // 단일 사진 컨테이너
  const form = new URLSearchParams();
  form.set("image_url", urls[0]);
  form.set("caption", caption);
  form.set("access_token", TOKEN);
  const cr = await j(await fetch(`${BASE}/${IG}/media`, { method: "POST", body: form }));
  if (!cr.id) { console.error("::error::컨테이너 생성 실패: " + JSON.stringify(cr)); process.exit(1); }
  cid = cr.id;
}

await waitFinished(cid);

// 발행
let r = await j(await fetch(`${BASE}/${IG}/media_publish`, {
  method: "POST",
  body: new URLSearchParams({ creation_id: cid, access_token: TOKEN })
}));
if (!r.id) { console.error("::error::발행 실패: " + JSON.stringify(r)); process.exit(1); }

console.log(`✓ 발행 완료: ${next.id} → media_id=${r.id}`);
next.published = true;
next.publishedAt = new Date().toISOString();
next.mediaId = r.id;
fs.writeFileSync(QUEUE, JSON.stringify(q, null, 2) + "\n");

const left = q.posts.filter((p) => !p.published).length;
console.log(`남은 큐: ${left}개`);
