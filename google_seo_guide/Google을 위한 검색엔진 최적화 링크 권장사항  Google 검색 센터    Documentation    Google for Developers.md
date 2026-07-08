Google에서는 링크를 신호로 사용해 페이지의 관련성을 파악하고 크롤링할 새 페이지를 찾습니다. Google에서 페이지의 링크를 통해 사이트에 있는 다른 페이지를 찾을 수 있도록 링크를 크롤링 가능하게 만드는 방법과 앵커 텍스트를 개선하여 사용자와 Google이 페이지를 더 쉽게 이해할 수 있도록 하는 방법에 관해 알아보세요.

## 링크를 크롤링 가능하게 설정하기

일반적으로 Google에서는 링크가 `href` 속성이 있는 `<a>` HTML 요소(_앵커 요소_라고도 함)인 경우에만 링크를 크롤링할 수 있습니다. 다른 형식의 링크는 Google 크롤러가 파싱하거나 추출할 수 없는 경우가 대부분입니다. Google에서는 `href` 속성이 없는 `<a>` 요소나 스크립트 이벤트로 인해 링크처럼 작동하는 다른 태그에서 안정적으로 URL을 추출해 낼 수 없습니다. 다음은 Google이 파싱할 수 있는 링크와 파싱할 수 없는 링크의 예입니다.

**권장(Google에서 파싱할 수 있음)**

```php-template
<a href="https://example.com">
```

```php-template
<a href="/products/category/shoes">
```

```php-template
<a href="./products/category/shoes">
```

```php-template
<a href="/products/category/shoes" onclick="javascript:goTo('shoes')">
```

```cpp
<a href="/products/category/shoes" class="pretty">
```

**권장하지 않음(하지만 Google에서 파싱을 시도할 수는 있음):**

```php-template
<a routerLink="products/category">
```

```php-template
<span href="https://example.com">
```

```php-template
<a onclick="goto('https://example.com')">
```

`<a>` 요소의 URL이 Google 크롤러가 요청을 전송할 수 있는 실제 웹 주소(URI와 유사함)로 변환되는지 확인합니다.

**권장(Google에서 해결할 수 있음):**

```php-template
<a href="https://example.com/stuff">
```

```php-template
<a href="/products">
```

```php-template
<a href="/products.php?id=123">
```

**권장하지 않음(하지만 Google에서 문제를 해결하기 위해 계속 시도할 수 있음):**

```php-template
<a href="javascript:goTo('products')">
```

```php-template
<a href="javascript:window.location.href='/products'">
```

## 앵커 텍스트 배치

