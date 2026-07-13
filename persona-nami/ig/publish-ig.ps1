# GROUND(@ground_geo) 인스타그램 사진 3장 발행 — Windows PowerShell 전용 (영상 취소, 사진만).
# 한글·이모지 캡션은 UTF-8 임시파일 + curl.exe(--data-urlencode @file)로 안전하게 전송.
#
# 실행:
#   powershell -ExecutionPolicy Bypass -File .\publish-ig.ps1 -Token "<INSTAGRAM_ACCESS_TOKEN>"
#
# 필요: Windows 10 1803+ (curl.exe 내장)
param(
  [Parameter(Mandatory = $true)][string]$Token,
  [string]$IgId = "17841472664941872",
  [string]$GraphVersion = "v21.0"
)
$ErrorActionPreference = "Stop"
$base = "https://graph.facebook.com/$GraphVersion"
# 공개 이미지 URL(커밋 SHA 고정)
$imgBase = "https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@2b9583686e9bac72339740fb6e15ad93114fcfe4/persona-nami/ig"

$cap1 = @'
요즘 저희 엄마도 궁금한 거 있으면 초록창 대신 챗지피티한테 물어보시더라고요 😅

검색이 '링크 고르기'에서 '답 하나 받기'로 바뀌는 중이에요. 그래서 이제 마케팅은 '검색 1등'이 아니라 → AI가 콕 집어 골라주는 그 답이 되는 것이 핵심이에요.

이걸 GEO(생성형 엔진 최적화)라고 불러요. 어렵지 않아요, 여기서 하나씩 같이 풀어봐요!

여러분은 요즘 검색, 어디서 하세요? 👇

#GEO #AI검색 #마케팅 #GROUND #검색마케팅 #디지털마케팅
'@

$cap2 = @'
궁금해서 진짜 해봤어요. ChatGPT한테 "○○ 잘하는 곳 추천해줘" 했더니… 우리는 언급도 안 되더라고요 🥲

AI는 '검색 순위'가 아니라 '믿을 만한 정보'를 골라서 인용하거든요. 그래서 요즘 AEO(답변 엔진 최적화)가 중요해졌어요.

오늘은 핵심 3가지만!
1️⃣ 질문–답 형식으로 쓰기
2️⃣ 출처·근거 확실하게
3️⃣ FAQ 구조화(스키마)

내일 하나씩 자세히 올릴게요 📌 궁금한 거 댓글 주세요!

#AEO #챗지피티 #콘텐츠마케팅 #GROUND #검색마케팅 #디지털마케팅
'@

$cap3 = @'
스압 없이 딱 3줄이면 돼요 😎

SEO는 이제 '키워드 많이 넣기'가 아니에요.
① 사람이 진짜 궁금한 걸 → ② 명확하게 답하고 → ③ 검색엔진이랑 AI 둘 다 이해하게 정리하기.

이 셋만 지켜도 절반은 먹고 들어가요.

저장해두고 글 쓸 때 꺼내보세요 🔖

#SEO #검색최적화 #마케팅꿀팁 #GROUND #검색마케팅 #디지털마케팅
'@

$posts = @(
  @{ img = "$imgBase/post1.png"; cap = $cap1 },
  @{ img = "$imgBase/post2.png"; cap = $cap2 },
  @{ img = "$imgBase/post3.png"; cap = $cap3 }
)

$utf8 = New-Object System.Text.UTF8Encoding($false)
$idx = 0
foreach ($p in $posts) {
  $idx++
  Write-Host "──────── 포스팅 $idx ────────"
  $capFile = [System.IO.Path]::GetTempFileName()
  [System.IO.File]::WriteAllText($capFile, $p.cap, $utf8)
  try {
    # 1) 컨테이너 생성 — curl.exe(진짜 curl), 캡션은 UTF-8 파일에서 URL 인코딩
    $createJson = & curl.exe -sS -X POST "$base/$IgId/media" `
      --data-urlencode "image_url=$($p.img)" `
      --data-urlencode "caption@$capFile" `
      -d "access_token=$Token"
  } finally {
    Remove-Item $capFile -Force -ErrorAction SilentlyContinue
  }
  $create = $createJson | ConvertFrom-Json
  if (-not $create.id) { Write-Host "✗ 컨테이너 실패: $createJson"; continue }
  $cid = $create.id

  # 2) 상태 확인(사진은 대개 즉시 FINISHED)
  for ($i = 0; $i -lt 5; $i++) {
    $stJson = & curl.exe -sS "$base/$cid`?fields=status_code&access_token=$Token"
    if (($stJson | ConvertFrom-Json).status_code -eq "FINISHED") { break }
    Start-Sleep -Seconds 2
  }

  # 3) 발행
  $pubJson = & curl.exe -sS -X POST "$base/$IgId/media_publish" -d "creation_id=$cid" -d "access_token=$Token"
  Write-Host "✓ 발행 결과: $pubJson"

  if ($idx -lt 3) { Start-Sleep -Seconds 30 }  # 레이트리밋 여유
}
Write-Host ""
Write-Host "완료. https://instagram.com/ground_geo 에서 확인하세요."
