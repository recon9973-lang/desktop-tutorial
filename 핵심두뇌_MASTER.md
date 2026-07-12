# 🧠 VENOM 핵심 두뇌 — 전체 지도 (MASTER)

> **"매번 어디 있는지 못 찾는 일"을 끝내는 단일 인덱스.** 뭔가 찾을 땐 여기부터.
> 계정: GitHub `recon9973-lang`(recon9973@gmail.com) · 운영 `76cold@gmail.com`
> 최종 갱신: 2026-07-12

---

## 🔎 빠른 찾기 (제일 많이 헷갈리는 것)
| 찾는 것 | 위치 |
|---|---|
| **베놈 사이트 코드** | `desktop-tutorial` 저장소 → `venom-wordpress/preview/` |
| **베놈 사이트 주소(배포)** | https://venom-new-site.vercel.app (Vercel 프로젝트명은 `desktop-tutorial`) |
| **ERP 코드** | `marketing-agency-erp` 저장소 (브랜치 `erp-v1`=라이브) |
| **이미지 제작 툴** | `marketing-agency-erp` → `/image-studio`, `/manuscript`, `src/components/ai/` |
| **SEO 진단기(엔진)** | `desktop-tutorial` → `venom-wordpress/preview/seo/` |
| **Google 203문서(지식맵)** | `desktop-tutorial` → `google_seo_guide/` (인덱스 `00_지식맵_MASTER_INDEX.md`) |
| **AI 노출 매트릭스(유료)** | `desktop-tutorial` → `venom-wordpress/preview/api/insights.js` |
| **비밀키(API키 등)** | 코드에 없음 → **Vercel 각 프로젝트 Settings → Environment Variables** |

---

## 📦 저장소 (GitHub `recon9973-lang`)
| 저장소 | 용도 | 공개 | 배포 |
|---|---|---|---|
| **desktop-tutorial** | 베놈 마케팅 사이트 + SEO 진단기 + 203문서 + 클리닉 진단 | Public | → venom-new-site.vercel.app (main 자동) |
| **marketing-agency-erp** | 마케팅대행 ERP(Next.js) — 거래처·계약·업무·정산·이미지/마케팅 스튜디오 | Public ⚠️ | → Vercel (erp-v1 자동) |
| Design-resources-repository | 디자인 리소스 | Public | — |
| seo-generator | SEO 생성기 | Public | — |
| wp-seo-writer | WordPress SEO 글쓰기 | Private | — |
| seo-writing-skill | SEO 글쓰기 스킬 | Private | — |
| your-supplement | 영양제 프로젝트 | Public | — |
| webp | 이미지 webp 변환 | Public | — |

> ⚠️ ERP가 Public입니다 — 업무시스템이라 **Private 권장**(Settings→General→Change visibility).

---

## ☁️ 배포 (Vercel) — 팀 `76cold-2381's projects`
| Vercel 프로젝트 | 저장소 | 주소 | 비고 |
|---|---|---|---|
| `desktop-tutorial` | desktop-tutorial | **venom-new-site.vercel.app** | 베놈 사이트 |
| `marketing-agency-erp` | marketing-agency-erp | (ERP 도메인) | ERP · Project ID `prj_6klGpQjt0QefuWFUE7ja4uqYXqZl` |

- **Vercel 팀 ID**: `team_RAEuNMET1CBjaKNLQvukzpRS` (비밀 아님 — API용)
- **GitHub 저장소명 ≠ 배포 주소**: "venom-new-site"는 주소일 뿐, 저장소는 `desktop-tutorial`.

---

## 🛠️ 핵심 기능 — 어디에 있나
### 베놈 사이트 (`desktop-tutorial/venom-wordpress/preview/`)
| 기능 | 위치 | 유료? |
|---|---|---|
| SEO 진단기(룰 엔진) | `seo/seo-engine.js` + `seo/seo-rules.json` + `seo/README.md` | 무료 |
| SEO 지식근거(203문서) | `../../google_seo_guide/` | — |
| AI 노출 매트릭스(AEO) | `api/insights.js` (Perplexity·Claude·Gemini·GPT) | **유료(토큰)** |
| AI 챗봇(의료광고법) | `api/chatbot.js` (Claude+GPT) + `chatbot/` | **유료(토큰)** |
| 키워드/속도/엔티티 체크 | `api/seo-proxy.js` (네이버·구글 무료API) | 무료 |
| 자동 블로그 글생성 | `api/generate-post.js`, `api/cron-daily-posts.js` | **유료(토큰)** |
| 클리닉 진단(medirank) | `clinic/pipeline/`, `clinic/self-check/` | 무료 |
| 관리자 화면 | `admin.html` / 클리닉 `clinic/admin/` | — |

### ERP (`marketing-agency-erp/src/`)
| 기능 | 위치 |
|---|---|
| 이미지 스튜디오 + 카드뉴스 | `app/(erp)/image-studio/`, `components/ai/ImageStudio.tsx`, `CardNewsMaker.tsx` |
| 원고 스튜디오 | `app/(erp)/manuscript/` → `public/studio.html`, `app/api/generate-image/` |
| 마케팅 엔진(VME) | `app/(erp)/marketing-studio/`, `server/marketing/` (canva·higgsfield·naver·wordpress) |
| AI 마케팅/회의록/검색량/토스결제 | `ai-studio`, `meetings`, `keywords`, `pay` |
| 인증(로그인) | `server/auth.ts` — 이메일+비밀번호(+매직링크) |

---

## 🌿 브랜치·배포 규칙
- **desktop-tutorial**: `main`이 라이브(자동배포). 작업은 `claude/*` 브랜치 → PR → main 병합.
- **marketing-agency-erp**: `erp-v1`이 라이브(자동배포). 빌드 시 Neon DB에 `prisma db push`.

## 🔐 비밀키(secrets)는 어디에 (값은 여기 없음)
- **Vercel** 각 프로젝트 → Settings → Environment Variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`, `NAVER_*`, ERP의 `DATABASE_URL`·`AUTH_SECRET`·`EMAIL_SERVER` 등)
- **GitHub Actions** secrets (워크플로용)
- **로컬** `.env.local` (git 제외)
- ⚠️ 비밀키 값은 **코드/이 문서에 절대 넣지 않음**.

---

## 📌 원칙 (혼란 방지)
1. **한 프로젝트 = 한 저장소.** 같은 걸 두 저장소에서 만들지 말 것(갈라지면 지옥).
2. 두 곳에서 작업 시: **작업 전 pull → 작업 → push**. 같은 파일 동시 편집 금지.
3. "어디 있지?" 싶으면 → **이 문서(핵심두뇌_MASTER.md) 부터.**
