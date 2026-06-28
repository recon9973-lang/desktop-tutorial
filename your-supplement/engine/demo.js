// 추천 엔진 검증용 데모 — 가상 사용자
const { recommend } = require('./recommend');

const user = {
  id: 'u_demo',
  profile: { age: 34, sex: 'F' },
  concerns: ['fatigue', 'eye', 'bone_joint'], // 피로 + 눈 + 뼈/관절
  medications: ['warfarin'],                   // 와파린(항응고제)
  allergies: [],
};

const result = recommend(user);

console.log('================  🧬 당신의 영양제 (데모)  ================');
console.log(`사용자: ${user.profile.age}세 ${user.profile.sex}, 복용약: ${user.medications.join(', ') || '없음'}`);
console.log(`고민: ${user.concerns.join(', ')}\n`);

console.log('── ✅ 추천 (점수순) ───────────────────────────');
for (const r of result.recommended) {
  const stars = '⭐'.repeat(r.evidence_level);
  const dur = { continuous: '🟢지속', monitor: '🟡점검', cyclic: '🔴주기' }[r.duration_type];
  console.log(`• ${r.name}  [${stars} / ${dur}]  score=${r.score}`);
  console.log(`    기능: ${r.functions.join(', ')}`);
  if (r.warnings.length) console.log(`    ⚠️ ${r.warnings.join(' / ')}`);
}

console.log('\n── ❌ 당신껜 권하지 않음 ──────────────────────');
if (result.not_recommended.length === 0) console.log('  (없음)');
for (const n of result.not_recommended) console.log(`• ${n.name}: ${n.reason}`);

console.log('\n── 📅 복용 스케줄 ────────────────────────────');
console.log(`  아침: ${result.schedule.morning.join(', ') || '-'}`);
console.log(`  저녁: ${result.schedule.evening.join(', ') || '-'}`);

console.log('\n── 🔗 상호작용 안내 ──────────────────────────');
if (result.interactions_note.length === 0) console.log('  (해당 없음)');
for (const note of result.interactions_note) console.log(`  ${note}`);
console.log('==========================================================');
