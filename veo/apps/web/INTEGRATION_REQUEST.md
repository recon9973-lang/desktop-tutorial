# 통합 담당자에게 요청 — 프런트엔드 (인증 · 권한)

작성: 프런트엔드 담당 (`apps/web`, `packages/ui`)

프런트엔드는 워크스페이스 루트 파일(`veo/package.json`, `veo/pnpm-workspace.yaml`,
루트 락파일)의 **내용을 직접 편집하지 않았습니다.** 다만 `apps/web` 에 테스트 도구와
`@veo/shared-types` 의존을 추가했으므로 루트 `pnpm-lock.yaml` 은 `pnpm install` 로
갱신되었습니다.

이전 판에 있던 워크스페이스 경계 파일(`apps/web/pnpm-workspace.yaml` 등) 관련 요청은
모두 해결되었습니다. 루트에서 `pnpm install` · `pnpm -r test` · `pnpm -r typecheck` 가
정상 동작합니다.

---

## 1. ★ 인증 API 계약 — 프런트엔드가 지금 가정하고 있는 것

인증 엔드포인트가 아직 `@veo/api-client` 에 없어서, 프런트엔드는 **`fetch` 로 직접**
호출합니다. 그 가정은 전부 아래 한 파일에만 있습니다.

> **`apps/web/src/lib/auth-api.ts`**

실제 계약이 확정되면 **이 파일 하나만** 고치면 됩니다. 다른 어떤 파일도 요청/응답
모양을 알지 못합니다.

### 가정한 엔드포인트

| 메서드 | 경로 | 요청 | 성공 응답 |
| --- | --- | --- | --- |
| POST | `{base}/api/auth/login` | `{"email","password"}` | `{"data":{"access_token": str, "expires_in": int\|null}}` |
| GET | `{base}/api/auth/me` | `Authorization: Bearer <token>` | `{"data":{"user_id","organization_id","display_name","email","roles":[Role],"permissions":[Permission]}}` |
| POST | `{base}/api/auth/logout` | `Authorization: Bearer <token>` | 2xx |

- 응답 봉투는 기존 API 와 동일하게 `{data, error, meta}` 로 가정했습니다.
- `{base}` 는 `VEO_API_BASE_URL` → 없으면 `NEXT_PUBLIC_VEO_API_BASE_URL` 순으로 읽습니다.
  둘 다 없으면 **로그인은 실패합니다.** localhost 를 추측하지 않습니다.

### 상태 코드 해석

| 상태 | 프런트엔드 처리 |
| --- | --- |
| 400 / 401 / 403 / 404 (login) | 전부 `INVALID_CREDENTIALS` 하나로 뭉갬 |
| 429 | `LOCKED_OUT`, `Retry-After`(초) 사용 |
| 5xx · 파싱 실패 | `SERVER_ERROR` |
| 네트워크 실패 | `UNAVAILABLE` |
| 401/403 (me) | `SESSION_EXPIRED` → 세션 없음으로 처리 |

**중요.** 로그인 실패 시 백엔드가 보낸 `message` 는 화면에 절대 노출하지 않습니다.
`"등록되지 않은 계정입니다"` 같은 문구가 내려와도 버리고 항상
`"이메일 또는 비밀번호가 올바르지 않습니다."` 하나만 보여 줍니다. 계정 존재 여부를
알려 주지 않겠다는 API 의 설계를 UI 가 깨지 않도록 한 것입니다. 이 정책이 바뀌면
알려 주세요.

### 요청 사항

1. 위 경로·필드명이 실제 구현과 다르면 알려 주세요. `auth-api.ts` 상단 주석의 표를
   기준으로 맞추겠습니다.
2. 로그인 실패 시 **백엔드도** 계정 존재 여부를 구분할 수 있는 상태 코드/코드값을
   쓰지 말아 주세요 (예: 없는 계정 404, 틀린 비밀번호 401). 지금은 프런트에서 둘 다
   뭉개고 있지만, 응답 시간 차이까지는 가릴 수 없습니다.
3. 잠금(429)일 때 `Retry-After` 를 초 단위로 주세요.

## 2. ★ `Permission` 을 `@veo/shared-types` 로 내보내 주세요

`Role` 은 생성된 `packages/shared-types/src/enums.ts` 에 있는데 `Permission` 은 없습니다.
그래서 `apps/web/src/lib/permissions.ts` 에 권한 문자열 목록을 **손으로 옮겨** 두었습니다.

- 드리프트 감지는 걸어 두었습니다. `apps/web/src/lib/permissions.test.ts` 가
  `apps/api/src/veo/authz/permissions.py` 를 직접 읽어 `Permission` 열거형과
  목록이 정확히 일치하는지 비교합니다. 어긋나면 테스트가 깨집니다.
- 다만 이건 임시방편입니다. `apps/api/scripts/export_shared_types.py` 의 `EXPORTED`
  목록에 `Permission` 을 추가해 주시면, 프런트엔드는 손으로 옮긴 목록을 지우고
  생성된 타입을 import 하도록 바꾸겠습니다.
- **역할 → 권한 매트릭스는 프런트엔드에 없습니다.** 필요도 없습니다. `/auth/me` 가
  해석된 권한 목록을 주기 때문에 화면은 그 목록만 봅니다.

