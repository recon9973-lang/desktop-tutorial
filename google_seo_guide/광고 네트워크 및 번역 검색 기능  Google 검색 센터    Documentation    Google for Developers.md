Google 검색은 사용자가 번역된 콘텐츠에 액세스할 수 있는 [번역 관련 기능](https://developers.google.com/search/docs/appearance/translated-results?hl=ko)을 제공합니다. 광고 네트워크를 운영하는데 광고가 번역된 웹페이지에서 올바르게 작동하지 않는다면 이 가이드의 단계를 따라 광고가 올바르게 렌더링되거나 기여도 분석이 정확하게 이루어지는지 확인해야 합니다.

## Google의 접근방식

사용자가 검색결과 내에서 [Google 번역](https://translate.google.com/about/?hl=ko)을 통해 제공되는 번역된 콘텐츠에 액세스하면 Google에서는 게시자로부터 페이지를 검색하여 소스 URL을 재작성하고 사용자가 번역된 검색결과를 클릭한 후 웹페이지를 번역합니다.

## Google 번역 URL을 원래 URL로 변환

게시자의 소스 URL에 의존하는 광고 네트워크를 운영하는 경우 Google 번역 URL을 변환하여 광고가 올바르게 작동하는지 확인해야 합니다. 다음 단계를 따라 게시자의 호스트 이름을 디코딩합니다.

1.  `.translate.goog` 접미사를 삭제하여 호스트 이름에서 도메인 접두사를 추출합니다.
2.  `_x_tr_enc` 매개변수를 `,`(쉼표) 문자로 분할하고 `encoding_list`로 저장합니다.
3.  `_x_tr_hp` 매개변수 값이 있으면 도메인 접두사 앞에 추가합니다.
4.  `encoding_list`에 `1`이 포함되어 있고 출력이 `1-`로 시작하면 2단계 출력에서 `1-` 접두사를 삭제합니다.
5.  `encoding_list`에 `0`이 포함되어 있고 출력이 `0-`로 시작하면 3단계 출력에서 `0-` 접두사를 삭제합니다. 접두사를 삭제한 경우 `is_idn`을 `true`로 설정합니다. 그 외의 경우에는 `is_idn`을 `false`로 설정합니다.
6.  `/\b-\b/`(정규식)를 `.`(점) 문자로 바꿉니다.
7.  `--`(이중 하이픈) 문자를 `-`(하이픈) 문자로 바꿉니다.
8.  `is_idn`이 `true`로 설정되어 있으면 punycode 접두사 `xn--`을 추가합니다.
9.  **선택사항**: 유니코드로 변환합니다.

### Google 번역 URL에서 호스트 이름을 디코딩하는 자바스크립트 코드 샘플

```csharp
function decodeHostname(proxyUrl) {
  const parsedProxyUrl = new URL(proxyUrl);
  const fullHost = parsedProxyUrl.hostname;
  // 1. Extract the domain prefix from the hostname, by removing the
        ".translate.goog" suffix
  let domainPrefix = fullHost.substring(0, fullHost.indexOf('.'));

  // 2. Split _x_tr_enc parameter by "," (comma), save as encodingList
  const encodingList = parsedProxyUrl.searchParams.has('_x_tr_enc') ?
      parsedProxyUrl.searchParams.get('_x_tr_enc').split(',') :
      [];

  // 3. Prepend value of _x_tr_hp parameter to the domain prefix, if it exists
  if (parsedProxyUrl.searchParams.has('_x_tr_hp')) {
    domainPrefix = parsedProxyUrl.searchParams.get('_x_tr_hp') + domainPrefix;
  }

  // 4. Remove '1-' prefix from the output of step 2 if encodingList contains
  //    '1' and the output begins with '1-'.
  if (encodingList.includes('1') && domainPrefix.startsWith('1-')) {
    domainPrefix = domainPrefix.substring(2);
  }

  // 5. Remove '0-' prefix from the output of step 3 if encodingList contains
  //    '0' and the output begins with '0-'.
  //    Set isIdn to true if removed, false otherwise.
  let isIdn = false;
  if (encodingList.includes('0') && domainPrefix.startsWith('0-')) {
    isIdn = true;
    domainPrefix = domainPrefix.substring(2);
  }

  // 6. Replace /\b-\b/ (regex) with '.' (dot) character.
  // 7. Replace '--' (double hyphen) with '-' (hyphen).
  let decodedSegment =
      domainPrefix.replaceAll(/\b-\b/g, '.').replaceAll('--', '-');

  // 8. If isIdn equals true, add the punycode prefix 'xn--'.
  if (isIdn) {
    decodedSegment = 'xn--' + decodedSegment;
  }
  return decodedSegment;
}
```

## URL 재구성

1.  원본 페이지 URL을 사용하여 호스트 이름을 디코딩된 호스트 이름으로 바꿉니다.
2.  모든 `_x_tr_*` 매개변수를 삭제합니다.

## 코드 테스트

다음 표를 사용하여 코드의 단위 테스트를 만들 수 있습니다. `proxyUrl`이 주어지면 `decodeHostname`은 예상 값과 일치해야 합니다.

다음 표는 호스트 이름 디코딩 테스트에만 사용할 수 있습니다. URL의 경로, 프래그먼트, 원래 매개변수가 그대로 유지되는지 확인해야 합니다.

| `proxyUrl` | `decodeHostname` |
|------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `https://example-com.translate.goog` | `example.com` |
| `https://foo-example-com.translate.goog` | `foo.example.com` |
| `https://foo--example-com.translate.goog` | `foo-example.com` |
| `https://0-57hw060o-com.translate.goog/?_x_tr_enc=0` | `xn--57hw060o.com (⚡😊.com)` |
| `https://1-en--us-example-com/?_x_tr_enc=1` | `en-us.example.com` |
| `https://0-en----w45as309w-com.translate.goog/?_x_tr_enc=0` | `xn--en--w45as309w.com (en-⚡😊.com)` |
| `https://1-0-----16pw588q-com.translate.goog/?_x_tr_enc=0,1` | `xn----16pw588q.com (⚡-😊.com)` |
| `https://lanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch-co-uk.translate.goog/?_x_tr_hp=l` | `llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch.co.uk` |
| `https://lanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch-co-uk.translate.goog/?_x_tr_hp=www-l` | `www.llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch.co.uk` |
| `https://a--aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-com.translate.goog/?_x_tr_hp=a--xn--xn--xn--xn--xn--------------------------a` | `a-xn-xn-xn-xn-xn-------------aa-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.com` |
| `https://g5h3969ntadg44juhyah3c9aza87iiar4i410avdl8d3f1fuq3nz05dg5b-com.translate.goog/?_x_tr_enc=0&_x_tr_hp=0-` | `xn--g5h3969ntadg44juhyah3c9aza87iiar4i410avdl8d3f1fuq3nz05dg5b.com (💖🌲😊💞🤷♂️💗🌹😍🌸🌺😂😩😉😒😘💕🐶🐱🐭🐹🐰🐻🦊🐇😺.com)` |