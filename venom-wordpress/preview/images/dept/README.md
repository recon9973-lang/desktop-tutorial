# 진료과목 이미지 폴더

상세페이지(진료과목·스포크)에서 자동으로 불러오는 이미지 폴더입니다.
파일이 없으면 그라디언트 배경 + 캡션이 대신 노출되므로(깨지지 않음),
아래 파일명으로 이미지를 추가하면 해당 위치에 자동으로 표시됩니다.

> **필요한 사진 목록은 [`PHOTO-LIST.md`](./PHOTO-LIST.md) 참고** — Tier별로 정리되어 있습니다.

## 파일명 규칙
- 진료과목 대표(히어로/관련카드): `images/dept/{과목}.jpg`
- 진료과목 섹션 이미지(개별): `images/dept/{과목}-{섹션}.jpg`
- 섹션 공용 컷(권장): `images/dept/_sec-{유형}.jpg`
  - 개별 컷이 없을 때 같은 유형(definition·process·caution 등)의 공용 컷을 자동 재사용합니다.
  - 우선순위: `{과목}-{섹션}.jpg` → `_sec-{유형}.jpg` → 그라디언트 배경
  - 예) `dental_navi_implant-process.jpg` 가 없으면 `_sec-process.jpg` 를 사용

## 치과(dental) 예시 — 현재 강화 적용됨
- dental.jpg              (대표)
- dental-implant.jpg      (임플란트 센터)
- dental-ortho.jpg        (치아교정 센터)
- dental-cosmetic.jpg     (심미보철·화이트닝)
- dental-conservative.jpg (일반·보존 치료)
- dental-prevention.jpg   (예방·잇몸 치료)

## 관련 마케팅 서비스 카드
관련 서비스 카드도 `images/dept/{과목}.jpg`(예: skin.jpg, ortho.jpg …)를 사용합니다.

권장 사이즈: 가로형 16:7 이상, 1200px+ 폭. jpg/webp.
