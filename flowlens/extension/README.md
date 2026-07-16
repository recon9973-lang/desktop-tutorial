# FlowLens 히트맵 오버레이 (크롬 확장 프로토타입)

실제 웹페이지 위에 FlowLens 클릭 히트맵을 겹쳐 보는 **대행사·운영자용 QA 뷰어**입니다.

> ⚠️ 이 확장은 **데이터를 수집하지 않습니다.** 방문자 행동 수집은 추적 스크립트(`t.js`)가 담당합니다.
> 확장은 "설치한 사람의 브라우저"에서만 동작하므로 방문자 추적 용도로는 쓸 수 없고,
> 이미 수집된 히트맵을 실제 화면 위에 얹어 **검토(QA)** 하는 용도입니다.

## 설치 (개발자 모드)
1. 크롬 → `chrome://extensions` → 우측 상단 **개발자 모드** 켜기
2. **압축해제된 확장 프로그램을 로드** → 이 `extension/` 폴더 선택
3. 툴바의 FlowLens 아이콘 클릭 → **FlowLens 주소**(예: `https://app.seokorea.org`)와 **사이트 키** 입력 → "히트맵 켜기"

## 동작
- 팝업이 현재 탭에 `content.js`를 주입 → `GET {origin}/api/overlay?site=…&path=…` 호출
- 응답(클릭 좌표 0~1 상대값)을 현재 페이지 문서 크기에 맞춰 캔버스 열지도로 오버레이
- 다시 누르면 오버레이 제거

## 서버 측
- 오버레이 좌표 API: `flowlens/src/app/api/overlay/route.ts` (siteKey로 조회, 좌표만 반환, CORS 허용, 개인정보 없음)

## 기능
- **클릭 히트맵** / **스크롤맵**(도달 밴드 + Average Fold 라인) 전환
- **기간 필터**: 전체 / 최근 7일 / 최근 30일
- 설정은 저장되어 다음에 그대로 사용

## 웹스토어 배포 패키징
1. 아이콘: `icon.svg`를 128/48/16px **PNG로 변환**해 `icons/` 에 넣고 `manifest.json`에 `"icons"`·`"action.default_icon"` 추가 (스토어 제출 시 PNG 필수)
2. 압축: 프로젝트 루트에서 `npm run ext:zip` → `flowlens-extension.zip` 생성
3. [크롬 웹스토어 개발자 대시보드](https://chrome.google.com/webstore/devconsole)에 zip 업로드 + 개인정보 처리방침 URL + 권한 사유 기재
4. **권장**: `host_permissions`를 `<all_urls>` 대신 실제 서비스 도메인으로 좁히기

## 다음
- 셀렉터 랭킹 오버레이, 디바이스 필터, 특정 요소 클릭 수 팝오버.
