<!-- 가지: claude/serene-dijkstra-7x6zte -->
# RESUME (사진 움직이기 방) — 2026-09-28 · 오더 2건

> 사장님 오더: «사진 한 장으로 움직이는 gif(웹최적화 · webP처럼)를 만들고 자막까지 넣는 프로그램. AI 연동으로 가볍게.»
> 설명서: `venom-wordpress/preview/tools/README-photo-motion.md` · 지도: `핵심두뇌_MASTER.md`(핵심 기능 표).

## ▶ 바로 이어갈 작업
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
