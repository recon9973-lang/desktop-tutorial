'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

const DUR_LABEL = { continuous: '🟢 지속 복용', monitor: '🟡 3개월 후 점검', cyclic: '🔴 8주 후 점검' };
const DUR_COLOR = { continuous: '#1aae39', monitor: '#dd5b00', cyclic: '#d63b3b' };

/* 서버에서 엔진 호출 대신, 클라이언트에서 API 호출 (실제 구현 시 /api/recommend) */
async function fetchRecommendation(user) {
  // TODO: 실제론 fetch('/api/recommend', { method:'POST', body: JSON.stringify(user) })
  // 데모: 정적 결과 반환
  return {
    recommended: [
      { ingredient_id: 'vitamin_d',      name: '비타민D',         evidence_level: 3, score: 1.3,  duration_type: 'monitor',    functions: ['칼슘 흡수·뼈 형성에 필요', '면역 기능 유지'], warnings: [], best_price: { price: 12900, count: 90, per_day: 143, vendor: '네이버', product: '뉴트리원 비타민D 2000IU 90정' } },
      { ingredient_id: 'vitamin_b_complex', name: '비타민B군',    evidence_level: 3, score: 1.0,  duration_type: 'continuous', functions: ['에너지 대사에 필요', '정상적 신경 기능'], warnings: [], best_price: { price: 18900, count: 60, per_day: 315, vendor: '쿠팡', product: '고려은단 비타민B 컴플렉스 60정' } },
      { ingredient_id: 'lutein',          name: '루테인',          evidence_level: 3, score: 1.0,  duration_type: 'continuous', functions: ['노화로 인한 눈 건강 유지에 도움'], warnings: [], best_price: { price: 15900, count: 90, per_day: 177, vendor: '아이허브', product: 'NOW 루테인 10mg 90정' } },
      { ingredient_id: 'magnesium',       name: '마그네슘',        evidence_level: 3, score: 0.7,  duration_type: 'continuous', functions: ['에너지 생성', '신경·근육 기능 유지'], warnings: [], best_price: { price: 14900, count: 120, per_day: 124, vendor: '네이버', product: '솔가 마그네슘 글리시네이트 120정' } },
      { ingredient_id: 'omega3',          name: '오메가3',         evidence_level: 3, score: 0.51, duration_type: 'continuous', functions: ['혈중 중성지방 개선', '혈행 개선'], warnings: ['와파린 복용 중이면 의사·약사 상담 후 결정하세요.'], best_price: { price: 21900, count: 90, per_day: 243, vendor: '쿠팡', product: '닥터스베스트 알티지 오메가3 90정' } },
    ],
    not_recommended: [
      { name: '홍국', reason: '스타틴 복용 중 병용 금지' },
    ],
    schedule: { morning: ['비타민D', '비타민B군', '루테인', '마그네슘'], evening: ['오메가3'] },
    interactions_note: [
      '🔗 비타민D + 마그네슘: 마그네슘이 비타민D 활성화에 관여 (함께 복용)',
      '🔗 비타민D + 칼슘: 뼈 형성 시너지 (함께 복용)',
    ],
  };
}

// 주요 구매처 검색 링크 (API 키·제휴 없이도 바로 동작하는 딥링크)
// 한국에서 영양제 구매가 많은 채널 순: 쿠팡 > 네이버쇼핑 > 아이허브(직구)
function buyLinks(name) {
  const q = encodeURIComponent(name);
  return [
    { vendor: '쿠팡',     url: `https://www.coupang.com/np/search?q=${q}`,                 color: '#ff4d4d' },
    { vendor: '네이버',   url: `https://search.shopping.naver.com/search/all?query=${q}`,  color: '#03c75a' },
    { vendor: '아이허브', url: `https://kr.iherb.com/search?kw=${q}`,                       color: '#4a9c2d' },
  ];
}

function StarBadge({ level }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, background: 'rgba(245,184,0,0.1)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>
      <span style={{ color: '#f5b800', fontSize: 12 }}>{'⭐'.repeat(level)}</span>
      <span style={{ fontSize: 11, color: 'var(--ink-muted)', fontWeight: 600 }}>
        {level === 3 ? '식약처 인정' : level === 2 ? 'NIH/논문' : '개별연구'}
      </span>
    </span>
  );
}

