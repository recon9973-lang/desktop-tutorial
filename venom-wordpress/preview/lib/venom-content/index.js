// ============================================================
// venom-content — L0 콘텐츠 파이프라인 (P1: 비파괴 배럴)
// ============================================================
// 목적: 사이트 lib/* 에 흩어진 콘텐츠 생성 모듈을 7스테이지 파이프라인
//       하나의 표면(surface)으로 재노출한다. 코드 이동 없음 → 사이트 무영향.
//       다른 화면(ERP 원고스튜디오·스킬·seo-generator)이 이 한 곳을 import.
//
// 설계: docs/L0-content-pipeline.md
// 스테이지: research → generate → image → validate(게이트) → design → structure → publish
//
// 방어적 require: 특정 모듈이 없거나 로드 실패해도 배럴 전체가 죽지 않는다.
// ============================================================

function opt(path) {
  try {
    return require(path);
  } catch (e) {
    return { __unavailable: true, __reason: e && e.message };
  }
}

const pipeline = {
  // 1) 키워드·주제 리서치 (Naver 검색광고·데이터랩·자동완성)
  research: opt('../keyword-research'),

  // 2) 본문·메타 생성 (GPT). seo-writing-skill 규격과 호환.
  generate: opt('../post-generator'),
  openai: opt('../openai-client'),

  // 3) 이미지 생성/변환 (DALL-E). webp·Higgsfield/Canva는 이미지 스튜디오와 공유.
  image: opt('../image-generator'),

  // 다국어
  translate: opt('../translate'),

  // 4) ⛔ 검증 게이트 — 모든 발행 경로 필수 통과 (의료광고법 + 콘텐츠 검수)
  validate: {
    medicalAd: opt('../medical-ad-validator'),
    content: opt('../content-validator'),
  },

  // 5) 브랜드 스타일 적용
  design: opt('../post-designer'),

  // 6) 구조화(JSON-LD·사이트맵)
  structure: {
    sitemap: opt('../sitemap-builder'),
  },

  // 7) 발행 어댑터 (GitHub 저장. WordPress/Vercel은 후속 어댑터.)
  publish: {
    github: opt('../github-store'),
  },
};

// 로드 상태 진단(운영 확인용)
pipeline.status = function status() {
  const flat = {
    research: pipeline.research,
    generate: pipeline.generate,
    image: pipeline.image,
    'validate.medicalAd': pipeline.validate.medicalAd,
    'validate.content': pipeline.validate.content,
    design: pipeline.design,
    'structure.sitemap': pipeline.structure.sitemap,
    'publish.github': pipeline.publish.github,
  };
  const out = {};
  for (const [k, v] of Object.entries(flat)) {
    out[k] = v && v.__unavailable ? `MISSING: ${v.__reason}` : 'ok';
  }
  return out;
};

module.exports = pipeline;
