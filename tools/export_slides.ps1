# Render the ten UI-page slides to 1366 x 720 PNGs, as V1's migration rendered them.
#
#   powershell -ExecutionPolicy Bypass -File tools\export_slides.ps1 <out-dir>
#
# Reads every deck in "D:\Work\Urea Simulation Docs\Equipment Drawing\UI Pages" (or the folder
# given as -Source) and writes <out-dir>\<page>.png. PowerPoint exports at 2x and the result is
# downsampled bicubically, because its own 1366 x 720 export aliases the thin instrument lines.
# The 16:9 slide squashed onto the 1366 x 720 stage is the same anisotropic mapping the overlay
# layout uses (screen_layout.SLIDE_RX). Needs PowerPoint (COM).
#
# It leaves the user's PowerPoint as it found it: a PowerPoint that was already running is not
# quit, and a deck the user already has open is exported from that open presentation and left
# open, never closed and never reopened read-only over the user's window. An open deck renders
# as it stands on screen, unsaved edits included; save it first for a render of the saved file.
#
# The renders are the input of tools/restore_nav_blocks.py, which takes from them the drawn
# destination blocks V1's backgrounds lost (decided 2026-10-16, project.md decision 129), and of
# tools/restore_slide_regions.py (decision 221).
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$OutDir,
    [string]$Source = "D:\Work\Urea Simulation Docs\Equipment Drawing\UI Pages"
)

New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
$decks = Get-ChildItem $Source -Filter *.pptx | Where-Object { $_.Name -notlike '~$*' }

$wasRunning = [bool](Get-Process POWERPNT -ErrorAction SilentlyContinue)
$app = New-Object -ComObject PowerPoint.Application
try {
    foreach ($deck in $decks) {
        $big = Join-Path $OutDir "$($deck.BaseName)-2x.png"
        $open = $null
        foreach ($p in $app.Presentations) { if ($p.FullName -ieq $deck.FullName) { $open = $p } }
        if ($open) {
            $open.Slides.Item(1).Export($big, "PNG", 2732, 1440)
            "exported $($deck.BaseName) from the presentation already open (left open)"
        } else {
            $pres = $app.Presentations.Open($deck.FullName, $true, $false, $false)
            $pres.Slides.Item(1).Export($big, "PNG", 2732, 1440)
            $pres.Close()
        }
    }
} finally {
    if (-not $wasRunning) { $app.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}

Add-Type -AssemblyName System.Drawing
foreach ($deck in $decks) {
    $big = Join-Path $OutDir "$($deck.BaseName)-2x.png"
    $src = [System.Drawing.Image]::FromFile($big)
    $bmp = New-Object System.Drawing.Bitmap 1366, 720
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.DrawImage($src, (New-Object System.Drawing.Rectangle 0, 0, 1366, 720))
    $g.Dispose(); $src.Dispose()
    $bmp.Save((Join-Path $OutDir "$($deck.BaseName).png"), [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Remove-Item $big
    "rendered $($deck.BaseName).png"
}
