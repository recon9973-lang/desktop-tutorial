// 식약처 '건강기능식품 기능성 원료 인정현황'(data.go.kr 15058359) 배치 적재.
// 성분 KB 자동 확장·국내 인정문구(D1·D2) 보강용. 런타임이 아니라 데이터 빌드 작업.
//
// 사용:
//   MFDS_MATERIAL_API_URL="<활용신청 후 명세 엔드포인트>" \
//   DATA_GO_KR_KEY="<키>" \
//   node scripts/sync-mfds-materials.mjs
// → data/mfds_raw_materials.json 생성/갱신 (apps/web/data 미러 포함)
//
// ※ 정확한 오퍼레이션/파라미터는 활용신청 후 명세에만 있으므로 추측 하드코딩하지 않음.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');

const base = process.env.MFDS_MATERIAL_API_URL;
const key = process.env.DATA_GO_KR_KEY;
if (!base || !key) {
  console.error('✗ MFDS_MATERIAL_API_URL / DATA_GO_KR_KEY 환경변수가 필요합니다. (data.go.kr 15058359 활용신청)');
  process.exit(1);
}

async function page(pageNo) {
  const url = `${base}?serviceKey=${encodeURIComponent(key)}&type=json&numOfRows=100&pageNo=${pageNo}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('MFDS material ' + res.status);
  const data = await res.json();
  const rows = data?.body?.items || data?.response?.body?.items?.item || data?.items || [];
  return Array.isArray(rows) ? rows : [rows];
}

const out = [];
for (let p = 1; p <= 50; p++) {
  const rows = await page(p);
  if (!rows.length) break;
  for (const r of rows) {
    const s = r.item || r;
    out.push({
      name: s.RAWMTRL_NM || s.rawmtrlNm || s.INGR_NAME || s.name || '',
      function: s.FNCLTY_CN || s.fnclityCn || s.FUNCTIONALITY || '',
      daily_intake: s.DAY_INTK_CN || s.dayIntkCn || '',
      caution: s.IFTKN_ATNT_MATR_CN || s.iftknAtntMatrCn || '',
      approval_no: s.RECOG_NO || s.recogNo || s.PRDLST_REPORT_NO || null,
    });
  }
  console.log(`  page ${p}: +${rows.length} (총 ${out.length})`);
}

const payload = {
  _meta: {
    version: '0.1',
    source: '식약처 건강기능식품 기능성 원료 인정현황 (data.go.kr 15058359)',
    synced_at: new Date().toISOString().slice(0, 10),
    note: '원료명→기능성·일일섭취량·주의 매핑. 성분 KB 매칭(D1·D2)·검수용.',
  },
  materials: out,
};
for (const dir of ['data', 'apps/web/data']) {
  const file = path.join(ROOT, dir, 'mfds_raw_materials.json');
  fs.writeFileSync(file, JSON.stringify(payload, null, 2) + '\n');
  console.log('✓ wrote', file, '(', out.length, 'materials )');
}
