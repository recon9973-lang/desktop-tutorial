# GROUND(@ground_geo) 인스타그램 발행 런북

이 문서는 **바로 발행 가능한 상태**로 자산·캡션·발행 절차를 정리한 것입니다.
작업 컨테이너(샌드박스)에서는 `graph.facebook.com`이 프록시에서 차단되고 인스타 토큰이 없어
**실제 API 발행은 이 환경에서 불가능**합니다. 아래 두 경로 중 하나로 Vercel/사용자 측에서 발행하세요.

- 발행 계정: **@ground_geo** (Instagram Business, ID `17841472664941872`)
- 페르소나: **배나미** — 25세, 자연스러운 캔디드 톤, "훅 먼저 → 정보 뒤"
- 그래프 API 버전: `v21.0`

---

## 자산 (공개 URL)

### 이미지 포스팅 3종 (jsDelivr CDN, Graph API `image_url`에 그대로 사용 가능)

| # | 훅 | 공개 이미지 URL |
|---|-----|-----------------|
| 1 | 요즘, 아무도 검색 안 해요 | `https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@2b9583686e9bac72339740fb6e15ad93114fcfe4/persona-nami/ig/post1.png` |
| 2 | 챗GPT한테 우리 브랜드 물어봤더니… | `https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@2b9583686e9bac72339740fb6e15ad93114fcfe4/persona-nami/ig/post2.png` |
| 3 | SEO, 30초컷 요약 | `https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@2b9583686e9bac72339740fb6e15ad93114fcfe4/persona-nami/ig/post3.png` |

### 릴스 1편 (Higgsfield CDN, Reels `video_url`)

- 12초 · 9:16 · 배나미 · 트렌드 영상 모션 카피 · 사무실 캔디드
- `https://d8j0ntlcm91z4.cloudfront.net/user_3DspgcBLnUBmBJ3UNK1kVIJDh1A/hf_20260712_183901_a7d88b2c-7f6e-4e8c-90e1-2843b790c0b5.mp4`
- 원본 job id: `a7d88b2c-7f6e-4e8c-90e1-2843b790c0b5`

> ⚠️ **발행 전 필수 QC**: 릴스·이미지의 인체(손·손가락·목·팔) 구조를 눈으로 확인. 이상 시 재생성.

---

## 캡션

### 포스팅 1 — 요즘, 아무도 검색 안 해요
```
요즘 저희 엄마도 궁금한 거 있으면 초록창 대신 챗지피티한테 물어보시더라고요 😅

검색이 '링크 고르기'에서 '답 하나 받기'로 바뀌는 중이에요. 그래서 이제 마케팅은 '검색 1등'이 아니라 → AI가 콕 집어 골라주는 그 답이 되는 것이 핵심이에요.

이걸 GEO(생성형 엔진 최적화)라고 불러요. 어렵지 않아요, 여기서 하나씩 같이 풀어봐요!

여러분은 요즘 검색, 어디서 하세요? 👇

#GEO #AI검색 #마케팅 #GROUND #검색마케팅 #디지털마케팅
```

### 포스팅 2 — 챗GPT한테 우리 브랜드 물어봤더니…
```
궁금해서 진짜 해봤어요. ChatGPT한테 "○○ 잘하는 곳 추천해줘" 했더니… 우리는 언급도 안 되더라고요 🥲

AI는 '검색 순위'가 아니라 '믿을 만한 정보'를 골라서 인용하거든요. 그래서 요즘 AEO(답변 엔진 최적화)가 중요해졌어요.

오늘은 핵심 3가지만!
1️⃣ 질문–답 형식으로 쓰기
2️⃣ 출처·근거 확실하게
3️⃣ FAQ 구조화(스키마)

내일 하나씩 자세히 올릴게요 📌 궁금한 거 댓글 주세요!

#AEO #챗지피티 #콘텐츠마케팅 #GROUND #검색마케팅 #디지털마케팅
```

### 포스팅 3 — SEO, 30초컷 요약
```
스압 없이 딱 3줄이면 돼요 😎

SEO는 이제 '키워드 많이 넣기'가 아니에요.
① 사람이 진짜 궁금한 걸 → ② 명확하게 답하고 → ③ 검색엔진이랑 AI 둘 다 이해하게 정리하기.

이 셋만 지켜도 절반은 먹고 들어가요.

저장해두고 글 쓸 때 꺼내보세요 🔖

#SEO #검색최적화 #마케팅꿀팁 #GROUND #검색마케팅 #디지털마케팅
```

### 릴스 — 검색이 사라지는 시대, 마케터의 하루
```
검색이 사라지는 시대, 마케터의 하루 🌿

요즘은 사람들이 검색창이 아니라 AI한테 물어봐요. 그래서 저희가 하는 일도 바뀌고 있어요 — '검색 1등 만들기'에서 → 'AI가 골라주는 답이 되기'로.

GROUND는 그 방법(SEO·GEO·AEO)을 하나씩 쉽게 풀어드려요.

팔로우하고 같이 시작해요 👉 @ground_geo

#GEO #AEO #SEO #검색마케팅 #AI마케팅 #GROUND
```

---

## 발행 경로 A — ERP 버튼 (권장)

Vercel에 배포된 ERP는 인스타 토큰(`INSTAGRAM_ACCESS_TOKEN`)과 egress를 갖고 있습니다.

1. ERP → 매거진 큐(MagazineQueue)에서 해당 항목의 **`📷 인스타`** 버튼 클릭
2. 모달에서 위 **공개 이미지 URL**과 **캡션**을 붙여넣기(또는 자동 채움)
3. 발행 → `igMediaId` / `igPermalink` 저장 확인

## 발행 경로 B — 수동 Graph API (이미지 예시)

```bash
IG_ID=17841472664941872
TOKEN=<INSTAGRAM_ACCESS_TOKEN>   # Vercel 환경변수와 동일
IMG='https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@2b9583686e9bac72339740fb6e15ad93114fcfe4/persona-nami/ig/post1.png'

# 1) 컨테이너 생성
CREATION=$(curl -s -X POST "https://graph.facebook.com/v21.0/$IG_ID/media" \
  -d "image_url=$IMG" \
  --data-urlencode "caption=요즘 저희 엄마도 ... #GROUND" \
  -d "access_token=$TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 2) 발행
curl -s -X POST "https://graph.facebook.com/v21.0/$IG_ID/media_publish" \
  -d "creation_id=$CREATION" -d "access_token=$TOKEN"
```

릴스는 `media` 호출 시 `media_type=REELS` + `video_url=<릴스 URL>` 로 바꾸고,
`status_code=FINISHED` 될 때까지 폴링한 뒤 `media_publish` 하면 됩니다.

---

## 권장 발행 순서

1. **릴스** 먼저 (도달률 견인) → 2. 포스팅 1 → 3. 포스팅 2 → 4. 포스팅 3
   (하루 1개씩, GROUND 웹 스케줄 7/13·15·17·20·22 과 리듬 맞춤)
