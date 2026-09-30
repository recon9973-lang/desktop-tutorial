<!-- 가지: claude/serene-dijkstra-7x6zte -->
# RESUME (사진 움직이기 방) — 2026-09-28 · 오더 5건

> 사장님 오더: «사진 한 장으로 움직이는 gif(웹최적화 · webP처럼)를 만들고 자막까지 넣는 프로그램. AI 연동으로 가볍게.»
> 설명서: `venom-wordpress/preview/tools/README-photo-motion.md` · 지도: `핵심두뇌_MASTER.md`(핵심 기능 표).

## ▶ 바로 이어갈 작업
0. **(오더 5) 사장님이 Vercel 에 `HIGGSFIELD_API_KEY`(키ID:키비밀, cloud.higgsfield.ai 발급) 를 넣으셨는지 여쭙고**, 넣으셨으면 화면에서 「AI 영상 만들기」를 한 번 눌러 본다.
   API 가 요청 항목(`image_url`/`duration` 등)을 거부하면 화면 오류 문구 그대로 `api/photo-motion-video.js` 의 `hfSubmit` 을 고친다(요청 몸통은 공개 문서 요약으로 만든 것이라 실측 전).
1. 배포된 화면 https://venom-new-site.vercel.app/tools/photo-motion.html 에서 사진 하나 올려 **「AI에게 추천받기」** 를 한 번 눌러 본다.
   - 작업 컨테이너는 외부 통신이 막혀(403) 실제 AI 답은 못 받아 봤다. 서버 키(Vercel `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`)가 있으면 바로 된다.
   - 안 되면 화면 「AI 연결 설정」에 키를 넣어도 된다.
2. 사장님이 원하시면: 베놈 로고 워터마크 넣기, 자막 글꼴 굵기 고르기, 여러 장 한꺼번에 처리 — 아직 안 만들었다.

## 무엇을 만들었나
- `tools/photo-motion.html` — HTML 한 파일. 사진 올리기 → 움직임 9가지 → 자막(여러 줄·차례로·나타나는 방식) → **움직이는 WebP / GIF / MP4·WebM** 내려받기. 외부 라이브러리 0(WebP 애니메이션 상자·GIF 인코더 직접 구현).
- `api/photo-motion-ai.js` — 줄인 사진 한 장을 AI 에 보내 자막 3개·움직임·주인공 위치를 받는다(Anthropic 우선 → OpenAI). 의료광고법 지시 포함. 시간당 30번 제한.
- `vercel.json` 에 함수 등록(30초).

## 확인한 것
헤드리스 크롬으로 실제 파일 생성 → WebP 30장·GIF 30장·MP4 모두 정상으로 읽힘. 서버 API 는 흉내 낸 응답으로 통과(실제 호출은 위 1번).

## 오더 2 (2026-09-28) — «AI 로 원본 인물 그대로 움직이는 영상이 되나 확인»
연결된 영상 AI(Higgsfield MCP)에 사이트 의사 사진(`images/dept/home-doctor.jpg`)을 **첫 장면(start_image)** 으로 고정해 5초를 뽑았다.
| 모델 | 비용(크레딧) | 걸린 시간 | 결과 |
|---|---|---|---|
| MiniMax H3 Max (768p) | 12.5 | 약 30초 | https://d8j0ntlcm91z4.cloudfront.net/user_3DspgcBLnUBmBJ3UNK1kVIJDh1A/hf_20260928_094111_e81b0250-b543-4b6d-9a3c-ad899935667f.mp4 |
| Seedance 2.5 (720p) | 35 | 약 5분 | https://d8j0ntlcm91z4.cloudfront.net/user_3DspgcBLnUBmBJ3UNK1kVIJDh1A/hf_20260928_094106_86be0141-e640-4aee-a0c9-5bafae5d1160.mp4 |
- 첫 장면은 원본 사진 그대로 시작한다(start_image 방식). 이후 장면은 AI 가 그리므로 **얼굴이 얼마나 유지되는지는 사장님이 눈으로 확인**해야 한다 — 작업 컨테이너는 결과 파일을 못 받아 와서 내가 직접 보지 못했다(외부 통신 403).
- 지시문: 「같은 사람, 얼굴·외모 변경 없음, 눈 깜빡임·옅은 미소·살짝 끄덕임·머리카락만, 카메라 살짝 다가감」.
- 다음 할 수 있는 것: `tools/photo-motion.html` 에 「AI 로 진짜 움직이기」 단추 추가(서버 API 가 Higgsfield 를 부르고, 나온 영상을 WebP/GIF 로 바꿔 자막을 얹음). 아직 안 만들었다.