function ReviewBox({ ingredientId }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);

  if (submitted) return (
    <div style={{ background: 'var(--canvas-soft)', borderRadius: 'var(--r-md)', padding: '12px 14px', marginTop: 12 }}>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>✅ 의견 남겨주셨어요. 감사합니다! (추천 점수엔 반영되지 않아요)</p>
    </div>
  );

  return (
    <div style={{ borderTop: '1px solid var(--hairline)', marginTop: 12, paddingTop: 12 }}>
      <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 8, fontWeight: 600 }}>
        📝 이 성분에 대한 의견 (참고용 — 추천 근거와 별개)
      </p>
      <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
        {[1,2,3,4,5].map((n) => (
          <button key={n}
            onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(0)}
            onClick={() => setRating(n)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 22, padding: 2 }}
          >
            {n <= (hover || rating) ? '⭐' : '☆'}
          </button>
        ))}
        {rating > 0 && <span style={{ fontSize: 13, color: 'var(--ink-muted)', marginLeft: 6, alignSelf: 'center' }}>{rating}점</span>}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={comment} onChange={(e) => setComment(e.target.value)}
          placeholder="복용 경험을 간단히 남겨주세요"
          style={{
            flex: 1, background: 'var(--surface)', border: '1px solid #ddd', borderRadius: 'var(--r-xs)',
            padding: '7px 10px', fontSize: 14, color: 'var(--ink)', outline: 'none',
          }}
        />
        <button
          onClick={() => rating && setSubmitted(true)}
          disabled={!rating}
          style={{
            background: rating ? 'var(--primary)' : 'var(--hairline)',
            color: rating ? '#fff' : 'var(--ink-faint)',
            border: 'none', borderRadius: 'var(--r-md)', padding: '7px 16px', fontSize: 14, cursor: rating ? 'pointer' : 'not-allowed',
          }}
        >
          남기기
        </button>
      </div>
    </div>
  );
}