## 3. 세션 쿠키

- 이름: `veo_console_session` (`apps/web/src/lib/session-cookie.ts` 한 곳에만 있음)
- 속성: `HttpOnly; Secure; SameSite=Lax; Path=/`
  (`Secure` 는 `NODE_ENV=development` 일 때만 뺍니다 — 로컬 http 개발용)
- `Max-Age` 는 로그인 응답의 `expires_in` 을 씁니다. 없으면 8시간.
- 쿠키를 굽고 지우는 곳은 라우트 핸들러 두 개뿐입니다.
  - `apps/web/src/app/api/session/route.ts` (POST · 로그인)
  - `apps/web/src/app/api/session/logout/route.ts` (POST · 로그아웃, 303 리다이렉트)
- 토큰은 브라우저 코드가 절대 만지지 않습니다. `localStorage`·`document.cookie` 사용은
  `apps/web/test/token-never-reaches-the-client.test.ts` 가 소스 전수 검사로 막고 있고,
  빌드 산출물(`.next/static`)도 `apps/web/test/client-bundle.test.ts` 가 검사합니다.

## 4. 리프레시 토큰 · 세션 만료 (미구현 · 결정 필요)

지금은 액세스 토큰 하나만 쿠키에 담습니다. 리프레시 토큰 회전이 계약에 들어가면
`auth-api.ts` 에 `refresh()` 를 추가하고 라우트 핸들러에서 쿠키를 갱신해야 합니다.
**정책이 정해지면 알려 주세요.** 지금은 만료된 토큰이면 `/login` 으로 보냅니다.

## 5. 프록시(구 미들웨어)

`apps/web/src/proxy.ts` 가 `/console/*` 요청에 `x-veo-pathname` 헤더를 붙입니다.
레이아웃이 자기 URL 을 알 수 없어서, 로그인 후 원래 가려던 곳으로 돌려보내려면
이 헤더가 필요합니다. **인증 판정은 하지 않습니다** — 판정은 콘솔 레이아웃의
`requireConsoleSession()` 이 `/auth/me` 로 합니다. 헤더 값은 `safeNextPath()` 로
검증한 뒤에만 리다이렉트에 씁니다 (오픈 리다이렉트 차단).

## 6. CI 연결 요청

`.github/workflows/ci.yml` 에 아직 프런트엔드 잡이 없습니다. 아래가 게이트로 적절합니다.

```bash
pnpm install
pnpm -r test          # @veo/ui 154, @veo/web 166, @veo/api-client 5
pnpm -r typecheck
pnpm --filter @veo/web lint
pnpm --filter @veo/web build
# 번들 검사가 실제로 돌게 하려면 build 뒤에 한 번 더:
pnpm --filter @veo/web test
```

마지막 줄이 필요한 이유: `client-bundle.test.ts` 는 `.next/static` 이 있을 때만
검사를 수행합니다. 빌드 전에는 건너뜁니다.

Node 20 이상. 검증은 Node 26.4.0 / pnpm 10.0.0 에서 수행했습니다.

## 7. 접근성 검사 라이브러리 도입 여부 (판단 요청)

WCAG 2.2 AA 감사 결과는 `apps/web/docs/accessibility.md` 에 있습니다. 명암비·모션·
구조 검사는 전부 손으로 쓴 vitest 스위트로 들어갔고, 새 런타임 의존은 없습니다.

`axe-core` 를 **devDependency 로** 추가하면 구조 규칙(중복 랜드마크, aria 속성 오용,
접근 가능한 이름 누락)을 자동으로 훑을 수 있습니다. 다만 pnpm 에서 `apps/web` 에
의존을 추가하면 루트 `pnpm-lock.yaml` 이 함께 바뀌고, 그 파일은 프런트엔드의 수정
범위 밖이라 **추가하지 않았습니다.**

- 도입을 원하시면 루트에서 `pnpm --filter @veo/web add -D axe-core` 를 실행해 주세요.
  검사 스위트는 프런트엔드가 붙이겠습니다.
- 다만 얻는 것은 구조 규칙뿐입니다. jsdom 은 CSS 를 적용하지 않아 axe 의
  `color-contrast` 규칙이 동작하지 않습니다. 명암비는 이미
  `packages/ui/src/tokens.contrast.test.ts` 가 `tokens.css` 값으로 직접 계산합니다.
- 브라우저에서 도는 검사(Playwright + axe)가 진짜 답이지만, E2E 러너 도입은
  프런트엔드 단독으로 결정할 문제가 아니라고 판단했습니다.

## 8. 기존 계약 참고 (변동 없음)

- 체크 상태는 `PASS | WARNING | FAIL | NOT_APPLICABLE | UNKNOWN` 다섯 가지.
- 점수 응답의 `score` 는 `number | null`. 측정 불가를 `0` 으로 내리지 마세요.
- 점수와 함께 `spec_id`, `spec_version`, `coverage`, `confidence` 가 항상 필요합니다.
- 값의 출처는 `DataSource` + ISO-8601 `collected_at` 쌍으로 주세요.
- GEO 준비도와 AI 가시성 관측은 응답에서도 분리된 필드로 주세요.