## 오더 3 (2026-09-28) — «12.5 크레딧이 얼마인지 · 카메라 고정 + 인터뷰하듯 말하는 영상»
- 값: 크레딧 충전 1,000 = 49달러(≈ 1 크레딧 4.9센트). 12.5 크레딧 ≈ 0.6달러, 35 ≈ 1.7달러. 500 충전은 26달러(1 크레딧 5.2센트).
- 같은 의사 사진, 카메라 고정, 8초, 인터뷰 답변 장면. 대사(의료광고법 안전): «안녕하세요. 처음 오시는 분들이 제일 많이 물어보시는 게 '아프지 않나요?'예요. 저희는 진료 전에 충분히 설명드리고 시작합니다.»
| 모델 | 비용 | 소리 | 걸린 시간 | 결과 |
|---|---|---|---|---|
| Seedance 2.0 Mini (720p) | 8 | 한국어 목소리 생성 | 약 1분 40초 | https://d8j0ntlcm91z4.cloudfront.net/user_3DspgcBLnUBmBJ3UNK1kVIJDh1A/hf_20260928_143031_2614c157-34f7-4a2b-9fd2-d2ab09ddc452.mp4 |
| MiniMax H3 Max (768p) | 20 | 없음(입만 움직임) | 약 1분 | https://d8j0ntlcm91z4.cloudfront.net/user_3DspgcBLnUBmBJ3UNK1kVIJDh1A/hf_20260928_143039_cea09dff-d0e8-44fa-932d-3520ca858a87.mp4 |
- Seedance 2.5 는 같은 조건에 56 크레딧이라 안 돌렸다. 지금까지 총 75.5 크레딧 사용(≈ 3.7달러), 잔액 924.5.
- 결과 파일은 내가 못 봤다(외부 통신 403). 얼굴 유지·입 모양·목소리는 사장님이 확인.

## 오더 4 (2026-09-28) — «MiniMax 로, 소리 없이, 자막 처리, GIF 처럼 연속 재생, 웹최적화 파일»
- 도구(`tools/photo-motion.html`)에 **영상 올리기** 추가: MP4 → 소리 제거 → 끝↔처음 겹쳐 섞기(이음새 없는 반복) → 자막 차례로 → WebP/GIF/MP4. 헤드리스 크롬으로 확인(23장 WebP).
- **워크플로 `video-to-webp.yml` + `tools/video-to-webp.py`**: 영상 주소 → ffmpeg 로 같은 일을 서버에서 → `images/motion/<이름>.webp` 커밋. (작업 컨테이너는 외부 통신이 막혀 이 길로 실제 파일을 만든다.)
- **확인(실측)**: 워크플로 2번째 실행 성공(1번째는 그 사이 main 이 움직여 push 거부 → `git pull --rebase` 추가). 결과
  `images/motion/doctor-interview.webp` **839KB · 480×360 · 89장 · 7.4초** (+ `doctor-interview.gif` 4.7MB).
  처음·중간·끝 장을 열어 봤다: 같은 의사(얼굴·가운·배경 유지), 입이 말하듯 움직임, 자막 3줄(Pretendard) 차례로 표시. 사이트 주소
  https://venom-new-site.vercel.app/images/motion/doctor-interview.webp
- 앞으로 같은 일: ① 클로드에게 사진+대사 → MiniMax 로 영상(20 크레딧) ② `video-to-webp.yml` Run workflow(주소·이름·자막) 또는 도구에 MP4 올리기.

## 오더 5 (2026-09-29) — «웹사이트에서 바로 AI 말하는 영상 작동하게»
- `api/photo-motion-video.js`: 사진(base64)+대사+길이 → 영상 AI 호출(Higgsfield `api.higgsfield.ai` 우선, 없으면 MiniMax `api.minimax.io`) → 번호 → 상태 조회 → 영상 주소. `?proxy=` 로 영상 파일 중계(CORS 대비). 시간당 12번 제한. `vercel.json` 60초.
- 화면: 사진 올리면 「이 사진으로 AI 말하는 영상 만들기」 상자(서버 키 있을 때만 보임) → 5초마다 상태 확인 → 영상 자동 적재 + 대사→자막.
- 검사: 서버 흉내(mock)로 화면 끝까지 통과(WebP 925KB). **실제 API 는 미실측**(키 없음·외부 통신 차단). 요청 몸통 근거: Higgsfield SDK README(`Authorization: Key ID:SECRET`, `/requests/{id}/status` → `video.url`) + 검색 요약(경로 `/minimax/hailuo-2.3/standard/image-to-video`).
- 사장님이 할 일: cloud.higgsfield.ai 에서 API 키 발급(사용량 과금, 구독 크레딧과 별도) → Vercel → 프로젝트 → Settings → Environment Variables 에 `HIGGSFIELD_API_KEY` = `키ID:키비밀` → Redeploy.
