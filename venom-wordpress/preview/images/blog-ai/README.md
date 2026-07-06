# blog-ai — 블로그 AI 이미지 (자체저장)

이 폴더의 이미지는 **고정 규칙**에 따라 생성한다. 전체 규칙은 저장소 루트 `CLAUDE.md` 참고.

핵심 (MUST):
1. GitHub 저장소의 관련 사진(`../photos/*`, `../dept/*`)을 **참고 이미지**로 사용 (그대로 쓰지 말고 AI 재가공).
2. **인물은 원본 유지**(한국인 정체성·얼굴 보존), **움직임·배경·무드만 변형**.
3. **콘텐츠 주제에 맞는** 사진 선택.
4. **중복 이미지 금지** (글마다 다른 이미지).
5. 텍스트·로고·워터마크 없음, 의료광고법 준수.

생성·배포: `nano_banana_2` image-to-image → `content/blog-ai-manifest*.json`에 URL 기록 → `.github/workflows/fetch-blog-ai.yml` 실행으로 `<postId>.webp` 자체저장.

`index.html`의 `_AI_HERO[postId]`가 썸네일·본문 히어로를 동시에 구동 → 겉·속 통일.
