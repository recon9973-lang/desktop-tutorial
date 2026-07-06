# VENOM 프로젝트 지침

## 블로그 이미지 생성 규칙 (고정 · MUST)

블로그(정적 글·개념 글)의 이미지는 **반드시** 아래 규칙을 따른다. 이 규칙은 사용자 지시로 고정되었다.

1. **GitHub 저장소 내 관련 사진을 참고(베이스) 이미지로 사용한다.**
   - 소스: `venom-wordpress/preview/images/photos/*`(진료과별 실사진), `venom-wordpress/preview/images/dept/*`(마케팅·의료진 사진).
   - 폴더 사진을 **그대로 쓰지 않는다.** 반드시 AI(image-to-image)로 재가공한다.
2. **인물은 원본을 유지한다.** 얼굴·정체성을 보존한다. **모든 인물은 한국인**이므로 인종·외형을 바꾸지 않는다. 인물을 새로 지어내지 않는다.
3. **움직임·배경·무드만 변형한다.** (모델: `nano_banana_2`, 참고 이미지를 `medias`로 전달)
4. **콘텐츠 내용에 적합한(주제 매칭) 사진을 고른다.** 글 주제와 이미지 내용이 어긋나면 안 된다.
5. **중복 이미지 사용 금지.** 글마다 서로 다른 이미지를 쓴다. (참고: `dept/`에는 파일명만 다른 동일 이미지가 다수 존재 — 예: `online_youtube=channel_mgmt`, `naver_ads=google_ads=shimui`, `online_sns=online_naver`. 실제로 서로 다른 이미지만 골라 쓸 것.)
6. 생성물은 `venom-wordpress/preview/images/blog-ai/<postId>.webp`에 **자체 저장**한다.
7. 프롬프트에 **텍스트·글자·숫자·로고·워터마크 없음**을 명시하고, **의료광고법을 준수**한다(전후사진·효과 보장·최상급 표현 배제).

### 겉·속 통일
- `index.html`의 `_AI_HERO` 맵이 정적 글의 **썸네일(`_postThumbOf`)과 본문 히어로(`openBlogPost`)를 동시에 구동**한다. 따라서 한 이미지로 겉(썸네일)·속(본문)이 자동 통일된다.
- 자동포스트는 크론 생성 이미지(`content/images/`)를 본문·썸네일에 공용으로 사용한다.

### 자체저장 파이프라인 (샌드박스 egress 차단 우회)
작업 컨테이너는 외부 CDN 다운로드가 막혀 있어, 생성 이미지를 저장소로 커밋하려면 GitHub Actions를 쓴다.
1. Higgsfield MCP(`nano_banana_2`)로 참고 이미지를 image-to-image 재가공 → CDN URL 확보.
2. `venom-wordpress/preview/content/blog-ai-manifest.json`(전체) 또는 소형 매니페스트(`blog-ai-manifest-<대상>.json`)에 `{id, out, url}` 기록.
3. `.github/workflows/fetch-blog-ai.yml`을 `workflow_dispatch`(입력 `manifest`)로 실행 → CDN 이미지를 내려받아 webp(폭 1600, q82) 변환 후 `/images/blog-ai/`에 커밋.

## 배포 파이프라인 (사전 승인)
모든 수정은 `implement → 검증(JS 구문 + Playwright) → commit → PR 생성 → 즉시 squash-merge → 브랜치를 origin/main으로 리셋`으로 즉시 반영한다.
- 작업 브랜치: `claude/session-review-prep-an0to9`
- 배포 타깃: venom-new-site.vercel.app (main 자동 배포)
- 커밋 트레일러(필수):
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_019LE9CVMNiehQWEAmqwUtsK
  ```
- 커밋/PR/코드에 모델 ID를 넣지 않는다. 실제 통계·인용을 지어내지 않는다.
