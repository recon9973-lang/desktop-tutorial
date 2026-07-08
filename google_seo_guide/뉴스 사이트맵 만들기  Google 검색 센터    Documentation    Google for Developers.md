## 뉴스 사이트맵

뉴스 게시자인 경우에는 뉴스 사이트맵을 사용하여 뉴스 기사와 추가 정보를 Google에 알려주세요. 기존 사이트맵을 뉴스 관련 태그를 사용하여 확장하거나 뉴스 기사 전용으로 사용할 수 있는 별도의 뉴스 사이트맵을 만들 수 있습니다. 두 옵션 모두 Google에서 정상적으로 작동하지만 뉴스 기사 전용 사이트맵을 별도로 만들면 Search Console의 Google 검색에서 콘텐츠를 더 잘 추적할 수 있습니다.

## 뉴스 사이트맵 권장사항

뉴스 사이트맵은 일반적인 사이트맵을 기반으로 하므로 뉴스 사이트맵에도 [일반 사이트맵 권장사항](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=ko#general-guidelines)이 적용됩니다.

새로운 기사가 게시되면 뉴스 사이트맵을 업데이트합니다. 업데이트할 때마다 새로운 사이트맵을 만들지 마세요. Google 뉴스는 사이트의 나머지 부분을 크롤링하는 것과 같은 빈도로 뉴스 사이트맵을 크롤링합니다.

지난 2일 동안 작성된 기사의 최근 URL만 포함합니다. 기사가 게시된 지 2일 이상 지난 후에는 뉴스 사이트맵에서 URL을 삭제하거나 사이트맵의 이전 URL에서 `<news:news>` 메타데이터를 삭제합니다.

뉴스 사이트맵에서 이전 URL을 삭제하는 방법을 선택하면 일정 기간 동안 사이트맵이 비어 있게 됩니다. 지난 며칠 동안 기사를 게시하지 않았다면 사이트맵이 비어있게 됩니다. Search Console에 빈 사이트맵 경고가 표시될 수 있지만 이는 사이트맵이 비어있는 상태가 의도된 것인지 확인하기 위한 것입니다. 파일이 비어 있더라도 Google 검색에 어떠한 문제도 발생하지 않습니다.

## 뉴스 사이트맵 예

다음 예는 뉴스 확장 프로그램이 포함된 일반 사이트맵을 보여줍니다. `<url>` 태그 1개와 필수 하위 태그가 있는 단일 `<news:news>` 태그를 포함합니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
  <loc>http://www.example.org/business/article55.html</loc>
  <news:news>
    <news:publication>
      <news:name>The Example Times</news:name>
      <news:language>en</news:language>
    </news:publication>
    <news:publication_date>2008-12-23</news:publication_date>
    <news:title>Companies A, B in Merger Talks</news:title>
  </news:news>
  </url>
</urlset>
```

## 뉴스 사이트맵 참조

`news` 태그는 뉴스 사이트맵 네임스페이스([`http://www.google.com/schemas/sitemap-news/0.9`](http://www.google.com/schemas/sitemap-news/0.9?hl=ko))에 정의됩니다.

Google에서 뉴스 사이트맵을 사용할 수 있도록 하려면 다음과 같은 필수 태그를 사용해야 합니다.

| 필수 태그 | 필수 태그 |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<news:news>` | `news:` 네임스페이스에 있는 다른 태그의 상위 태그입니다. 각 `url` 사이트맵 태그에는 `news:news` 태그가 1개만 포함될 수 있으며(그에 대응되는 닫는 태그도 포함), 하나의 사이트맵에는 최대 1,000개의 `news:news` 태그가 포함될 수 있습니다. 뉴스 사이트맵에 `<news:news>` 태그가 1,000개 이상인 경우 [사이트맵을 여러 개의 작은 사이트맵으로 분할](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps?hl=ko)하세요. |
| `<news:publication>` | `<news:name>` 및 `<news:language>` 태그의 상위 태그입니다. 각 `<news:news>` 상위 태그에는 `<news:publication>` 태그 1개만 있을 수 있습니다. |
| `<news:name>` | `<news:name>` 태그는 뉴스 간행물의 이름입니다. 괄호 안의 내용을 제외하고 [news.google.com](https://news.google.com/?hl=ko)의 기사에 표시된 이름과 정확히 일치해야 합니다. |
| `<news:language>` | `<news:language>` 태그는 간행물의 언어입니다. [ISO 639 언어 코드](http://www.loc.gov/standards/iso639-2/php/code_list.php)(2자 또는 3자)를 사용합니다.

**예외**: 중국어의 경우 간체에는 `zh-cn`을 사용하고 번체에는 `zh-tw`를 사용합니다. |
| `<news:publication_date>` | [W3C 형식](http://www.w3.org/TR/NOTE-datetime)의 기사 발행일입니다. '완전한 날짜' 형식(`YYYY-MM-DD`) 또는 '완전한 날짜와 시간, 분, 초'에 시간대 지정자가 포함된 형식(`YYYY-MM-DDThh:mm:ssTZD`)을 사용합니다. 기사를 사이트에 처음 게시한 원래 날짜와 시간을 지정합니다. 기사를 사이트맵에 추가한 시간은 지정하지 않습니다.

Google에서 허용하는 형식은 다음과 같습니다.

-   완전한 날짜: `YYYY-MM-DD (1997-07-16)`
-   완전한 날짜와 시간, 분: `YYYY-MM-DDThh:mmTZD (1997-07-16T19:20+01:00)`
-   완전한 날짜와 시간, 분, 초: `YYYY-MM-DDThh:mm:ssTZD (1997-07-16T19:20:30+01:00)`
-   완전한 날짜와 시간, 분, 초, 초의 소수점 아래 한 자리: `YYYY-MM-DDThh:mm:ss.sTZD`(`1997-07-16T19:20:30.45+01:00`) |
| `<news:title>` | 뉴스 기사의 제목입니다. |

## 사이트맵 문제 해결

사이트맵에 문제가 있는 경우 Google Search Console을 사용하여 오류를 조사할 수 있습니다. 도움이 필요한 경우 Search Console의 [사이트맵 문제 해결 가이드](https://support.google.com/webmasters/answer/7451001?hl=ko#errors)를 참고하세요.