'use client';
import { useState, useRef } from 'react';

// 낱알식별 색상 표준값 → 대표 RGB (중앙부 평균색을 근접 매핑, 어디까지나 추정 힌트)
const COLOR_REF = [
  ['하양', [245, 245, 245]], ['노랑', [245, 208, 51]], ['주황', [239, 138, 58]],
  ['분홍', [241, 155, 176]], ['빨강', [224, 80, 58]], ['갈색', [138, 90, 58]],
  ['초록', [58, 168, 115]], ['파랑', [58, 123, 213]], ['보라', [138, 99, 196]],
  ['회색', [154, 168, 160]], ['검정', [51, 51, 51]],
];

// 이미지 중앙 영역 평균색 → 가장 가까운 표준 색상명 추정
function estimateColor(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      try {
        const c = document.createElement('canvas');
        const w = (c.width = 64), h = (c.height = 64);
        const ctx = c.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        // 중앙 50% 영역만 표본 (배경 영향 축소)
        const x0 = w * 0.25, y0 = h * 0.25, sw = w * 0.5, sh = h * 0.5;
        const { data } = ctx.getImageData(x0, y0, sw, sh);
        let r = 0, g = 0, b = 0, n = 0;
        for (let i = 0; i < data.length; i += 4) {
          if (data[i + 3] < 128) continue; // 투명 픽셀 제외
          r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
        }
        if (!n) return resolve('');
        r /= n; g /= n; b /= n;
        let best = '', bd = Infinity;
        for (const [name, [rr, gg, bb]] of COLOR_REF) {
          const d = (r - rr) ** 2 + (g - gg) ** 2 + (b - bb) ** 2;
          if (d < bd) { bd = d; best = name; }
        }
        resolve(best);
      } catch { resolve(''); }
    };
    img.onerror = () => resolve('');
    img.src = dataUrl;
  });
}

export default function DrugScanPage() {
  const [preview, setPreview] = useState(null);
  const [imageData, setImageData] = useState(null);
  const [result, setResult] = useState(null);
  const [colorHint, setColorHint] = useState('');
  const [loading, setLoading] = useState(false);
  const fileRef = useRef(null);

  function onFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = async () => {
      setPreview(reader.result); setImageData(reader.result); setResult(null); setColorHint('');
      const col = await estimateColor(reader.result);
      setColorHint(col);
    };
    reader.readAsDataURL(f);
  }

  // 각인/색 힌트를 실은 검색 링크
  function drugLink(imprint) {
    const qs = new URLSearchParams();
    if (imprint) qs.set('imprint', imprint);
    if (colorHint) qs.set('color', colorHint);
    return `/drug?${qs.toString()}`;
  }

  async function scan() {
    if (!imageData) return;
    setLoading(true); setResult(null);
    try {
      const res = await fetch('/api/drug/ocr', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData }),
      });
      setResult(await res.json());
    } catch { setResult({ source: 'error', imprint: '' }); }
    setLoading(false);
  }

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <div style={{ maxWidth: 640, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>사진으로 찾기 (베타)</span>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>📷 이 약 뭐지?</h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>알약을 촬영하면 <strong>각인을 읽어</strong> 후보를 찾아드려요</p>
        </div>
      </div>

      <div style={{ maxWidth: 640, margin: '0 auto', padding: '24px' }}>
        <div style={{ background: 'rgba(5,150,105,0.05)', border: '1px solid rgba(5,150,105,0.2)', borderRadius: 'var(--r-xl)', padding: '14px 18px', marginBottom: 16 }}>
          <p style={{ fontSize: 13.5, color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
            📸 <strong>촬영 팁</strong>: 밝은 곳에서 · 각인이 정면으로 · 알약 1개만 크게. 인식은 <strong>참고용</strong>이며 후보를 좁혀줄 뿐이에요.
          </p>
        </div>

        <input ref={fileRef} type="file" accept="image/*" capture="environment" onChange={onFile} style={{ display: 'none' }} />
        <button onClick={() => fileRef.current?.click()} className="btn-primary" style={{ width: '100%', padding: '13px', fontSize: 16 }}>
          📷 사진 촬영 / 앨범에서 선택
        </button>

        {preview && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <img src={preview} alt="알약 미리보기" style={{ maxWidth: '100%', maxHeight: 260, borderRadius: 'var(--r-xl)', border: '1px solid var(--hairline)' }} />
            {colorHint && (
              <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 8 }}>
                추정 색상: <strong style={{ color: 'var(--primary)' }}>{colorHint}</strong> <span style={{ color: 'var(--ink-faint)' }}>(검색 필터에 자동 적용돼요)</span>
              </p>
            )}
            <button onClick={scan} className="btn-primary" style={{ display: 'block', width: '100%', marginTop: 12, padding: '12px', fontSize: 15 }}>
              🔎 각인 읽어서 후보 찾기
            </button>
            {colorHint && (
              <a href={drugLink('')} style={{ display: 'block', marginTop: 8, fontSize: 14, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none' }}>
                각인 없이 색상({colorHint})으로 먼저 찾기 →
              </a>
            )}
          </div>
        )}

        {loading && <p style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: 30 }}>각인 인식 중…</p>}

        {result && (
          <div className="card" style={{ borderRadius: 'var(--r-xl)', marginTop: 16, textAlign: 'center', padding: '24px 20px' }}>
            {(result.source === 'clova' || result.source === 'vision') && result.imprint ? (
              <>
                <p style={{ fontSize: 14, color: 'var(--ink-muted)' }}>읽은 각인/식별문자</p>
                <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--primary)', margin: '4px 0 14px', letterSpacing: 1 }}>{result.imprint}</p>
                <a href={drugLink(result.imprint)} className="btn-primary" style={{ padding: '10px 22px', fontSize: 15, textDecoration: 'none' }}>이 각인으로 약 검색 →</a>
              </>
            ) : (
              <>
                <div style={{ fontSize: 32 }}>💊</div>
                <p style={{ fontSize: 15, fontWeight: 600, marginTop: 6 }}>
                  {result.source === 'unconfigured' ? '사진 각인 인식은 준비 중이에요' : '각인을 읽지 못했어요'}
                </p>
                <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '6px 0 16px' }}>
                  {result.source === 'unconfigured' ? '지금은 모양·색·각인 필터 검색을 이용해보세요.' : '더 밝게·정면으로 다시 찍거나, 필터 검색을 이용하세요.'}
                </p>
                <a href={drugLink('')} className="btn-primary" style={{ padding: '10px 22px', fontSize: 15, textDecoration: 'none' }}>
                  {colorHint ? `색상(${colorHint})·모양으로 검색하기 →` : '모양·색으로 검색하기 →'}
                </a>
              </>
            )}
          </div>
        )}

        <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 20, lineHeight: 1.6 }}>
          ⚠️ 사진 인식은 <strong>참고용 보조</strong>입니다. 후보 중 정확한 약은 <strong>포장·처방전 또는 약사</strong>로 확인하세요.<br />업로드 사진은 인식에만 쓰이고 저장되지 않습니다.
        </p>
      </div>
    </div>
  );
}
