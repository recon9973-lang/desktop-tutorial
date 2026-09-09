# patches — 다른 저장소에 낼 고침을 담아 두는 자리

작업 방(컨테이너)은 세션마다 초기화된다. `veo-platform` 처럼 **이 방에서 밀 권한이
없는** 저장소의 고침은, 밀기 전에 여기에 패치로 남겨 둔다. 방이 사라져도 일이 안 사라진다.

되살리는 법:

```bash
git -C <veo-platform 클론> checkout -b <가지 이름>
git -C <veo-platform 클론> am docs/patches/000*.patch
```

| 패치 | 대상 | 무엇 |
| --- | --- | --- |
| `0001-fix-geo.patch` | `recon9973-lang/veo-platform` | 「어느 AI 가 어느 채널을 보나」 — 미분류를 맨 뒤로 · 미분류 몫이 경쟁사 등록에 안 사라지게 · 분모를 교차표 제 셈으로 (관문 5건) |
| `0002-fix-geo-deploy.patch` | `recon9973-lang/veo-platform` | 기간 탭이 채널 카드도 데려간다 · `claim_version.py` 가 대장 머리말에서 남의 판 번호·지난 기록을 안 건드린다 (관문 2건) |
| `0003-fix-geo-brands.patch` | `recon9973-lang/veo-platform` | 몇 곳에 물었는지 접기 전에 말한다(화면·서버 둘 다) · 임대형 홈페이지를 경로 없이 자사로 선언하는 것을 막는다 (관문 4건) |

**순서대로 적용한다.** 가지 하나에 세 판을 이어 얹은 것이다.

검사는 `veo-platform` 쪽에서 다 돌렸다 — vitest 2,515건 · API 1,572건 · mypy 456파일 ·
ruff · tsc · next build.
