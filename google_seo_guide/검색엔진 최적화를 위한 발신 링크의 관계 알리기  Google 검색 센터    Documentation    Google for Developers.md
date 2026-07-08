# Google에 외부 연결 링크의 유효성 알리기

사이트에 있는 일부 링크의 경우 링크된 페이지와의 관계를 Google에 알리는 것이 좋습니다. 이렇게 하려면 `<a>` 태그에 다음 `rel` 속성 값 중 하나를 사용하세요.

아무런 확인 없이도 Google이 가져오고 파싱해야 하는 일반 링크의 경우 `rel` 속성을 추가하지 않아도 됩니다. 예:

```php-template
<p>My favorite horse is the <a href="https://horses.example.com/Palomino">palomino</a>.</p>
```

다른 링크의 경우 다음 값 중 하나 이상을 사용하세요.

| `rel` 값 | `rel` 값 |
|---------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ### `rel="sponsored"` | 광고 링크나 유료 게재 링크(일반적으로 _유료 링크_라고 함)를 `sponsored` 값으로 표시합니다. [유료 링크에 관한 Google의 입장](https://developers.google.com/search/docs/essentials/spam-policies?hl=ko#link-spam)에 관해 자세히 알아보기

<a **rel="sponsored"** href="https://cheese.example.com/Appenzeller_cheese">Appenzeller</a> |
| ### `rel="ugc"` | 댓글 및 포럼 게시물과 같은 사용자 제작 콘텐츠(UGC) 링크는 `ugc` 값으로 표시하는 것이 좋습니다.

<a **rel="ugc"** href="https://cheese.example.com/Appenzeller_cheese">Appenzeller</a>

신뢰할 수 있는 참여자를 인정하고 보상을 제공하기 위해 오랜 시간 동안 지속적으로 우수한 기여를 해 온 회원 또는 사용자가 게시한 링크에서 이 속성을 삭제할 수도 있습니다. [사이트 및 플랫폼에서 사용자 생성 스팸을 방지](https://developers.google.com/search/docs/monitor-debug/prevent-abuse?hl=ko)하는 방법 자세히 알아보기 |
| ### `rel="nofollow"` | 다른 값이 적용되지 않으며 Google에서 내 사이트와 링크된 페이지를 연결하지 않기를 바라거나 링크된 페이지를 크롤링하지 않기를 바라는 경우 `nofollow` 값을 사용합니다. 내 사이트 내의 링크인 경우 [robots.txt `disallow` 규칙](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt?hl=ko#disallow)을 사용합니다.

<a **rel="nofollow"** href="https://cheese.example.com/Appenzeller_cheese">Appenzeller</a> |
| ### _여러 값_ | 공백 또는 쉼표로 구분된 목록으로 여러 `rel` 값을 지정할 수 있습니다. **예:**

<p>I love <a **rel="ugc nofollow"** href="https://cheese.example.com/Appenzeller_cheese">Appenzeller</a> cheese.</p>

<p>I hate <a **rel="ugc,nofollow"** href="https://cheese.example.com/blue_cheese">Blue</a> cheese.</p> |

일반적으로 이러한 `rel` 속성이 표시된 링크는 추적되지 않습니다. 사이트맵이나 다른 사이트의 링크와 같은 다른 수단을 통해서도 링크된 페이지가 발견될 수 있으므로 페이지가 크롤링될 가능성은 여전히 존재합니다. 이러한 `rel` 속성은 [Google에서 크롤링할 수 있는 `<a>` 요소](https://developers.google.com/search/docs/crawling-indexing/links-crawlable?hl=ko#crawlable-links)에서만 사용됩니다. 다만 `nofollow`는 제외되며 이는 [robots `meta` 태그](https://developers.google.com/search/docs/crawling-indexing/special-tags?hl=ko)로도 제공됩니다.

Google에서 내 사이트의 페이지 링크를 가져오지 못하게 하려면 [robots.txt `disallow` 규칙](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt?hl=ko#disallow)을 사용하세요.

Google에서 페이지 색인을 생성하지 못하게 하려면 크롤링을 허용하고 [`noindex` robots 규칙](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=ko)을 사용하세요.