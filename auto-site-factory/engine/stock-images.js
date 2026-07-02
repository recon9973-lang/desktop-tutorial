'use strict';
// 카테고리/업종별 스톡 이미지
// 이미지는 사용자가 spec.images.hero 등으로 덮어쓸 수 있음
// 실사 이미지는 assets/images/ 에 있으며 raw.githubusercontent.com 으로 서빙

const REPO_RAW = 'https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/auto-site-factory/assets/images';

const G = (path, w) => {
  const url = `${REPO_RAW}/${path}`;
  return w ? `${url}?w=${w}` : url;
};

const CLINIC_HERO = {
  dental:   G('clinic/dental-hero.png'),
  skin:     G('clinic/skin-hero.png'),
  ortho:    G('clinic/ortho-hero.png'),
  plastic:  G('clinic/plastic-hero.png'),
  oriental: G('clinic/oriental-hero.png'),
  naegwa:   G('clinic/naegwa-hero.png'),
  angwa:    G('clinic/angwa-hero.png'),
  default:  G('clinic/naegwa-hero.png'),
};

const CLINIC_INTRO = {
  dental:   G('clinic/dental-intro.png'),
  skin:     G('clinic/skin-intro.png'),
  ortho:    G('clinic/ortho-intro.png'),
  plastic:  G('clinic/plastic-intro.png'),
  oriental: G('clinic/oriental-intro.png'),
  naegwa:   G('clinic/naegwa-intro.png'),
  angwa:    G('clinic/angwa-intro.png'),
  default:  G('clinic/naegwa-intro.png'),
};

const CLINIC_GALLERY = {
  dental:   [G('clinic/dental-gallery-1.png'), G('clinic/dental-gallery-2.png'), G('clinic/dental-gallery-3.png')],
  skin:     [G('clinic/skin-gallery-1.png'),   G('clinic/skin-gallery-2.png'),   G('clinic/skin-gallery-3.png')],
  ortho:    [G('clinic/ortho-gallery-1.png'),  G('clinic/ortho-gallery-2.png'),  G('clinic/ortho-gallery-3.png')],
  plastic:  [G('clinic/plastic-gallery-1.png'),G('clinic/plastic-gallery-2.png'),G('clinic/plastic-gallery-3.png')],
  oriental: [G('clinic/oriental-gallery-1.png'),G('clinic/oriental-gallery-2.png'),G('clinic/oriental-gallery-3.png')],
  naegwa:   [G('clinic/naegwa-gallery-1.png'), G('clinic/naegwa-gallery-2.png'), G('clinic/naegwa-gallery-3.png')],
  angwa:    [G('clinic/angwa-gallery-1.png'),  G('clinic/angwa-gallery-2.png'),  G('clinic/angwa-gallery-3.png')],
  default:  [G('clinic/naegwa-gallery-1.png'), G('clinic/naegwa-gallery-2.png'), G('clinic/naegwa-gallery-3.png')],
};

const LOCAL_HERO = {
  cafe:       G('local/cafe-hero.png'),
  restaurant: G('local/restaurant-hero.png'),
  beauty:     G('local/beauty-hero.png'),
  nail:       G('local/nail-hero.png'),
  fitness:    G('local/fitness-hero.png'),
  bakery:     G('local/bakery-hero.png'),
  retail:     G('local/retail-hero.png'),
  default:    G('local/cafe-hero.png'),
};

const LOCAL_INTRO = {
  cafe:       G('local/cafe-intro.png'),
  restaurant: G('local/restaurant-intro.png'),
  beauty:     G('local/beauty-intro.png'),
  nail:       G('local/nail-intro.png'),
  fitness:    G('local/fitness-intro.png'),
  bakery:     G('local/bakery-intro.png'),
  retail:     G('local/retail-intro.png'),
  default:    G('local/cafe-intro.png'),
};

const LOCAL_GALLERY = {
  cafe:       [G('local/cafe-gallery-1.png'),       G('local/cafe-gallery-2.png'),       G('local/cafe-gallery-3.png')],
  restaurant: [G('local/restaurant-gallery-1.png'), G('local/restaurant-gallery-2.png'), G('local/restaurant-gallery-3.png')],
  beauty:     [G('local/beauty-gallery-1.png'),     G('local/beauty-gallery-2.png'),     G('local/beauty-gallery-3.png')],
  nail:       [G('local/nail-gallery-1.png'),       G('local/nail-gallery-2.png'),       G('local/nail-gallery-3.png')],
  fitness:    [G('local/fitness-gallery-1.png'),    G('local/fitness-gallery-2.png'),    G('local/fitness-gallery-3.png')],
  bakery:     [G('local/bakery-gallery-1.png'),     G('local/bakery-gallery-2.png'),     G('local/bakery-gallery-3.png')],
  retail:     [G('local/retail-gallery-1.png'),     G('local/retail-gallery-2.png'),     G('local/retail-gallery-3.png')],
  default:    [G('local/cafe-gallery-1.png'),       G('local/cafe-gallery-2.png'),       G('local/cafe-gallery-3.png')],
};

const PRESS_HERO = {
  default: G('clinic/naegwa-hero.png'),
};

const LOCAL_PATH = '/home/user/desktop-tutorial/auto-site-factory/assets/images';

function localPath(relPath) {
  return `file://${LOCAL_PATH}/${relPath}`;
}

function getHero(category, subKey, local) {
  if (local) {
    if (category === 'clinic') return localPath(`clinic/${subKey || 'naegwa'}-hero.png`);
    if (category === 'local')  return localPath(`local/${subKey  || 'cafe'}-hero.png`);
    return localPath('clinic/naegwa-hero.png');
  }
  if (category === 'clinic')  return CLINIC_HERO[subKey]  || CLINIC_HERO.default;
  if (category === 'local')   return LOCAL_HERO[subKey]   || LOCAL_HERO.default;
  if (category === 'press')   return PRESS_HERO.default;
  return CLINIC_HERO.default;
}

function getIntro(category, subKey, local) {
  if (local) {
    if (category === 'clinic') return localPath(`clinic/${subKey || 'naegwa'}-intro.png`);
    if (category === 'local')  return localPath(`local/${subKey  || 'cafe'}-intro.png`);
    return localPath('clinic/naegwa-intro.png');
  }
  if (category === 'clinic') return CLINIC_INTRO[subKey] || CLINIC_INTRO.default;
  if (category === 'local')  return LOCAL_INTRO[subKey]  || LOCAL_INTRO.default;
  return CLINIC_INTRO.default;
}

function getGallery(category, subKey, local) {
  if (local) {
    const s = subKey || (category === 'local' ? 'cafe' : 'naegwa');
    const cat = category === 'local' ? 'local' : 'clinic';
    return [1,2,3].map(i => localPath(`${cat}/${s}-gallery-${i}.png`));
  }
  if (category === 'clinic') return CLINIC_GALLERY[subKey] || CLINIC_GALLERY.default;
  if (category === 'local')  return LOCAL_GALLERY[subKey]  || LOCAL_GALLERY.default;
  return [];
}

module.exports = { getHero, getIntro, getGallery };
