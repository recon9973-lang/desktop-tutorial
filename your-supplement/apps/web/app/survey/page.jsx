'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import surveyData from '../../data/survey.json';

const TOTAL = surveyData.steps.length;

/* ── 공통 스타일 ── */
const S = {
  chip: (active) => ({
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', borderRadius: 'var(--r-full)', cursor: 'pointer',
    border: active ? '2px solid var(--primary)' : '1.5px solid var(--hairline)',
    background: active ? 'rgba(0,117,222,0.06)' : 'var(--surface)',
    color: active ? 'var(--primary)' : 'var(--ink)',
    fontWeight: active ? 600 : 400, fontSize: 15,
    transition: 'all 0.15s', userSelect: 'none',
    boxShadow: active ? 'none' : 'var(--shadow-soft)',
  }),
  concernCard: (active) => ({
    display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
    borderRadius: 'var(--r-lg)', cursor: 'pointer',
    border: active ? '2px solid var(--primary)' : '1.5px solid var(--hairline)',
    background: active ? 'rgba(0,117,222,0.05)' : 'var(--surface)',
    transition: 'all 0.15s', userSelect: 'none',
    boxShadow: active ? 'none' : 'var(--shadow-soft)',
  }),
};

function ChipGroup({ options, value, onChange, multi = false, noneOption }) {
  const selected = new Set(Array.isArray(value) ? value : value ? [value] : []);

  // isNoneButton: 멀티선택의 "없음" 버튼(전체 해제)일 때만 true.
  // 단일선택(생활습관)의 value:'none'은 정상 선택지이므로 일반 경로로 처리.
  const toggle = (v, isNoneButton = false) => {
    if (isNoneButton) { onChange([]); return; }
    if (!multi) { onChange(v === value ? '' : v); return; }
    const next = new Set(selected);
    next.has(v) ? next.delete(v) : next.add(v);
    onChange([...next]);
  };

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
      {noneOption && (
        <button style={S.chip(selected.size === 0)} onClick={() => toggle(null, true)}>
          {noneOption.label}
        </button>
      )}
      {options.map((o) => (
        <button key={o.value} style={S.chip(selected.has(o.value))} onClick={() => toggle(o.value)}>
          {o.icon && <span>{o.icon}</span>}
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ConcernGrid({ options, value, onChange }) {
  const selected = new Set(value || []);
  const toggle = (v) => {
    const next = new Set(selected);
    next.has(v) ? next.delete(v) : next.add(v);
    onChange([...next]);
  };
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
      {options.map((o) => (
        <button key={o.value} style={S.concernCard(selected.has(o.value))} onClick={() => toggle(o.value)}>
          <span style={{ fontSize: 24, flexShrink: 0 }}>{o.emoji}</span>
          <div style={{ textAlign: 'left' }}>
            <p style={{ fontWeight: 600, fontSize: 15, color: selected.has(o.value) ? 'var(--primary)' : 'var(--ink)' }}>
              {o.label}
            </p>
            <p style={{ fontSize: 13, color: 'var(--ink-faint)', marginTop: 2 }}>{o.hint}</p>
          </div>
        </button>
      ))}
    </div>
  );
}

export default function SurveyPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({
    age_range: '', sex: '',
    concerns: [],
    smoking: '', drinking: '', exercise: '',
    medications: [], allergies: [],
  });

  const current = surveyData.steps[step];
  const progress = ((step + 1) / TOTAL) * 100;

  const update = (key, val) => setAnswers((prev) => ({ ...prev, [key]: val }));

  const canNext = () => {
    if (current.id === 'profile') return answers.age_range && answers.sex;
    if (current.id === 'concerns') return answers.concerns.length > 0;
    return true;
  };

  const handleNext = () => {
    if (step < TOTAL - 1) { setStep((s) => s + 1); window.scrollTo(0, 0); }
    else handleSubmit();
  };

  const handleSubmit = () => {
    const user = {
      profile: { age_range: answers.age_range, sex: answers.sex },
      concerns: answers.concerns,
      medications: answers.medications.filter((m) => m !== 'none'),
      allergies: answers.allergies.filter((a) => a !== 'none'),
      lifestyle: { smoking: answers.smoking, drinking: answers.drinking, exercise: answers.exercise },
    };
    // 세션 스토리지에 저장 → 결과 페이지에서 읽어 엔진 호출
    sessionStorage.setItem('survey_user', JSON.stringify(user));
    router.push('/result');
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--canvas-soft)' }}>
      {/* Progress bar */}
      <div style={{ height: 4, background: 'var(--hairline)' }}>
        <div style={{ height: '100%', width: `${progress}%`, background: 'var(--primary)', transition: 'width 0.3s' }} />
      </div>

      <div style={{ maxWidth: 600, margin: '0 auto', padding: '48px var(--sp-lg)' }}>
        {/* Step indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
          <span className="badge">{step + 1} / {TOTAL}</span>
          <span className="eyebrow" style={{ color: 'var(--ink-faint)' }}>
            {current.id === 'profile' && '기본 정보'}
            {current.id === 'concerns' && '고민 선택'}
            {current.id === 'lifestyle' && '생활 습관'}
            {current.id === 'medications' && '복용 약'}
            {current.id === 'allergies' && '알레르기'}
          </span>
        </div>

        {/* Question */}
        <h1 className="heading-2" style={{ marginBottom: 8 }}>{current.title}</h1>
        <p className="body-sm" style={{ color: 'var(--ink-muted)', marginBottom: 32 }}>{current.subtitle}</p>

        {/* Step: profile */}
        {current.id === 'profile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            {current.fields.map((field) => (
              <div key={field.id}>
                <p style={{ fontWeight: 600, marginBottom: 12, fontSize: 15 }}>{field.label}</p>
                <ChipGroup options={field.options} value={answers[field.id]} onChange={(v) => update(field.id, v)} />
              </div>
            ))}
          </div>
        )}

        {/* Step: concerns */}
        {current.id === 'concerns' && (
          <ConcernGrid options={current.options} value={answers.concerns} onChange={(v) => update('concerns', v)} />
        )}

        {/* Step: lifestyle */}
        {current.id === 'lifestyle' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            {current.fields.map((field) => (
              <div key={field.id}>
                <p style={{ fontWeight: 600, marginBottom: 4, fontSize: 15 }}>{field.label}</p>
                {field.note && <p style={{ fontSize: 13, color: 'var(--accent-orange)', marginBottom: 12 }}>{field.note}</p>}
                <ChipGroup options={field.options} value={answers[field.id]} onChange={(v) => update(field.id, v)} />
              </div>
            ))}
          </div>
        )}

        {/* Step: medications */}
        {current.id === 'medications' && (
          <ChipGroup
            options={current.options} value={answers.medications}
            onChange={(v) => update('medications', v)}
            multi noneOption={current.none_option}
          />
        )}

        {/* Step: allergies */}
        {current.id === 'allergies' && (
          <ChipGroup
            options={current.options} value={answers.allergies}
            onChange={(v) => update('allergies', v)}
            multi noneOption={current.none_option}
          />
        )}

        {/* Navigation */}
        <div style={{ display: 'flex', gap: 12, marginTop: 48, justifyContent: 'space-between', alignItems: 'center' }}>
          {step > 0 ? (
            <button className="btn-secondary" onClick={() => setStep((s) => s - 1)} style={{ padding: '10px 24px' }}>
              ← 이전
            </button>
          ) : <span />}

          <button
            className="btn-primary"
            onClick={handleNext}
            disabled={!canNext()}
            style={{ padding: '10px 32px', opacity: canNext() ? 1 : 0.45, cursor: canNext() ? 'pointer' : 'not-allowed' }}
          >
            {step === TOTAL - 1 ? '결과 보기 🧬' : '다음 →'}
          </button>
        </div>

        {/* Skip option for optional steps */}
        {!current.required && step < TOTAL - 1 && (
          <p style={{ textAlign: 'center', marginTop: 16 }}>
            <button onClick={handleNext} style={{ background: 'none', border: 'none', color: 'var(--ink-faint)', cursor: 'pointer', fontSize: 14 }}>
              건너뛰기
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
