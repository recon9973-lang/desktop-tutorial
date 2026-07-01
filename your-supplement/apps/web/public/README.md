# public — 정적 자산

이 폴더의 파일은 배포 URL 루트에서 그대로 접근됩니다.
예) `public/hero.png` → `https://<도메인>/hero.png`

## 히어로 이미지 교체
1. 여기에 `hero.png`(랜딩 히어로 이미지) 업로드
2. `app/page.jsx`의 `HERO_IMG` 를 `'/hero.png'` 로 변경
