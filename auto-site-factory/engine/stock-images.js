'use strict';
// 카테고리/업종별 스톡 이미지
// spec.images.hero 등으로 언제든지 사용자 이미지로 덮어쓸 수 있음

// GitHub raw CDN: assets/images/*.svg
const REPO_RAW = 'https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/auto-site-factory/assets/images';
const G = p => `${REPO_RAW}/${p}`;

const CLINIC_HERO = {
  dental:   G('clinic/dental-hero.svg'),
  skin:     G('clinic/skin-hero.svg'),
  ortho:    G('clinic/ortho-hero.svg'),
  plastic:  G('clinic/plastic-hero.svg'),
  oriental: G('clinic/oriental-hero.svg'),
  naegwa:   G('clinic/naegwa-hero.svg'),
  angwa:    G('clinic/angwa-hero.svg'),
  default:  G('clinic/naegwa-hero.svg'),
};

const CLINIC_INTRO = {
  dental:   G('clinic/dental-intro.svg'),
  skin:     G('clinic/skin-intro.svg'),
  ortho:    G('clinic/ortho-intro.svg'),
  plastic:  G('clinic/plastic-intro.svg'),
  oriental: G('clinic/oriental-intro.svg'),
  naegwa:   G('clinic/naegwa-intro.svg'),
  angwa:    G('clinic/angwa-intro.svg'),
  default:  G('clinic/naegwa-intro.svg'),
};

const CLINIC_GALLERY = {
  dental:   [G('clinic/dental-gallery-1.svg'),   G('clinic/dental-gallery-2.svg'),   G('clinic/dental-gallery-3.svg')],
  skin:     [G('clinic/skin-gallery-1.svg'),     G('clinic/skin-gallery-2.svg'),     G('clinic/skin-gallery-3.svg')],
  ortho:    [G('clinic/ortho-gallery-1.svg'),    G('clinic/ortho-gallery-2.svg'),    G('clinic/ortho-gallery-3.svg')],
  plastic:  [G('clinic/plastic-gallery-1.svg'),  G('clinic/plastic-gallery-2.svg'),  G('clinic/plastic-gallery-3.svg')],
  oriental: [G('clinic/oriental-gallery-1.svg'), G('clinic/oriental-gallery-2.svg'), G('clinic/oriental-gallery-3.svg')],
  naegwa:   [G('clinic/naegwa-gallery-1.svg'),   G('clinic/naegwa-gallery-2.svg'),   G('clinic/naegwa-gallery-3.svg')],
  angwa:    [G('clinic/angwa-gallery-1.svg'),    G('clinic/angwa-gallery-2.svg'),    G('clinic/angwa-gallery-3.svg')],
  default:  [G('clinic/naegwa-gallery-1.svg'),   G('clinic/naegwa-gallery-2.svg'),   G('clinic/naegwa-gallery-3.svg')],
};

// ── 소상공인 로컬 ──────────────────────────────────────────
const LOCAL_HERO = {
  cafe:       G('local/cafe-hero.svg'),
  restaurant: G('local/restaurant-hero.svg'),
  beauty:     G('local/beauty-hero.svg'),
  nail:       G('local/nail-hero.svg'),
  fitness:    G('local/fitness-hero.svg'),
  bakery:     G('local/bakery-hero.svg'),
  retail:     G('local/retail-hero.svg'),
  default:    G('local/cafe-hero.svg'),
};

const LOCAL_INTRO = {
  cafe:       G('local/cafe-intro.svg'),
  restaurant: G('local/restaurant-intro.svg'),
  beauty:     G('local/beauty-intro.svg'),
  nail:       G('local/nail-intro.svg'),
  fitness:    G('local/fitness-intro.svg'),
  bakery:     G('local/bakery-intro.svg'),
  retail:     G('local/retail-intro.svg'),
  default:    G('local/cafe-intro.svg'),
};

const LOCAL_GALLERY = {
  cafe:       [G('local/cafe-gallery-1.svg'),       G('local/cafe-gallery-2.svg'),       G('local/cafe-gallery-3.svg')],
  restaurant: [G('local/restaurant-gallery-1.svg'), G('local/restaurant-gallery-2.svg'), G('local/restaurant-gallery-3.svg')],
  beauty:     [G('local/beauty-gallery-1.svg'),     G('local/beauty-gallery-2.svg'),     G('local/beauty-gallery-3.svg')],
  nail:       [G('local/nail-gallery-1.svg'),       G('local/nail-gallery-2.svg'),       G('local/nail-gallery-3.svg')],
  fitness:    [G('local/fitness-gallery-1.svg'),    G('local/fitness-gallery-2.svg'),    G('local/fitness-gallery-3.svg')],
  bakery:     [G('local/bakery-gallery-1.svg'),     G('local/bakery-gallery-2.svg'),     G('local/bakery-gallery-3.svg')],
  retail:     [G('local/retail-gallery-1.svg'),     G('local/retail-gallery-2.svg'),     G('local/retail-gallery-3.svg')],
  default:    [G('local/cafe-gallery-1.svg'),       G('local/cafe-gallery-2.svg'),       G('local/cafe-gallery-3.svg')],
};

const PRESS_HERO = {
  default: G('clinic/naegwa-hero.svg'),
};

function localPath(relPath) {
  return `/assets/images/${relPath}`;
}

function getHero(category, subKey, local) {
  if (local) {
    if (category === 'clinic') return localPath(`clinic/${subKey || 'naegwa'}-hero.svg`);
    if (category === 'local')  return localPath(`local/${subKey  || 'cafe'}-hero.svg`);
    return localPath('clinic/naegwa-hero.svg');
  }
  if (category === 'clinic')  return CLINIC_HERO[subKey]  || CLINIC_HERO.default;
  if (category === 'local')   return LOCAL_HERO[subKey]   || LOCAL_HERO.default;
  if (category === 'press')   return PRESS_HERO.default;
  return CLINIC_HERO.default;
}

function getIntro(category, subKey, local) {
  if (local) {
    if (category === 'clinic') return localPath(`clinic/${subKey || 'naegwa'}-intro.svg`);
    if (category === 'local')  return localPath(`local/${subKey  || 'cafe'}-intro.svg`);
    return localPath('clinic/naegwa-intro.svg');
  }
  if (category === 'clinic') return CLINIC_INTRO[subKey] || CLINIC_INTRO.default;
  if (category === 'local')  return LOCAL_INTRO[subKey]  || LOCAL_INTRO.default;
  return CLINIC_INTRO.default;
}

function getGallery(category, subKey, local) {
  if (local) {
    const s   = subKey || (category === 'local' ? 'cafe' : 'naegwa');
    const cat = category === 'local' ? 'local' : 'clinic';
    return [1,2,3].map(i => localPath(`${cat}/${s}-gallery-${i}.svg`));
  }
  if (category === 'clinic') return CLINIC_GALLERY[subKey] || CLINIC_GALLERY.default;
  if (category === 'local')  return LOCAL_GALLERY[subKey]  || LOCAL_GALLERY.default;
  return [];
}

module.exports = { getHero, getIntro, getGallery };
