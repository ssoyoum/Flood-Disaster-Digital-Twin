# build.py 다음에 실행한다.
#   powershell -ExecutionPolicy Bypass -File finalize.ps1 [-Preview <폴더>]
# PowerPoint 로 기본 PPTX 를 읽기 전용으로 열어 PDF 사본을 만들고, -Preview 를 주면 장마다 PNG 를 내보낸다.
# 글꼴 포함 저장은 하지 않는다. PowerPoint 가 Noto Sans KR 을 일부 글자만 포함해 저장하는데,
# 다른 프로그램에서 그 조각 글꼴 때문에 글자가 깨져 보였다(2026-10-07).
param([string]$Preview = "")

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
# Windows PowerShell 5.1 은 BOM 없는 UTF-8 스크립트의 한글을 깨뜨리므로 파일명을 적지 않고 찾는다.
$deck = (Get-ChildItem -LiteralPath $here -Filter "*.pptx" | Where-Object { $_.Name -notlike "_*" -and $_.Name -notlike "*(PNG)*" } | Select-Object -First 1).FullName
$pdf  = [System.IO.Path]::ChangeExtension($deck, ".pdf")

$pp = New-Object -ComObject PowerPoint.Application
try {
    $p = $pp.Presentations.Open($deck, -1, 0, 0)
    $p.SaveCopyAs($pdf, 32)
    if ($Preview -ne "") {
        New-Item -ItemType Directory -Force $Preview | Out-Null
        for ($i = 1; $i -le $p.Slides.Count; $i++) {
            $p.Slides.Item($i).Export((Join-Path $Preview ("s{0:D2}.png" -f $i)), "PNG", 1600, 900)
        }
    }
    "slides: " + $p.Slides.Count
    $p.Close()
} finally { $pp.Quit() }
"pdf: $pdf"
