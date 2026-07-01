'use strict';
// 카테고리/업종별 큐레이션 Unsplash 스톡 이미지
// 이미지는 사용자가 spec.images.hero 등으로 덮어쓸 수 있음

const U = (id, w = 1920) =>
  `https://images.unsplash.com/photo-${id}?w=${w}&q=82&auto=format&fit=crop`;

const CLINIC_HERO = {
  dental:   U('1606811971618-4486d14f3f99'),  // 치과 진료실
  skin:     U('1570172619644-dfd03ed5d881'),  // 피부과
  ortho:    U('1576091160550-2173dba999ef'),  // 정형/재활
  plastic:  U('1522338140262-f46f5913618a'),  // 성형/미용
  oriental: U('1540206276207-99e3bf1da4a9'),  // 한의원
  naegwa:   U('1519494026892-80bbd2d6fd0d'),  // 내과/일반
  angwa:    U('1587440871838-2f68e35e6d73'),  // 안과
  default:  U('1551076805-e1869033e561'),     // 병원 일반
};

const CLINIC_INTRO = {
  dental:   U('1607613009820-a29f7bb81c04', 960),
  skin:     U('1522337360826-9a8dc6b6cf01', 960),
  ortho:    U('1581056771107-24ca5f033842', 960),
  plastic:  U('1576091160399-112ba8d25d1d', 960),
  oriental: U('1533804575768-c2d8e01d7bb6', 960),
  naegwa:   U('1530026405845-dba5ae3e888f', 960),
  angwa:    U('1614649024145-4294b8f0e81f', 960),
  default:  U('1519494026892-80bbd2d6fd0d', 960),
};

const CLINIC_GALLERY = {
  dental:   [U('1588776814546-1ffbb172b0a0',800), U('1628177142898-93e36e4e3a50',800), U('1606811971618-4486d14f3f99',800)],
  skin:     [U('1570172619644-dfd03ed5d881',800), U('1522337360826-9a8dc6b6cf01',800), U('1512290923902-8a9f81dc236c',800)],
  default:  [U('1519494026892-80bbd2d6fd0d',800), U('1530026405845-dba5ae3e888f',800), U('1551076805-e1869033e561',800)],
};

const LOCAL_HERO = {
  cafe:       U('1501339847302-ac426a4a7cbb'),
  restaurant: U('1414235077428-338989a2e8c0'),
  beauty:     U('1522335789203-aabd1fc54bc9'),
  nail:       U('1604654894610-df63bc536371'),
  fitness:    U('1534438327276-14e5300c3a48'),
  bakery:     U('1509440159596-0249088772ff'),
  retail:     U('1555529669-e69e7aa0ba9a'),
  default:    U('1556742049-0cfed4f6a45d'),
};

const LOCAL_INTRO = {
  cafe:       U('1495474472287-4d71bcdd2085', 960),
  restaurant: U('1517248135467-4c7edcad34c4', 960),
  beauty:     U('1560066984-138dafc5cbbd', 960),
  fitness:    U('1517836357463-d25dfeac3438', 960),
  bakery:     U('1587241321921-91a834d6d191', 960),
  default:    U('1504384308090-c5fb69dc7d6e', 960),
};

const PRESS_HERO = {
  newsroom: U('1504711434969-e33886168f5c'),
  blog:     U('1499750310107-5fef28a66643'),
  magazine: U('1585829365800-9b7b4567fb9b'),
  default:  U('1504711434969-e33886168f5c'),
};

function getHero(category, subKey) {
  if (category === 'clinic')  return CLINIC_HERO[subKey]  || CLINIC_HERO.default;
  if (category === 'local')   return LOCAL_HERO[subKey]   || LOCAL_HERO.default;
  if (category === 'press')   return PRESS_HERO[subKey]   || PRESS_HERO.default;
  return CLINIC_HERO.default;
}

function getIntro(category, subKey) {
  if (category === 'clinic') return CLINIC_INTRO[subKey] || CLINIC_INTRO.default;
  if (category === 'local')  return LOCAL_INTRO[subKey]  || LOCAL_INTRO.default;
  return CLINIC_INTRO.default;
}

function getGallery(category, subKey) {
  if (category === 'clinic') return CLINIC_GALLERY[subKey] || CLINIC_GALLERY.default;
  return [];
}

module.exports = { getHero, getIntro, getGallery };
