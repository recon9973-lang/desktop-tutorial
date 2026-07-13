# GROUND(@ground_geo) 인스타그램 사진 3장 발행 - Windows PowerShell (영상 취소, 사진만).
# here-string/인코딩 함정 회피: 캡션은 UTF-8 파일을 curl.exe로 받아 --data-urlencode @file 로 전송.
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
$assetRoot = "https://cdn.jsdelivr.net/gh/recon9973-lang/desktop-tutorial@6420a672817b34d0669584f3d3e1f68d41bbdaf4/persona-nami/ig"

$posts = @(
  @{ img = "$assetRoot/post1.png"; cap = "$assetRoot/post1.txt" },
  @{ img = "$assetRoot/post2.png"; cap = "$assetRoot/post2.txt" },
  @{ img = "$assetRoot/post3.png"; cap = "$assetRoot/post3.txt" }
)

$n = 0
foreach ($p in $posts) {
  $n = $n + 1
  Write-Host ("-------- posting " + $n + " --------")
  $capFile = [System.IO.Path]::GetTempFileName()
  & curl.exe -sS $p.cap -o $capFile
  $createJson = & curl.exe -sS -X POST "$base/$IgId/media" --data-urlencode "image_url=$($p.img)" --data-urlencode "caption@$capFile" -d "access_token=$Token"
  Remove-Item $capFile -Force -ErrorAction SilentlyContinue
  $create = $createJson | ConvertFrom-Json
  if (-not $create.id) { Write-Host ("X container failed: " + $createJson); continue }
  $cid = $create.id
  $statusUrl = $base + "/" + $cid + "?fields=status_code&access_token=" + $Token
  for ($i = 0; $i -lt 6; $i++) {
    $stJson = & curl.exe -sS $statusUrl
    if (($stJson | ConvertFrom-Json).status_code -eq "FINISHED") { break }
    Start-Sleep -Seconds 2
  }
  $pubJson = & curl.exe -sS -X POST "$base/$IgId/media_publish" -d "creation_id=$cid" -d "access_token=$Token"
  Write-Host ("OK published: " + $pubJson)
  if ($n -lt 3) { Start-Sleep -Seconds 30 }
}
Write-Host "done. check https://instagram.com/ground_geo"
