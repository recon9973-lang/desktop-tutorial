# juso-search-webview

행안부 주소검색 오픈 API(juso.go.kr) 팝업 결과를 받아 Flutter WebView(`james.postMessage`)로
전달하는 최소 브릿지 서버. 아래 두 gist를 원본 그대로 가져와 짝을 맞춰 설치했다.

- [adNodeJs.js](https://gist.github.com/doyle-flutter/30a86e366858e8c5188903b19fe71b88) — 서버
- [adNodeJsHTML.html](https://gist.github.com/doyle-flutter/1c3e9712a60aa84c7e3f39fdb0e249b0) — `ad.html`로 저장(서버가 `./ad.html`을 서빙하므로 파일명을 맞춤)

## 동작 흐름

1. [주소검색 팝업 API](https://business.juso.go.kr/addrlink/openApi/apiExam.do) 결과 폼이
   `POST /` 로 `roadFullAddr` 필드를 제출한다.
2. 서버가 그 값을 쿼리스트링으로 붙여 `GET /com?data=...` 로 리다이렉트한다.
3. `/com`은 `ad.html`을 서빙한다. 이 HTML은 로드 1초 뒤 현재 URL의 쿼리스트링을
   디코딩해 `james.postMessage(...)`로 전달한다 — Flutter `InAppWebView`의
   JavaScript Handler 이름이 `james`일 때 앱 쪽에서 선택된 주소를 받는 구조다.

## 실행

```bash
npm install
npm start        # PORT 환경변수로 포트 지정 가능 (기본 3000)
```

## 검증

`node adNodeJs.js` 로 띄운 뒤 실제 요청으로 확인함:

```
POST / (roadFullAddr=서울특별시 종로구 세종대로 209)
  → 302 Location: /com?data=%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C...

GET /com?data=...
  → ad.html 정상 서빙, james.postMessage 브릿지 코드 포함 확인
```

## 참고

- 원본 gist에는 `package.json`이 없다 — 이 설치에서 `express` 의존성을 명시한
  `package.json`을 새로 추가해 `npm install`만으로 바로 실행되게 했다.
- `james`는 Flutter WebView 쪽에서 등록한 JavaScript 채널 이름이므로, 다른 이름을
  쓰는 앱이라면 `ad.html`의 `james.postMessage` 부분을 그에 맞게 바꿔야 한다.
