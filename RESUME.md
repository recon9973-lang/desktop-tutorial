# RESUME — 다음 세션 이어가기 (2026-08-30 · s09 화면 이식 2차)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 이번 세션 상세는
> `docs/session-logs/2026-08-30-s09.md`, 현황은 `PROJECT_STATE.md`.

## 지금 상태 — 한눈에

```
veo-platform  main               9fd47e8  판 0.3.391  ← 운영 도달 실측(08-30 20:15 KST)
              anseo-console-port 1bbff54  판 0.3.392~394  ← 묶음 배포 진행(후보 가지 반영)
desktop-tutorial                 이 가지(claude/image-design-workflow-analysis-efuea7)
```

- **라벨 41곳 정리(0.3.390)까지 커밋된 작업은 전부 라이브다.** 운영 서버·워커·웹
  삼중 실측 완료. 남은 미배포물은 «새 화면 시뮬 10종»뿐이고, 그건 코드가 아니라
  설계도라서 **실물 코드로 옮겨야(이식 2차) 화면에 보인다.**
- **배포는 이 방이 직접 한다**(사장님 2026-08-30 «여기방에서» + «모든 권한 승인» —
  2026-08-23 «ANSEO 방 몫» 지시를 대체). 경로: preflight → `deploy-candidate` 커밋 반영
  → GitHub MCP `actions_list`로 CI 초록 → main fast-forward → 바깥 샌드박스 curl로
  운영 실측(`gh`는 이 방에서 토큰 무효, 운영 curl은 프록시 403 — 우회가 정본).

## 🚀 바로 이어갈 작업 — 화면 이식 2차 (⑤부터)

시뮬 10종을 실물 코드로. **화면별 슬라이스 = 한 판**, 매 판 web verify 초록 후 배포.
목록은 `docs/ANSEO-화면-대조표.md` §2, 처방 원문은 각 시뮬 HTML.

```
나감      ① 리포트 세트 v0.3.391(등급 주인공·칩 톤 — 운영 실측 완료)
배포 중   ② 이슈 진행 단계 띠 v0.3.392 · ③ 거래처 목록 축소판 등급+GradeChip v0.3.393 ·
          ④ 대시보드 레일 등급 v0.3.394  (deploy-candidate 1bbff54)
남음      ⑤ 답변 검수 · ⑥ 키워드 · ⑦ 브랜드 식별 · ⑧ 원고 검수 · ⑨ 설정 묶음(6화면 톤 시트) ·
          ⑩ 공개면 · ⑪ 거래처 폼 + 리포트 세트 잔여(목록 등급 칩 열·발행본 목표선)
제외      /console/geo(AEO — 다른 방 재구성 소관) · 감사 #6 눈금 게이지(평균이라 등급 불성립 — 판단 종결)
```

②③④ 배포가 «진행 중»으로 끝났다면: `git ls-remote origin main`이 `1bbff54`인지,
운영 셋이 `0.3.394`인지부터 실측하고 WORKLIST-HISTORY·§2에 결과를 적는다.
참고: 서버 밴드 이름은 명세의 것(준비 완료·양호·취약…) — A+~F 11단으로 바꾸려면
채점 명세 bands 개정이 별도 판으로 필요(발행 불변 주의).

## 사장님 확정 (되묻지 말 것)

- 등급 11단(A+95~F0-49) · **등급 크게 점수 작게** · 톤 4단(90+/75~89기본/60~74/<60) ·
  목표선 취약탈출50·관리목표90 · 그래프는 **곡선·실선**(08-29) · 판 다르면 비교 금지 ·
  못 잰 값 — · 발행 불변 · 의료광고법 준수.
- «토큰 사용량»은 사장님 어휘(08-25) — 교체 금지.
- 라벨 원칙: **사장님이 물어봐야 하는 라벨 = 나쁜 라벨.**
- 세부 감사·깨끗 계열 목록: `docs/ANSEO-톤앤매너-전수감사.md`.

## 주의·제약 (반드시)

- 사장님께 나가는 글은 「커밋」과 「배포」 두 단어만(민다·푸시 금지).
- 판 번호 고르기 전 `git ls-remote`(프록시가 fetch 참조 캐싱 — ls-remote가 정본).
- 관문 무력화 금지 · 계약 재생성(`export_openapi.py` → api-client generate) ·
  비밀키 값·모델 ID를 커밋/PR/코드/문서에 넣지 않는다 · 커밋 트레일러 준수.
- WORKLIST §2는 나간 판을 내리고 실측 문장으로(1,200줄 한도), HISTORY는
  «## 날짜별 기록» 바로 뒤 prepend.
- veo-platform 가지 `claude/anseo-console-port`, desktop-tutorial 은 이 가지 유지.

## 개발 환경 (이 방 재구성)

- PostgreSQL 16: `sudo -u postgres initdb -D /var/lib/postgresql/veo-test` →
  `pg_ctl -o '-p 5432 -k /var/run/postgresql'` → `createdb veo_test`,
  `VEO_TEST_DATABASE_URL='postgresql+psycopg://postgres@/veo_test?host=/var/run/postgresql&port=5432'`.
- `.venv/bin/pip install -e apps/worker`, PATH=/opt/node22/bin,
  PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers.
- ci-local의 mypy 스텁 7건은 환경 문제(수정 전 트리 동일) — 정본 관문은 GitHub CI.

## 대기/차단 (사용자 액션)

- 이월: #36 GSC env 입력 · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.
