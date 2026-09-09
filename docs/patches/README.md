# patches — 다른 저장소에 낼 고침을 담아 두는 자리

작업 방(컨테이너)은 세션마다 초기화된다. `veo-platform` 처럼 **이 방에서 밀 권한이
없는** 저장소의 고침은, 밀기 전에 여기에 패치로 남겨 둔다. 방이 사라져도 일이 안 사라진다.

되살리는 법:

```bash
git -C <veo-platform 클론> checkout -b <가지 이름>
git -C <veo-platform 클론> am < docs/patches/<파일>.patch
```

| 패치 | 대상 | 무엇 |
| --- | --- | --- |
| `2026-09-09-veo-platform-geo-채널표-고침.patch` | `recon9973-lang/veo-platform` | 「어느 AI 가 어느 채널을 보나」 — 미분류를 맨 뒤로 · 미분류 몫이 경쟁사 등록에 안 사라지게 · 분모를 교차표 제 셈으로 (관문 5건) |