export default function ResultPage() {
  const [result, setResult] = useState(null);
  const [kakaoSent, setKakaoSent] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem('survey_user');
    const user = raw ? JSON.parse(raw) : { concerns: ['fatigue', 'eye'], medications: [], allergies: [] };
    fetchRecommendation(user).then(setResult);
  }, []);

  if (!result) return (
    <div style={{ textAlign: 'center', padding: '120px 24px' }}>
      <p className="title" style={{ color: 'var(--ink-muted)' }}>🧬 분석 중...</p>
    </div>
  );

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      {/* Result hero */}
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '48px 24px 56px', textAlign: 'center' }}>
        <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 16, display: 'inline-flex' }}>
          근거 기반 맞춤 추천
        </span>
        <h1 style={{ fontSize: 36, fontWeight: 700, letterSpacing: -0.75, marginBottom: 8 }}>
          🧬 당신의 영양제
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 15 }}>
          모든 추천은 식약처 인정 근거 기반 · 후기·광고 미반영
        </p>

        {/* Kakao send */}
        <button
          onClick={() => setKakaoSent(true)}
          style={{
            marginTop: 24, background: '#FEE500', color: '#3A1D1D',
            border: 'none', borderRadius: 'var(--r-full)', padding: '10px 28px',
            fontWeight: 700, fontSize: 15, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8,
          }}
        >
          {kakaoSent ? '✅ 카카오톡으로 전송됨' : '💬 카카오톡으로 받기'}
        </button>
      </div>

      <div style={{ maxWidth: 680, margin: '0 auto', padding: '32px 24px' }}>

        {/* Schedule box */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--r-xl)', border: '1px solid var(--hairline)', padding: '20px 24px', marginBottom: 24 }}>
          <h2 className="title" style={{ marginBottom: 16 }}>📅 오늘의 복용 스케줄</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[['☀️ 아침', result.schedule.morning], ['🌙 저녁', result.schedule.evening]].map(([label, items]) => (
              <div key={label} style={{ background: 'var(--canvas-soft)', borderRadius: 'var(--r-md)', padding: '12px 14px' }}>
                <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>{label}</p>
                {items.length ? items.map((n) => (
                  <p key={n} style={{ fontSize: 14, color: 'var(--ink-secondary)', marginBottom: 4 }}>• {n}</p>
                )) : <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>없음</p>}
              </div>
            ))}
          </div>
        </div>

        {/* Interaction notes */}
        {result.interactions_note.length > 0 && (
          <div style={{ background: 'rgba(0,117,222,0.05)', borderRadius: 'var(--r-lg)', border: '1px solid rgba(0,117,222,0.15)', padding: '16px 20px', marginBottom: 24 }}>
            {result.interactions_note.map((n, i) => (
              <p key={i} style={{ fontSize: 14, color: 'var(--ink-secondary)', marginBottom: i < result.interactions_note.length - 1 ? 8 : 0 }}>{n}</p>
            ))}
          </div>
        )}

        {/* Recommended list */}
        <h2 className="title" style={{ marginBottom: 16 }}>✅ 추천 영양제</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 28 }}>
          {result.recommended.map((r, i) => (
            <div key={r.ingredient_id} className="card-elevated" style={{ borderRadius: 'var(--r-xl)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                {/* Rank */}
                <div style={{
                  width: 36, height: 36, borderRadius: 'var(--r-md)',
                  background: i === 0 ? 'var(--primary)' : 'var(--canvas-soft)',
                  color: i === 0 ? '#fff' : 'var(--ink-muted)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 700, fontSize: 15, flexShrink: 0,
                }}>
                  {i + 1}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Header row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                    <strong style={{ fontSize: 17 }}>{r.name}</strong>
                    <StarBadge level={r.evidence_level} />
                    <span style={{
                      fontSize: 12, fontWeight: 600, color: DUR_COLOR[r.duration_type],
                      background: `${DUR_COLOR[r.duration_type]}15`,
                      borderRadius: 'var(--r-full)', padding: '2px 8px',
                    }}>
                      {DUR_LABEL[r.duration_type]}
                    </span>
                  </div>

                  {/* Functions */}
                  <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 6 }}>
                    {r.functions.join(' · ')}
                  </p>

                  {/* Warnings */}
                  {r.warnings.length > 0 && (
                    <div style={{ background: '#fff8f0', borderRadius: 'var(--r-sm)', padding: '8px 10px', marginBottom: 8 }}>
                      {r.warnings.map((w, wi) => (
                        <p key={wi} style={{ fontSize: 13, color: 'var(--accent-orange)' }}>⚠️ {w}</p>
                      ))}
                    </div>
                  )}

                  {/* Best price — 하루당 가격으로 직관화 */}
                  {r.best_price && (
                    <div style={{ background: 'var(--canvas-soft)', borderRadius: 'var(--r-md)', padding: '10px 14px', marginTop: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink)' }}>
                          하루 약 {r.best_price.per_day.toLocaleString()}원
                        </span>
                        <span style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
                          꼴 (₩{r.best_price.price.toLocaleString()} / {r.best_price.count}일분)
                        </span>
                      </div>
                      <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 4 }}>
                        📦 {r.best_price.product} · <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{r.best_price.vendor} 최저가</span>
                      </p>
                    </div>
                  )}

                  {/* 구매처 비교 — 실제 클릭되는 링크 (새 탭) */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, color: 'var(--ink-faint)', marginRight: 2 }}>가격 비교:</span>
                    {buyLinks(r.name).map((b) => (
                      <a key={b.vendor} href={b.url} target="_blank" rel="noopener noreferrer"
                        style={{
                          fontSize: 13, fontWeight: 600, color: b.color, textDecoration: 'none',
                          border: `1px solid ${b.color}40`, borderRadius: 'var(--r-full)', padding: '4px 12px',
                        }}>
                        {b.vendor} →
                      </a>
                    ))}
                  </div>

                  {/* Review box — 별점/의견 (근거와 분리) */}
                  <ReviewBox ingredientId={r.ingredient_id} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Not recommended */}
        {result.not_recommended.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <h2 className="title" style={{ marginBottom: 12 }}>❌ 당신껜 권하지 않아요</h2>
            <div className="card" style={{ borderRadius: 'var(--r-xl)' }}>
              {result.not_recommended.map((n, i) => (
                <div key={n.name} style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0',
                  borderBottom: i < result.not_recommended.length - 1 ? '1px solid var(--hairline)' : 'none',
                }}>
                  <span style={{ fontSize: 20 }}>🚫</span>
                  <div>
                    <strong style={{ fontSize: 15 }}>{n.name}</strong>
                    <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 2 }}>{n.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Register my supplement CTA */}
        <div className="card" style={{
          borderRadius: 'var(--r-xl)', background: 'var(--secondary)', border: 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
        }}>
          <div>
            <h3 style={{ fontSize: 17, fontWeight: 700, color: '#fff', marginBottom: 4 }}>📦 내 영양제 등록하기</h3>
            <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)' }}>섭취 시간 알람 · 복용 점검 · 조합 충돌 확인</p>
          </div>
          <button style={{
            background: '#fff', color: 'var(--secondary)',
            border: 'none', borderRadius: 'var(--r-full)', padding: '10px 24px',
            fontWeight: 700, fontSize: 15, cursor: 'pointer', whiteSpace: 'nowrap',
          }}>
            등록하기 →
          </button>
        </div>

        {/* Disclaimer */}
        <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 32, lineHeight: 1.6 }}>
          ⚠️ 본 추천은 질병의 진단·치료가 아닌 정보 제공 목적입니다.<br />
          복용 전 의사·약사와 상담하시고, 기능성 문구는 식약처 인정 원료 고시 기준입니다.
        </p>

        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <Link href="/survey" className="btn-secondary" style={{ fontSize: 14 }}>
            ← 설문 다시 하기
          </Link>
        </div>
      </div>
    </div>
  );
}
