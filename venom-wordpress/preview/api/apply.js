'use strict';

/* 베놈 체크업 — 무료 진단 신청 접수 (내부용, Airtable 저장)
 *
 *  POST /api/apply   { hospital, department, ... , consent:{...} }
 *   → 검증(필수값·필수동의·허니팟) 후 Airtable "진단 신청" 테이블에 1행 생성.
 *   → 동의 증적(일시·문구버전·항목·채널)과 신청자 IP를 함께 기록.
 *
 *  필요 환경변수 (Vercel → Settings → Environment Variables):
 *   - AIRTABLE_TOKEN     : Airtable 개인 액세스 토큰 (scope: data.records:write, schema.bases:read)
 *   - AIRTABLE_BASE_ID   : (기본 appvjDAassfO6Q39W)
 *   - AIRTABLE_TABLE     : (기본 진단 신청)
 *
 *  토큰은 서버(Vercel)에만 두므로 정적 페이지에 노출되지 않는다.
 */

const BASE_ID = process.env.AIRTABLE_BASE_ID || 'appvjDAassfO6Q39W';
const TABLE   = process.env.AIRTABLE_TABLE   || '진단 신청';
const TOKEN   = process.env.AIRTABLE_TOKEN;

// CORS 허용 출처 (허브·랜딩 배포 도메인). 그 외는 차단.
const ALLOW_ORIGINS = [
  'https://recon9973-lang.github.io',
  'https://desktop-tutorial-chi-peach.vercel.app',
];

function setCors(req, res) {
  const origin = (req.headers && req.headers.origin) || '';
  if (ALLOW_ORIGINS.includes(origin)) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

async function readBody(req) {
  let body = req.body;
  if (body && typeof body === 'object' && !Array.isArray(body)) return body;
  const chunks = [];
  await new Promise((resolve, reject) => {
    req.on('data', c => chunks.push(c));
    req.on('end', resolve);
    req.on('error', reject);
  });
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return {}; }
}

module.exports = async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ ok: false, error: 'Method not allowed' }); return; }

  try {
    const b = await readBody(req);

    // 1) 허니팟 — 봇이 채우는 숨은 필드가 있으면 조용히 성공 처리(정보 노출 방지)
    if (b.company_website) { res.status(200).json({ ok: true }); return; }

    // 2) 필수값·필수동의 검증
    const consent = b.consent || {};
    if (!b.hospital || !b.name || !b.phone) {
      res.status(400).json({ ok: false, error: '필수 항목이 누락되었습니다.' }); return;
    }
    if (!consent.privacy || !consent.terms) {
      res.status(400).json({ ok: false, error: '필수 동의 항목에 동의가 필요합니다.' }); return;
    }
    if (!TOKEN) {
      res.status(500).json({ ok: false, error: '서버 설정 오류(AIRTABLE_TOKEN 미설정)' }); return;
    }

    // 3) 신청자 IP (증적) — 프록시 헤더에서 추출
    const fwd = (req.headers['x-forwarded-for'] || '').split(',')[0].trim();
    const ip = fwd || req.socket?.remoteAddress || '';

    // 4) 광고 수신 채널 정규화
    const chMap = { ad_sms: '문자', ad_email: '이메일', ad_call: '전화' };
    const channels = Array.isArray(b.adChannels)
      ? b.adChannels.map(c => chMap[c] || c).filter(Boolean) : [];

    const fields = {
      '병원명': String(b.hospital || ''),
      '신청일시': b.ts || new Date().toISOString(),
      '진료과목': String(b.department || ''),
      '주소': String(b.address || ''),
      '신청자 성명': String(b.name || ''),
      '직책': String(b.role || ''),
      '전화': String(b.phone || ''),
      '이메일': String(b.email || ''),
      '리포트 수령 방식': ({ '이메일': '이메일', '문자 링크': '문자', '둘 다': '이메일' })[b.delivery] || undefined,
      '대표번호': String(b.tel || ''),
      '홈페이지 URL': String(b.url || ''),
      '관심 키워드': String(b.keywords || ''),
      '상담 희망': String(b.consult || ''),
      '문의사항': String(b.etc || ''),
      '동의:개인정보(필수)': !!consent.privacy,
      '동의:제공조건(필수)': !!consent.terms,
      '동의:상담(선택)': !!consent.consult,
      '동의:광고성수신(선택)': !!consent.ad,
      '광고 수신 채널': channels,
      '동의 문구 버전': String(b.policyVersion || ''),
      '신청자 IP': ip,
      '처리 상태': '신규',
    };
    // 빈 문자열/undefined 필드는 제거 (Airtable 오류 방지)
    Object.keys(fields).forEach(k => {
      if (fields[k] === '' || fields[k] === undefined) delete fields[k];
    });

    const air = await fetch(
      `https://api.airtable.com/v0/${BASE_ID}/${encodeURIComponent(TABLE)}`,
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ records: [{ fields }], typecast: true }),
        signal: AbortSignal.timeout(15000),
      }
    );
    const data = await air.json().catch(() => ({}));
    if (!air.ok) {
      res.status(502).json({ ok: false, error: 'Airtable 저장 실패', detail: data?.error?.message || air.status });
      return;
    }

    res.status(200).json({ ok: true, id: data?.records?.[0]?.id || null });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e && e.message || e).slice(0, 200) });
  }
};