_앵커 텍스트_(_링크 텍스트_라고도 함)는 링크에 표시되는 텍스트입니다. 이 텍스트는 사용자와 Google에 지금 들어가려는 페이지가 어떤 페이지인지 알려줍니다. [Google에서 크롤링할 수 있는 `<a>` 요소](https://developers.google.com/search/docs/crawling-indexing/links-crawlable?hl=ko#crawlable-links) 사이에 앵커 텍스트를 배치하세요.

**맞는 예:**

> <a href="https://example.com/ghost-peppers">**고스트 페퍼**</a>

**나쁜 예(빈 링크 텍스트):**

> <a href="https://example.com"></a>

`<a>` 요소가 어떤 이유로 비어 있다면 Google에서 대신 `title` 속성을 앵커 텍스트로 사용할 수 있습니다.

> <a href="https://example.com/ghost-pepper-recipe" title="**고스트 페퍼 피클 만드는 법**"></a>

이미지를 링크로 사용할 때 Google에서는 `img` 요소의 `alt` 속성을 앵커 텍스트로 사용하므로 [이미지를 설명하는 대체 텍스트를 추가](https://developers.google.com/search/docs/appearance/google-images?hl=ko#descriptive-alt-text)해야 합니다.

**맞는 예:**

> <a href="/add-to-cart.html"><img src="enchiladas-in-shopping-cart.jpg" alt="**장바구니에 엔칠라다 추가**"/></a>

**나쁨(빈 대체 텍스트와 빈 링크 텍스트):**

> <a href="/add-to-cart.html"><img src="enchiladas-in-shopping-cart.jpg" alt=""/></a>

자바스크립트를 사용하여 앵커 텍스트를 삽입하는 경우 [URL 검사 도구](https://support.google.com/webmasters/answer/9012289?hl=ko)를 사용하여 앵커 텍스트가 렌더링된 HTML에 있는지 확인하세요.

## 좋은 앵커 텍스트 작성하기

좋은 앵커 텍스트는 구체적이고 간결해야 하며 앵커 페이지가 표시되는 페이지 및 연결되는 페이지와 관련이 있어야 합니다. 좋은 앵커 텍스트는 링크에 맥락을 제공하고 독자의 기대치를 설정합니다. 앵커 텍스트가 좋을수록 사용자가 탐색하기 쉬우며 링크를 통해 연결되는 페이지를 Google이 더 잘 이해할 수 있습니다.

**나쁨(너무 일반적임):**

> <a href="https://example.com">**여기를 클릭**</a>하여 자세히 알아보세요.

> <a href="https://example.com">**자세히 알아보세요**</a>.

> <a href="https://example.com">**웹사이트**</a>에서 당사 치즈에 대해 자세히 알아보세요.

> 치즈 제조 방법에 대한 자세한 배경 정보를 제공하는 <a href="https://example.com">**도움말**</a>을 참고하세요.

**더 좋음(추가 설명을 제공함):**

> 구매할 수 있는 치즈의 전체 목록을 확인하려면 <a href="https://example.com">**치즈 유형 목록**</a>을 참고하세요.

**바람직하지 않음(지나치게 긺):**

> 다음 주 화요일부터 <a href="https://example.com">**Knitted Cow는 위스콘신 주민들을 재개장 행사에 초대합니다. 또한 소 모양의 얼음 조각을**</a> 선착순 20명에게 무료로 제공합니다.

**더 좋음(간결함):**

> 다음 주 화요일부터 <a href="https://example.com">**Knitted Cow는 위스콘신 주민들을 재개장 행사에 초대**</a>합니다. 또한 소 모양의 얼음 조각을 선착순 20명에게 무료로 제공합니다.

앵커 텍스트는 최대한 자연스럽게 작성하세요. 링크하려는 페이지와 관련된 모든 키워드를 전부 다 집어넣어서는 안 됩니다. [유인 키워드 반복](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko#keyword-stuffing)은 스팸 정책에 위배된다는 점을 기억하세요. 이 키워드가 다음에 표시될 페이지를 이해하는 데 필요한지 생각해 보세요. 앵커 텍스트에 키워드를 무리하게 집어 넣고 있다는 느낌이 든다면 이미 바람직하지 않은 상태일 수 있습니다.

링크에 컨텍스트를 제공하는 것도 잊지 마세요. 링크 앞뒤에 있는 단어도 중요합니다. 전체 문장을 잘 살펴보세요. 여러 개의 링크를 연달아 배치하지 마세요. 독자가 링크를 구분하기 어려워지고 각 링크의 주변 텍스트가 사라집니다.

**나쁨(링크가 너무 많음):**

> 저는 올해 치즈에 <a href="https://example.com/page1">**관해**</a> <a href="https://example.com/page2">**여러**</a> <a href="https://example.com/page3">**번**</a> <a href="https://example.com/page4">**글을**</a> <a href="https://example.com/page5">**썼습니다**</a>.

**더 좋음(컨텍스트에 따라 링크를 띄어씀)**

> 저는 올해 치즈에 관해 여러 번 글을 썼습니다. <a href="https://example.com/blue-cheese-vs-gorgonzola">**블루 치즈와 고르곤졸라에 대한 논란**</a>을 잊을 수 있는 사람이 있을까요. <a href="https://example.com/worlds-oldest-brie">**세계에서 가장 오래된 브리**</a>로 Cheesiest Research 메달을 수상하기도 했고요. 장엄한 스토리, <a href="https://example.com/the-lost-cheese">**The Lost Cheese**</a>를 저 나름대로 다시 풀어놓기도 했고, 제가 개인적으로 가장 좋아하는 <a href="https://example.com/boy-and-his-cheese">**A Boy and His Cheese: a story of two unlikely friends**</a>라는 작품도 있었습니다.

## 내부 링크: 자체 콘텐츠 교차 참조

<iframe frameborder="0" allowfullscreen="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" width="640" height="360" src="https://www.youtube.com/embed/vc3uGc6TSH0?origin=https%3A%2F%2Fdevelopers.google.com&amp;autoplay&amp;controls&amp;embed_domain&amp;enablejsapi=1&amp;end&amp;hl&amp;showinfo&amp;start&amp;video-id=vc3uGc6TSH0&amp;widgetid=31&amp;forigin=https%3A%2F%2Fdevelopers.google.com%2Fsearch%2Fdocs%2Fcrawling-indexing%2Flinks-crawlable%3Fhl%3Dko&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fwww.google.com%2F&amp;vf=1" id="widget32" data-gtm-yt-inspected-225073684_46="true" data-gtm-yt-inspected-183356566_95="true" data-gtm-yt-inspected-26="true" data-gtm-yt-inspected-45="true" data-gtm-yt-inspected-52="true" data-title="YouTube video player" title="How to use internal linking for SEO"></iframe>

링크는 일반적으로 외부 웹사이트로의 연결하는 의미에서 생각하기 쉽지만 내부 링크에 사용되는 앵커 텍스트를 주의 깊게 살펴보면 사용자와 Google이 사이트를 더욱 쉽게 이해하고 사이트의 다른 페이지를 찾는 데 도움을 줄 수 있습니다. 중요한 페이지마다 사이트에 있는 다른 페이지 중 하나 이상의 링크가 있어야 합니다. 독자가 사이트의 특정 페이지를 이해할 때 사이트의 다른 리소스 중 어떤 리소스가 도움이 될지 생각해 보고 컨텍스트에 따라 해당 페이지로 연결되는 링크를 제공하세요.

## 외부 링크: 다른 사이트로 연결되는 링크

다른 사이트에 연결하는 일을 겁내지 마세요. 출처를 인용하는 등 외부 링크를 사용하면 신뢰성을 구축하는 데 도움이 될 수 있습니다. 적절한 경우라면 외부 사이트에 연결하고 독자에게 기대할 수 있는 내용에 관한 컨텍스트를 제공하세요.

**좋음(출처 인용)**:

> 최근 스위스 연구에 따르면 음악에 노출한 에멘탈 치즈는 음악에 노출하지 않은 치즈와 비교했을 때 더욱 부드러운 맛을 냈습니다. <a href="https://example.com">**Cheese in Surround Sound - 음식 실험**</a>에서 전체 결과를 확인하세요.

[`nofollow`](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko#nofollow)는 출처를 신뢰할 수 없을 때만 사용하세요. 사이트에 있는 모든 외부 링크에 사용해서는 안 됩니다. 예를 들어 치즈 애호가인데 누군가가 내가 좋아하는 치즈에 관해 나쁘게 이야기하는 글을 게시했다고 생각해 봅시다. 그래서 이 글에 반박하는 글을 쓰고 싶지만 링크를 걸어 내 사이트가 갖고 있는 명성을 해당 사이트에 나눠 주고 싶지는 않습니다. 이런 경우 `nofollow`를 사용하는 것이 좋습니다.

어떤 방식으로든 링크 비용을 지급받은 경우 [`sponsored`](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko#sponsored) 또는 `nofollow`를 사용하여 링크에 자격을 부여할 수 있습니다. 포럼 섹션 또는 Q&A 사이트에서와 같이 사용자가 사이트에 링크를 삽입할 수 있는 경우 이러한 링크에도 [`ugc`](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=ko#ugc) 또는 `nofollow`를 추가하시기 바랍니다.