# tools/cardgen — 자동블로그 카드뉴스 렌더러

자동발행 블로그 글의 이미지를 **AI 사진 대신 브랜드 카드뉴스**로 생성한다.
(AI 사진의 거부감·깨진 글자 제거 · DALL-E 비용 0 · 그리드 통일)

## 구성
- `render.mjs` — `blog-posts.json`을 읽어 **카드 이미지가 없는 글만** HTML→PNG로 렌더(Playwright + Pretendard). 멱등.
- `convert.py` — PNG를 `content/images/`에 `jpg`+`webp`로 변환(Pillow).
- `fonts/Pretendard-*.woff2` — 임베드용 폰트(4 weight). 출처: orioncactus/pretendard v1.3.9.

## 동작(파이프라인)
1. 크론(`api/cron-daily-posts.js`)이 글 발행. `lib/image-generator.js`는 **카드 모드(기본)**로
   DALL-E를 호출하지 않고 `content/images/<postId>-card.jpg` 경로만 지정한다.
2. `.github/workflows/render-blog-cards.yml`가 발행 직후 실행 → 카드 파일이 없는 글을
   `render.mjs`로 렌더하고 `convert.py`로 jpg+webp 변환 후 main에 커밋.
3. 프런트(`index.html` imgToWebp)가 `.webp`(폴백 `.jpg`)로 서빙 → 썸네일·히어로 공용.

## 로컬 실행
```bash
NODE_PATH=/opt/node22/lib/node_modules node render.mjs   # 없는 카드만 렌더 → out/
python3 convert.py out ../../venom-wordpress/preview/content/images
# 전량 재렌더가 필요하면 CARD_FORCE=1
```

## 되돌리기
Vercel 환경변수 `BLOG_IMAGE_MODE=dalle` → 크론이 다시 DALL-E 사진 생성(권장하지 않음).
