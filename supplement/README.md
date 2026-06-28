# 당신의 영양제 — 랜딩 & 진단 프로토타입

AI 맞춤 영양제 추천 서비스의 웹 디자인 시안입니다. Notion 디자인 시스템 기반의
정적 사이트(HTML/CSS/JS, 빌드 불필요)로 구성되어 있습니다.

## 페이지 구성

| 경로 | 파일 | 설명 |
|------|------|------|
| `/` | `index.html` | 랜딩페이지 (히어로·기능·후기·CTA) |
| `/quiz` | `quiz.html` | 동작하는 진단 퀴즈 (질문 5종 → AI 분석) |
| `/result` | `result.html` | 맞춤 영양제 결과 리포트 |

> `cleanUrls`가 켜져 있어 `.html` 없이 `/quiz`, `/result`로도 접근됩니다.

## 로컬에서 보기

빌드·서버 없이 `index.html`을 브라우저로 바로 열면 됩니다.
진단 시작 → 질문 → 결과까지 클릭으로 전부 동작합니다.

## Vercel 배포 (기존 프로젝트와 분리)

이 폴더는 저장소 루트의 `venom-wordpress` 배포와 **완전히 분리된 별도 Vercel
프로젝트**로 배포합니다. 같은 저장소를 두 개의 프로젝트가 각자 다른 Root
Directory로 바라보는, Vercel 표준 구성입니다.

### 최초 1회 설정 (Vercel 대시보드)

1. Vercel → **Add New… → Project** → 이 GitHub 저장소(`desktop-tutorial`) 선택
2. **Root Directory**를 `supplement` 로 지정 (Edit 버튼 → 폴더 선택)
3. Framework Preset: **Other** (자동 감지됨), Build Command/Output 은 비워둠
4. **Deploy** 클릭

이렇게 하면 `supplement/vercel.json`만 적용되어, 루트 `vercel.json`(venom-wordpress)
설정과 절대 섞이지 않습니다. 이후 `claude/web-design-ai-tools-qp9j46` 브랜치(또는
설정한 프로덕션 브랜치)에 푸시할 때마다 이 프로젝트만 독립적으로 재배포됩니다.

### 적용되는 설정 (`supplement/vercel.json`)

- 정적 배포 (빌드 없음, `outputDirectory: "."`)
- `cleanUrls` — `.html` 확장자 없는 URL
- 보안 헤더 (X-Frame-Options, CSP 관련, HSTS 등)
- `index.html` 캐시 비활성 (항상 최신 시안 노출)
