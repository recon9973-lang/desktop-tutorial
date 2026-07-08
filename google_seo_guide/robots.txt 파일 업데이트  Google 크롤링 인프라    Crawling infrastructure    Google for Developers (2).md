기존 robots.txt 파일의 규칙을 업데이트하려면 robots.txt 파일의 사본을 사이트에서 다운로드하여 필요에 따라 수정합니다. 그런 다음 업데이트된 파일을 사이트에 업로드합니다.

## robots.txt 파일 다운로드

robots.txt 파일은 다음과 같은 여러 가지 방법으로 다운로드할 수 있습니다.

-   robots.txt 파일로 이동(예: `https://example.com/robots.txt`)하여 콘텐츠를 컴퓨터의 새 텍스트 파일로 복사합니다. 새 로컬 파일을 만들 때는 [파일 형식](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#format_location)과 관련된 가이드라인을 따라야 합니다.
-   cURL과 같은 도구를 사용하여 robots.txt 파일의 실제 사본을 다운로드합니다. 예를 들면 다음과 같습니다.
    
    ```
    curl https://example.com/robots.txt -o robots.txt
    ```
    
-   Search Console의 [robots.txt 보고서](https://support.google.com/webmasters/answer/6062598?hl=ko)를 사용하여 robots.txt 파일의 콘텐츠를 복사한 다음 컴퓨터에 있는 파일에 붙여넣을 수 있습니다.

## robots.txt 파일 수정

사이트에서 다운로드한 robots.txt 파일을 텍스트 편집기에서 열고 필요에 따라 규칙을 수정합니다. [올바른 구문](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#create_rules)을 사용하고 UTF-8 인코딩으로 파일을 저장해야 합니다.

## robots.txt 파일 업로드

새 robots.txt 파일을 이름이 robots.txt인 텍스트 파일로 사이트의 루트 디렉터리에 업로드합니다. 파일을 사이트에 업로드하는 방법은 플랫폼과 서버에 따라 크게 달라집니다. [사이트에 robots.txt 파일을 업로드](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=ko#upload)하는 데 도움이 되는 팁을 확인하세요.

## Google의 robots.txt 캐시 새로고침

자동 크롤링 프로세스 중에 Google 크롤러는 robots.txt 파일의 변경사항을 감지하고 24시간마다 캐시된 버전을 업데이트합니다. 캐시를 더 빠르게 업데이트해야 한다면 [robots.txt 보고서](https://support.google.com/webmasters/answer/6062598?hl=ko)의 **재크롤링 요청** 기능을 사용합니다.