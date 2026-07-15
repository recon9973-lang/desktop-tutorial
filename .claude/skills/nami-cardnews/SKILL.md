---
name: nami-cardnews
description: 배나미(GROUND @ground_geo) 인스타그램 카드뉴스 제작·발행 스킬. 배나미 페르소나로 SEO/GEO/AEO 개념을 5장 캐러셀 카드뉴스로 만들고 자동 발행한다. "배나미", "GROUND 인스타", "카드뉴스 만들어", "그라운드 발행"이라고 하면 실행.
---

# 배나미 카드뉴스 (GROUND @ground_geo)

배나미 페르소나로 SEO/GEO/AEO 개념을 **5장 캐러셀 카드뉴스**로 만들어 인스타그램에 하루 1개씩 자동 발행하는 전체 파이프라인. 아래 확정 규칙을 **그대로** 따른다.

## 페르소나 · 브랜드
- 계정: **@ground_geo** (IG Business ID `17841472664941872`)
- 배나미: 25세 한국인 여성, 자연스러운 캔디드 톤, **"훅 먼저 → 정보 뒤"**
- 정체성 기준 이미지: `persona-nami/nami-face.png` (jsDelivr로 Higgsfield에 import)
- 디자인 토큰: 라임 `#C7F24E` · 에메랄드 `#12574F` · 잉크 `#14201d` · 크림 `#F4F1E8`

## 캐러셀 구조 (항상 5장)
1. **커버** — 배나미 사진(**이 장만 인물 등장**) + 형광펜 훅
2. **인트로** — 개념 한 줄 + 부제 (인물 없음)
3. **포인트** — 핵심 3~4가지 (라임 숫자 스티커)
4. **팁** — 한 줄 강조(에메랄드 배경)
5. **CTA** — GR[OU]ND 팔로우 유도

## 배나미 이미지 규칙 (확정)
1. **누끼 금지 → 테마 단색 배경에서 직접 생성.** 배경색을 커버색으로 삼으면 머리카락 매팅 문제가 원천 소멸(가장자리 완벽).
2. **날씨 맞춤 패션.** 발행 시점 **서울 날짜·날씨를 확인**(WebSearch)해 계절/기온에 맞는 옷. 예: 한여름 장마·33°C → 반팔·리넨·원피스 등.
3. **배포마다 다르게** — 얼굴 각도·표정·의상·배경색을 글마다 전부 다르게(한 사진 우려먹기 금지).
4. **얼굴·정체성 보존**(한국인, 새 인물 생성 금지), 손·손가락 인체 정상(Higgsfield 위젯에서 눈으로 QC — 샌드박스는 생성물 열람 불가), 생성 프롬프트에 **텍스트·로고·워터마크 없음** 명시.
5. 인물은 **프레임 오른쪽**에 두고 **왼쪽에 여백**(텍스트 자리).
- 모델: `nano_banana_2`(=nano_banana_flash), medias role `image`에 nami-face media_id, aspect_ratio `1:1`.

## 커버·카드 디자인 규칙 (확정)
- **텍스트가 배나미를 가리면 안 됨** — 훅은 왼쪽 영역(`right:496`)에만.
- **문장 간격 넓게** — 커버 훅 `line-height:1.42`, 카드 본문 `1.5~1.6`.
- 콘텐츠 카드(2~5장)는 **인물 없이** 커버와 톤앤매너 통일(크림/에메랄드 + 형광펜 + 손그림 두들 spark/star/squig).
- 인트로·포인트 카드 본문은 **세로 중앙 정렬**(상단 쏠림 금지).
- 커버: 어두운 배경=흰 글자+라임 형광펜 / 밝은 배경=잉크 글자+에메랄드 형광펜.

## 제작 파이프라인 (샌드박스 egress 차단 우회)
샌드박스는 외부 CDN(생성물) 접근·합성이 불가 → **GitHub Actions 러너에서 합성**한다.
1. **생성**: Higgsfield `generate_image`(nano_banana_2) → 각 글 배나미 1장(테마 단색배경) → `show_generations`로 rawUrl 확보.
2. **커버 매니페스트**: `persona-nami/ig/cover-manifest.json` = `[{post,id,dark,hookHtml,photo(cloudfront url)}]`.
3. **커버 합성**: `.github/workflows/build-covers.yml`(workflow_dispatch) 실행 → 러너가 setup-chrome + fonts-noto-cjk 설치 후 `build-cover.mjs`로 full-bleed 합성 → `persona-nami/ig/postN.png` 커밋.
4. **콘텐츠 카드(2~5장)**: 텍스트뿐이라 **샌드박스에서 직접 렌더**(headless chrome) → 커밋. 생성 스크립트: `.claude/skills/nami-cardnews/render-content-cards.py`.
5. **큐**: `persona-nami/ig/queue.json` 각 글 `images:[postN, postN-2..-5]`(5장), `cap: postN.txt`.
6. **커밋 후 pull** 하면 합성 결과가 로컬에 생겨 **Read로 직접 QC** 가능.

## 발행 · 자동화
- **발행**: `.github/workflows/publish-ig.yml` — 매일 21:00 KST cron + workflow_dispatch. `publish-next.mjs`가 큐의 다음 미발행 1건을 캐러셀(자식 컨테이너→CAROUSEL→media_publish)로 발행 후 큐 상태 커밋.
- **토큰**: 발행 시크릿 `IG_TOKEN`. 자동갱신 `.github/workflows/refresh-ig-token.yml`(매월, `META_APP_SECRET`+`GH_PAT` 필요).
- 워크플로우는 **기본 브랜치(main)에 있어야** cron·dispatch가 작동(작업 브랜치만 두면 안 켜짐).

## 작업 순서 요약
1. 발행 시점 서울 날씨 확인 → 계절 룩 결정
2. Higgsfield로 글 수만큼 배나미 생성(배경색·각도·표정·룩 상이) → QC(위젯) → rawUrl 수집
3. cover-manifest 갱신 → build-covers 워크플로우로 커버 합성·커밋
4. render-content-cards.py로 2~5장 렌더·커밋
5. queue.json 5장 반영 → main 병합
6. publish-ig 트리거(또는 cron 대기)

## 금지 · 주의
- 의료·과장·보장·최상급 표현 배제. 실제 통계·인용 지어내기 금지.
- 커밋/PR/코드에 모델 ID 넣지 않기.
- 중복 이미지 사용 금지(글마다 다른 컷).
