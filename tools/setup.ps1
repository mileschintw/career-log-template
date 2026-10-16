# Install the local LaTeX toolchain for building resumes on Windows. Idempotent; no admin.
#   - TinyTeX (pdfTeX; the templates use \pdfgentounicode) into %APPDATA%\TinyTeX
#   - the TeX packages in tools\tex-packages.txt
#   - poppler (pdfinfo, pdftotext, pdftoppm) through winget, scoop or choco
# Run from PowerShell:  powershell -ExecutionPolicy Bypass -File tools\setup.ps1
$ErrorActionPreference = 'Stop'
$Root = (git -C $PSScriptRoot rev-parse --show-toplevel).Trim()

# TinyTeX's own rule: APPDATA unless the path has spaces or non-ASCII characters
$TexBase = if ($env:APPDATA -match '^[!-~]+$') { $env:APPDATA } else { $env:ProgramData }
$TexDir = Join-Path $TexBase 'TinyTeX'
$Bin = Join-Path $TexDir 'bin\windows'
$Tlmgr = Join-Path $Bin 'tlmgr.bat'

if (-not (Test-Path (Join-Path $Bin 'pdflatex.exe'))) {
  Write-Host "Installing TinyTeX into $TexDir"
  $Tmp = Join-Path $env:TEMP ("tinytex-" + [guid]::NewGuid())
  New-Item -ItemType Directory -Path $Tmp | Out-Null
  Push-Location $Tmp
  try {
    curl.exe -fL --retry 5 -o TinyTeX-1-windows.exe 'https://github.com/rstudio/tinytex-releases/releases/download/daily/TinyTeX-1-windows.exe'
    & .\TinyTeX-1-windows.exe -y | Out-Null   # self-extracting archive; unpacks .\TinyTeX
    if ($LASTEXITCODE -ne 0) { throw 'TinyTeX extraction failed' }
    Move-Item TinyTeX $TexBase
  } finally {
    Pop-Location
    Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
  }
}
Write-Host "pdflatex: $Bin\pdflatex.exe"

$Pkgs = Get-Content (Join-Path $Root 'tools\tex-packages.txt') | Where-Object { $_ -notmatch '^\s*(#|$)' }
# A TinyTeX older than the repository refuses to install until tlmgr updates itself.
& $Tlmgr update --self
if ($LASTEXITCODE -ne 0) { throw 'tlmgr update --self failed' }
& $Tlmgr install @Pkgs
if ($LASTEXITCODE -ne 0) { throw 'tlmgr install failed' }

# Any pdftotext on PATH is not enough: Git for Windows ships xpdf's, which lacks the
# -bbox-layout that tools\resume.py needs. Look for poppler's on PATH and in winget's folder.
function Test-Poppler {
  $ErrorActionPreference = 'Continue'   # Windows PowerShell turns native stderr into errors under Stop
  $Cands = @(Get-Command pdftotext -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }) +
           @(Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\*Poppler*\*\Library\bin\pdftotext.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
  foreach ($c in $Cands) { if ((& $c -h 2>&1 | Out-String) -match 'bbox-layout') { return $true } }
  return $false
}

if (-not (Test-Poppler)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install --id oschwartz10612.Poppler -e --accept-source-agreements --accept-package-agreements
  } elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
    scoop install poppler
  } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
    choco install poppler -y
  } else {
    throw 'Install poppler with winget, scoop or choco, or set POPPLER_BIN to its bin folder'
  }
}

if (Get-Command py -ErrorAction SilentlyContinue) { $PyExe = 'py'; $PyArgs = @('-3') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $PyExe = 'python'; $PyArgs = @() }
else { throw 'Python 3.9+ is required (winget install Python.Python.3.12)' }

Write-Host 'Checking: building the example resume'
$Newest = Get-Item (Join-Path $Root 'skills\career-log\examples\resume.tex')
$Check = Join-Path $Root '.build\setup-check'
New-Item -ItemType Directory -Path $Check -Force | Out-Null
Copy-Item $Newest.FullName $Check   # build a copy, so the example stays untouched
& $PyExe @PyArgs (Join-Path $Root 'tools\resume.py') (Join-Path $Check $Newest.Name) --out (Join-Path $Check 'build')
exit $LASTEXITCODE
