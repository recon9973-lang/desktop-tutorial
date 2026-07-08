## 검색결과에서 사이트에 호스팅된 이미지 삭제하기

## 긴급 이미지 삭제

사이트에 호스팅된 이미지를 Google 검색결과에서 빠르게 삭제하려면 [삭제 도구](https://support.google.com/webmasters/answer/9689846?hl=ko#zippy=,image-url)를 사용하세요. [긴급하지 않은 이미지 삭제 섹션](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko#non-emergency-image-removal)에 설명된 대로 사이트에서 이미지를 삭제하거나 이미지를 차단하지 않는 한 삭제 요청이 만료되면 이미지가 Google 검색결과에 다시 표시될 수 있습니다.

## 긴급하지 않은 이미지 삭제

다음 두 가지 방법으로 Google 검색결과에서 사이트의 이미지를 삭제할 수 있습니다.

-   [robots.txt 허용 안함 규칙](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko#robotstxt)
-   [`noindex` `X-Robots-Tag` HTTP 헤더.](https://developers.google.com/search/docs/crawling-indexing/prevent-images-on-your-page?hl=ko#noindex)

두 방법의 효과는 동일하며 사이트에 더 편리한 방법을 선택하면 됩니다. Googlebot은 HTTP 헤더를 추출하기 위해 URL을 크롤링해야 하므로 두 방법을 동시에 구현하는 것은 적절하지 않습니다.

이미지를 호스팅하는 사이트(예: CDN)에 대한 액세스 권한이 없거나 CMS에서 `noindex` `X-Robots-Tag` HTTP 헤더 또는 robots.txt로 이미지를 차단하는 방법을 제공하지 않는 경우 사이트에서 이미지를 완전히 삭제해야 할 수도 있습니다.

### robots.txt 규칙을 사용하여 이미지 삭제

사이트의 이미지가 Google 검색결과에 표시되지 않게 하려면 이미지를 호스팅하는 사이트의 루트(예: `https://yoursite.example.com/robots.txt`)에 [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=ko) 파일을 추가하세요. robots.txt 규칙을 사용하여 Google 검색결과에서 이미지를 삭제하면 삭제 도구를 사용하는 것보다 시간이 오래 걸리지만 와일드 카드를 사용하거나 하위 경로를 차단하여 보다 유연하게 제어할 수 있습니다. 또한 삭제 도구는 Google에만 적용되지만 이 방법은 모든 검색엔진에 적용됩니다.

예를 들어 Google이 사이트에 있는 `dogs.jpg` 이미지를 `yoursite.example.com/images/dogs.jpg`에서 제외하기를 원한다면 robots.txt 파일에 다음을 추가합니다.

```makefile
User-agent: Googlebot-Image
Disallow: /images/dogs.jpg
```

다음번에 Google에서 사용자의 `dogs.jpg` 이미지를 크롤링할 때 이 규칙을 발견하고 이미지를 검색결과에 표시하지 않습니다.

규칙에는 더 유연하게 제어할 수 있도록 [특수문자](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt?hl=ko#url-matching-based-on-path-values)가 포함될 수 있습니다. 특히 `*` 문자는 모든 문자 시퀀스와 일치하므로 하나의 규칙과 여러 이미지 경로를 일치시킬 수 있습니다.

Google 색인에서 사이트에 있는 여러 이미지를 삭제하려면 각 이미지별로 `disallow` 규칙을 추가하고 만약 이미지가 파일명의 접미사와 같은 공통된 패턴을 공유하고 있다면 파일 이름에 `*` 문자를 사용합니다. 예:

```makefile
User-agent: Googlebot-Image
# Repeated 'disallow' rules for each image:
Disallow: /images/dogs.jpg
Disallow: /images/cats.jpg
Disallow: /images/llamas.jpg

# Wildcard character in the filename for
# images that share a common suffix. For example,
#   animal-picture-UNICORN.jpg and
#   animal-picture-SQUIRREL.jpg
# in the "images" directory
# will be matched by this pattern.
Disallow: /images/animal-picture-*.jpg
```

Google 색인에서 사이트에 있는 이미지를 모두 삭제하려면 robots.txt 파일에 다음 규칙을 추가합니다.

```makefile
User-agent: Googlebot-Image
Disallow: /
```

`.gif` 이미지는 모두 제외하고 `.jpg` 이미지만 포함하는 등 특정 형식의 파일을 모두 삭제하려면 다음 robots.txt 항목을 사용합니다.

```makefile
User-agent: Googlebot-Image
Disallow: /*.gif$
```

`Googlebot-Image`를 `User-agent`로 지정하면 이미지가 Google 이미지에서 제외됩니다. Google 검색 및 Google 이미지를 포함한 모든 Google 검색에서 이미지를 제외하려면 `Googlebot` 사용자 에이전트를 지정합니다.

### `noindex` `X-Robots-Tag` HTTP 헤더로 이미지 삭제

삭제하려는 리소스의 HTTP 응답 헤더에 `noindex` `X-Robots-Tag`를 추가하여 Google 검색결과에서 사이트에 호스팅된 이미지를 삭제할 수도 있습니다. 이 경우에는 Googlebot이 `noindex` 규칙을 추출할 수 있도록 이미지 URL 크롤링을 허용해야 합니다. `noindex` `X-Robots-Tag` HTTP 응답 헤더를 구현하려면 [`noindex`에 관한 문서를 따르세요](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=ko#xrobotstag-implementation).

특정 페이지에 `noimageindex` 로봇 태그를 추가하면 해당 페이지에 삽입된 이미지의 색인이 생성되지 않습니다. 그러나 동일한 이미지가 다른 페이지에도 표시되는 경우 해당 페이지에서 색인이 생성될 수 있습니다. 이미지가 표시되는 위치와 관계없이 특정 이미지를 차단하려면 `noindex` `X-Robots-Tag` HTTP 응답 헤더를 사용합니다.

## 내가 소유하지 않은 사이트에서 이미지를 삭제하려면 어떻게 해야 하나요?

[검색결과에서 이미지를 삭제하는 방법에 대한 Google 검색 도움말](https://support.google.com/websearch/answer/4628134?hl=ko)을 참고하세요.