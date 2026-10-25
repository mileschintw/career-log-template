# Machine setup on Windows (SETUP.md step 5). Idempotent. Installs for this user only, with no
# administrator dialog.
#
#   powershell -ExecutionPolicy Bypass -File tools\setup.ps1 [-Yes playwright-cli] [-No playwright-cli]
#
# Always: Python 3.11+ (winget, for this user only, when py -3 is older), and TinyTeX (pdfTeX; the
#   templates use \pdfgentounicode) into %APPDATA%\TinyTeX (or one already in a packaged app's store,
#   as tools\resume.py finds it), the packages in tools\tex-packages.txt, and poppler (pdfinfo,
#   pdftotext, pdftoppm): the user's own when tools\resume.py finds one, else conda-forge's, which
#   micromamba installs into ~\.career-log\poppler, with the runtime DLLs it needs, and a rerun
#   updates (#281).
# Optional, installed only when ~\.career-log\machine.toml says yes for it:
#   playwright-cli  Node 18+ (winget's per-user zip), @playwright/cli (npm), its skill in this
#                   checkout, Chromium when Chrome and Edge are both missing (with Edge and no
#                   Chrome, playwright-cli picks Edge: #166)
# -Yes and -No write the user's choice into machine.toml first; with only -No, that is all.
# A scheduled or unattended run (CAREER_LOG_UNATTENDED set, or no interactive desktop) records any
# -Yes or -No, then installs nothing, opens no dialog, and exits 3.
# Started inside a packaged app's container (the Claude desktop app's Git Bash, and a Windows
# PowerShell it starts), it runs itself again outside the container and shows that run's output:
# what it installs inside would land in the app's private store, where shells outside it cannot
# see it (#152, #162).
# Ends with tools\check.py setup.
param([string]$Yes = '', [string]$No = '', [switch]$Outside)
$ErrorActionPreference = 'Stop'
# A program that cannot load a DLL (a poppler of the user's without the Visual C++ runtime) fails at
# once, with no dialog; the processes this one starts inherit the mode
Add-Type -Namespace CareerLog -Name Native -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetErrorMode(uint mode); [DllImport("kernel32.dll")] public static extern uint GetOEMCP();'
[CareerLog.Native]::SetErrorMode(0x8003) | Out-Null
# The folder above tools\ (tools\resume.py's fallback without git): needs no git and works outside a checkout
$Root = Split-Path -Parent $PSScriptRoot
$Tools = @('playwright-cli')
$Machine = Join-Path $HOME '.career-log\machine.toml'

function Update-Path {   # this process sees what an install added to the machine's or user's PATH, ahead of older entries
  $Dirs = ([Environment]::GetEnvironmentVariable('Path', 'Machine'), [Environment]::GetEnvironmentVariable('Path', 'User'), $env:Path) -join ';'
  $env:Path = (@($Dirs -split ';' | Where-Object { $_ }) | Select-Object -Unique) -join ';'
}
function Add-UserPath($Dir) {   # for every later shell too; the user's PATH needs no admin
  $User = [Environment]::GetEnvironmentVariable('Path', 'User')
  if (-not (($User -split ';') -contains $Dir)) {
    [Environment]::SetEnvironmentVariable('Path', ($(if ($User) { "$User;" } else { '' }) + $Dir), 'User')
    Write-Host "added to your PATH: $Dir"
  }
  Update-Path
  $env:Path = "$Dir;$env:Path"   # ahead of an older copy elsewhere on PATH (a machine-wide Node below 18)
}

# ---- The user's choices: one `<tool> = true|false` line per optional tool in machine.toml ----

function Write-Machine($Lines) { [IO.File]::WriteAllLines($Machine, [string[]]$Lines) }   # UTF-8 without BOM, which tomllib needs
# TinyTeX was optional before #151; a leftover yes or no is dropped, since setup now always installs it
if ((Test-Path $Machine) -and (@(Get-Content $Machine) -match '^tinytex *=').Count -gt 0) {
  Write-Machine @(Get-Content $Machine | Where-Object { $_ -notmatch '^tinytex *=' })
  Write-Host 'machine.toml: removed tinytex (TinyTeX is no longer optional: setup always installs it)'
}
function Set-Machine($Key, $Value) {   # one `<key> = <TOML value>` line in machine.toml
  New-Item -ItemType Directory -Force -Path (Split-Path $Machine) | Out-Null
  $Lines = if (Test-Path $Machine) { @(Get-Content $Machine) } else { @(
    '# career-log Machine setup: the optional tools the user wants on this machine',
    '# (true) or declined (false), and where poppler came from. Written by tools/setup.sh and',
    '# tools/setup.ps1; whether a tool is installed is detected on every run (tools/check.py).') }
  Write-Machine (@($Lines | Where-Object { $_ -notmatch "^$([regex]::Escape($Key)) *=" }) + "$Key = $Value")
  Write-Host "machine.toml: $Key = $Value"
}
function Set-Choice($List, $Value) {
  foreach ($t in ($List -split ',' | Where-Object { $_ })) {
    if ($t -eq 'tinytex') { Write-Host 'tinytex: not optional any more; setup always installs it'; continue }
    if ($Tools -notcontains $t) { throw "unknown tool: $t (tools: $($Tools -join ', '))" }
    Set-Machine $t $Value
  }
}
Set-Choice $Yes 'true'
Set-Choice $No 'false'
if ($No -and -not $Yes) { exit 0 }   # a no only records the answer: nothing to install
function Test-Chosen($t, $Value) { (Test-Path $Machine) -and (@(Get-Content $Machine) -match "^$([regex]::Escape($t)) *= *$Value").Count -gt 0 }

# ---- Unattended: no installs, no dialog ----

if ($env:CAREER_LOG_UNATTENDED -or -not [Environment]::UserInteractive) {
  Write-Host "unattended run (CAREER_LOG_UNATTENDED is set, or there is no desktop): setup installs nothing and opens no dialog. If tools\check.py reports something missing, run setup while the user is at the machine: powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
  exit 3
}

# ---- A packaged app's container: run again outside it ----

# Inside a container, a new folder under %LOCALAPPDATA% goes to the app's store instead (#152).
# No API shows the container (GetCurrentPackageFullName fails inside it too), so this looks.
function Test-InsidePackage {
  $Name = 'career-log-probe-' + [guid]::NewGuid()
  New-Item -ItemType Directory -Path (Join-Path $env:LOCALAPPDATA $Name) | Out-Null
  $Stored = @(Get-ChildItem "$env:LOCALAPPDATA\Packages\*\LocalCache\Local\$Name" -Directory -ErrorAction SilentlyContinue)
  Remove-Item (Join-Path $env:LOCALAPPDATA $Name) -Force
  return $Stored.Count -gt 0
}
if (-not $Outside -and (Test-InsidePackage)) {
  # A process WMI starts belongs to no package. Its window stays hidden; Windows' dialog still shows.
  Write-Host "Inside a packaged app's container: running setup again outside it, so every shell sees what it installs"
  $Out = Join-Path $env:TEMP ('career-log-setup-' + [guid]::NewGuid())
  # Windows PowerShell, never this host: a Store pwsh started by its path may run in its own package.
  # The run starts with the user's saved environment, so a variable set only in this shell is not in it.
  $Exe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
  # `call echo %^errorlevel%` reads the exit code when it runs, not when cmd parses the line
  $Line = 'cmd.exe /d /c ""{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}" -Outside > "{2}.log" 2>&1 & call echo exit %^errorlevel%> "{2}.exit""' -f $Exe, $PSCommandPath, $Out
  $Startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
  $Started = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $Line; ProcessStartupInformation = $Startup }
  if ($Started.ReturnValue -ne 0) { throw "could not start setup outside the container (Win32_Process.Create returned $($Started.ReturnValue))" }
  # The run writes in its console's code page, the system's OEM one; a line is shown once it is whole.
  # Stopping this shell does not stop that run: it goes on, hidden, to the end.
  $Enc = [Text.Encoding]::GetEncoding([int][CareerLog.Native]::GetOEMCP())
  $Pos = 0; $Code = $null
  do {
    try { if ((Get-Content "$Out.exit" -Raw -ErrorAction Stop) -match 'exit (-?\d+)') { $Code = [int]$Matches[1] } } catch { }
    if (Test-Path "$Out.log") {   # read after the exit file, so the log's last lines are shown
      $s = [IO.File]::Open("$Out.log", 'Open', 'Read', 'ReadWrite')
      try { $null = $s.Seek($Pos, 'Begin'); $Buf = New-Object byte[] ($s.Length - $Pos); $n = $s.Read($Buf, 0, $Buf.Length) }
      finally { $s.Close() }
      $End = if ($null -ne $Code -or $n -eq 0) { $n } else { [Array]::LastIndexOf($Buf, [byte]10, $n - 1) + 1 }
      if ($End -gt 0) { [Console]::Out.Write($Enc.GetString($Buf, 0, $End)); $Pos += $End }
    }
    if ($null -eq $Code) { Start-Sleep -Seconds 2 }
  } until ($null -ne $Code)
  Remove-Item "$Out.log", "$Out.exit" -ErrorAction SilentlyContinue
  exit $Code
}
Update-Path   # a shell opened before an earlier run has not seen what it added

# ---- Python 3.11+ ----
# py -3 first, for the reason SKILL.md, Platforms gives.

function Find-Python {
  $ErrorActionPreference = 'Continue'   # Windows PowerShell turns native stderr into errors under Stop (the Store's python stub writes some)
  foreach ($c in @(@('py', '-3'), @('python'))) {
    if (Get-Command $c[0] -ErrorAction SilentlyContinue) {
      & $c[0] @($c | Select-Object -Skip 1) -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>$null
      if ($LASTEXITCODE -eq 0) { return , $c }
    }
  }
  return $null
}
$Py = Find-Python
if (-not $Py) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'missing: Python 3.11+ and winget. Install Python 3.11+ for your user from python.org, then rerun' }
  Write-Host 'Installing Python 3.13 for this user only (winget)'
  # The launcher too goes in per user: the installer's default puts it in for all users, which needs admin
  winget install --id Python.Python.3.13 -e --source winget --scope user --accept-source-agreements --accept-package-agreements --override '/quiet InstallAllUsers=0 InstallLauncherAllUsers=0 PrependPath=1 Include_test=0'
  Update-Path
  $Py = Find-Python   # judged by the result: winget exits nonzero for "already installed" too
  if (-not $Py) { throw "Python 3.11+ install failed (winget exit $LASTEXITCODE): py -3 still finds none" }
}
$PyExe = $Py[0]; $PyArgs = @($Py | Select-Object -Skip 1)
Write-Host "python: $((@($PyExe) + $PyArgs) -join ' ') ($(& $PyExe @PyArgs --version))"

# ---- playwright-cli ----

function Test-Node {
  $ErrorActionPreference = 'Continue'
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { return $false }
  # The version from `node --version` (v24.11.0): Windows PowerShell drops the quotes inside a `node -e` script
  return [int]((& node --version) -replace '^v(\d+)\..*', '$1') -ge 18
}
function Install-Playwright {
  if (-not (Test-Node)) {
    Write-Host 'Installing Node LTS for this user only (winget, a zip under %LOCALAPPDATA%)'
    winget install --id OpenJS.NodeJS.LTS -e --source winget --scope user --accept-source-agreements --accept-package-agreements
    $WingetExit = $LASTEXITCODE   # nonzero for "already installed" too, so the result decides
    $NodeDir = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS*\node-*" -Directory -ErrorAction SilentlyContinue |
      Sort-Object Name -Descending | Select-Object -First 1
    if (-not $NodeDir) { throw "Node install failed (winget exit $WingetExit): no node folder under %LOCALAPPDATA%\Microsoft\WinGet\Packages" }
    Add-UserPath $NodeDir.FullName   # npm.cmd sits beside node.exe; winget links only node.exe
    if (-not (Test-Node)) { throw 'Node install failed: node does not start' }
  }
  Write-Host "node: $((Get-Command node).Source) ($(node --version))"
  Add-UserPath (Join-Path $env:APPDATA 'npm')   # npm's global folder, where playwright-cli goes
  if (-not (Get-Command playwright-cli -ErrorAction SilentlyContinue)) {
    npm install -g '@playwright/cli@latest'
    if ($LASTEXITCODE -ne 0) { throw 'npm install -g @playwright/cli failed' }
  }
  # playwright-cli install --skills picks Chrome, then Edge, as tools\check.py looks for them
  $Browser = @($env:LOCALAPPDATA, $env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ } |
    Where-Object { (Test-Path (Join-Path $_ 'Google\Chrome\Application\chrome.exe')) -or
                   (Test-Path (Join-Path $_ 'Microsoft\Edge\Application\msedge.exe')) }
  if (-not $Browser) {
    Write-Host "Chrome and Edge not found: installing Chromium into Playwright's cache"
    playwright-cli install-browser chromium
    if ($LASTEXITCODE -ne 0) { throw 'playwright-cli install-browser chromium failed' }
  }
  # The skill and, without Chrome, .playwright\cli.config.json (Edge or Chromium): per checkout, ignored by git
  Push-Location $Root
  try { playwright-cli install --skills; if ($LASTEXITCODE -ne 0) { throw 'playwright-cli install --skills failed' } }
  finally { Pop-Location }
}

# ---- TinyTeX ----

function Install-TinyTeX {
  # TinyTeX's own rule: APPDATA unless the path has spaces or non-ASCII characters
  $TexBase = if ($env:APPDATA -match '^[!-~]+$') { $env:APPDATA } else { $env:ProgramData }
  $TexDir = Join-Path $TexBase 'TinyTeX'
  $Bin = Join-Path $TexDir 'bin\windows'
  # A copy in a packaged app's store comes first, as in tools\resume.py: an older setup run inside
  # the Claude desktop app's container put it there (#152), and every shell finds it by that path
  $Stored = Get-ChildItem "$env:LOCALAPPDATA\Packages\*\LocalCache\Roaming\TinyTeX\bin\windows\pdflatex.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($Stored) { $Bin = $Stored.DirectoryName }
  $Tlmgr = Join-Path $Bin 'tlmgr.bat'

  if (-not (Test-Path (Join-Path $Bin 'pdflatex.exe'))) {
    if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
      throw 'missing: curl.exe (part of Windows 10 1803 and later). Install curl, then rerun'
    }
    Write-Host "Installing TinyTeX into $TexDir"
    $Tmp = Join-Path $env:TEMP ("tinytex-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $Tmp | Out-Null
    Push-Location $Tmp
    try {   # finally also runs on Ctrl-C, so no 70 MB leftover in %TEMP%
      curl.exe -fL --retry 5 -o TinyTeX-1-windows.exe 'https://github.com/rstudio/tinytex-releases/releases/download/daily/TinyTeX-1-windows.exe'
      if ($LASTEXITCODE -ne 0) { throw "TinyTeX download failed (curl exit $LASTEXITCODE). Check the network or proxy (HTTPS_PROXY), then rerun" }
      & .\TinyTeX-1-windows.exe -y | Out-Null   # self-extracting archive; unpacks .\TinyTeX
      if ($LASTEXITCODE -ne 0) { throw 'TinyTeX extraction failed' }
      New-Item -ItemType Directory -Force -Path $TexBase | Out-Null   # Move-Item renames into a missing folder
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

  Install-Poppler
  if (-not (Get-Pdftotext)) {
    Write-Host 'poppler missing: skipping the example build until it is installed'
    return
  }
  Write-Host 'Checking: building the example resume'
  $Newest = Get-Item (Join-Path $Root 'skills\career-log\examples\resume.tex')
  $Check = Join-Path $Root '.build\setup-check'
  New-Item -ItemType Directory -Path $Check -Force | Out-Null
  Copy-Item $Newest.FullName $Check   # build a copy, so the example stays untouched
  & $PyExe @PyArgs (Join-Path $Root 'tools\resume.py') (Join-Path $Check $Newest.Name) --out (Join-Path $Check 'build')
  if ($LASTEXITCODE -ne 0) { throw 'the example resume did not build' }
}

# ---- poppler ----

# poppler's pdftotext (tools\resume.py needs its -bbox-layout; Git for Windows ships xpdf's, which
# lacks it), as tools\resume.py picks it: the user's own first, setup's environment last. Single
# quotes in the Python: Windows PowerShell drops double quotes inside a native command's argument.
function Get-Pdftotext {
  $ErrorActionPreference = 'Continue'
  $p = & $PyExe @PyArgs -B -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import resume; print(resume.poppler_bin(''pdftotext'') or '''')' (Join-Path $Root 'tools')
  if ($LASTEXITCODE -eq 0 -and "$p".Trim()) { return "$p".Trim() }
}
$MambaVersion = '2.9.0-0'   # micromamba's release; the download is checked against the release's .sha256
$MambaRoot = Join-Path $HOME '.career-log\micromamba'   # micromamba and its package cache
$Mamba = Join-Path $MambaRoot 'micromamba.exe'
$PopplerEnv = Join-Path $HOME '.career-log\poppler'   # tools\resume.py's poppler_env
function Get-Micromamba {
  if (Test-Path $Mamba) { return $true }
  $ErrorActionPreference = 'Continue'
  $Url = "https://github.com/mamba-org/micromamba-releases/releases/download/$MambaVersion/micromamba-win-64"
  Write-Host "Downloading micromamba $MambaVersion (about 11 MB) into $MambaRoot"
  New-Item -ItemType Directory -Force -Path $MambaRoot | Out-Null
  curl.exe -fsSL --retry 5 -o "$Mamba.part" $Url
  $Sum = if ($LASTEXITCODE -eq 0) { curl.exe -fsSL --retry 5 "$Url.sha256" }
  if ($LASTEXITCODE -ne 0 -or -not $Sum -or (Get-FileHash "$Mamba.part" -Algorithm SHA256).Hash -ne ("$Sum".Trim() -split '\s+')[0]) {
    Write-Host 'micromamba: the download failed or does not match its checksum'
    Remove-Item "$Mamba.part" -ErrorAction SilentlyContinue
    return $false
  }
  Move-Item "$Mamba.part" $Mamba -Force
  return $true
}
# --no-rc with --override-channels -c conda-forge: conda-forge only, whatever a .condarc of the user's says
function Invoke-Mamba {
  $ErrorActionPreference = 'Continue'
  & $Mamba @args -y --no-rc -r $MambaRoot | Out-Host
  return $LASTEXITCODE -eq 0
}
function Install-Poppler {
  $Found = Get-Pdftotext
  if ($Found -and -not $Found.StartsWith("$PopplerEnv\", [StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "poppler: $Found (the user's own: used as it is)"
    Set-Machine 'poppler' '"own"'
    # micromamba serves only setup's environment: with no working one left, both go
    if ((Test-Path $MambaRoot) -and -not (Test-Path (Join-Path $PopplerEnv 'Library\bin\pdftotext.exe'))) {
      Remove-Item $MambaRoot, $PopplerEnv -Recurse -Force -ErrorAction SilentlyContinue
      if (-not (Test-Path $MambaRoot)) { Write-Host "removed ${MambaRoot}: setup has no poppler environment to manage" }
    }
    return
  }
  if (-not (Get-Micromamba)) {
    $script:UserLines += '  poppler: micromamba did not download (offline, or behind a proxy: set HTTPS_PROXY), so rerun this script; or install poppler yourself and set POPPLER_BIN to its bin folder'
    return
  }
  # An environment with its pdftotext in place is updated, even when that pdftotext did not answer
  # (a first run slowed by a virus scan, say); one an interrupted run left without it is made afresh
  if ($Found -or ((Test-Path (Join-Path $PopplerEnv 'conda-meta')) -and (Test-Path (Join-Path $PopplerEnv 'Library\bin\pdftotext.exe')))) {
    Write-Host "Updating poppler in $PopplerEnv (micromamba, conda-forge)"
    if (-not (Invoke-Mamba update -p $PopplerEnv --override-channels -c conda-forge --all)) {
      Write-Host 'poppler: the update failed; rerun this script to try again'
    }
  } else {
    Remove-Item $PopplerEnv -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Installing poppler into $PopplerEnv (micromamba, conda-forge)"
    # created empty, then filled: `create` with packages ends by telling the user to activate the
    # environment, which career-log never needs
    if (-not ((Invoke-Mamba create -p $PopplerEnv) -and (Invoke-Mamba install -p $PopplerEnv --override-channels -c conda-forge poppler))) {
      $script:UserLines += '  poppler: micromamba could not install it (its error is above), so rerun this script; or install poppler yourself and set POPPLER_BIN to its bin folder'
      return
    }
  }
  # the downloaded packages (about 300 MB): the environment has its own links or copies
  Remove-Item (Join-Path $MambaRoot 'pkgs') -Recurse -Force -ErrorAction SilentlyContinue
  if (Get-Pdftotext) { Set-Machine 'poppler' '"micromamba"' }
}

$UserLines = @()
Write-Host '== tinytex'
Install-TinyTeX
$Undecided = @()
foreach ($t in $Tools) {
  if (Test-Chosen $t 'true') {
    Write-Host "== $t"
    switch ($t) { 'playwright-cli' { Install-Playwright } }
  } elseif (-not (Test-Chosen $t 'false')) {
    $Undecided += $t
  }
}
if ($Undecided) { Write-Host "not chosen yet on this machine: $($Undecided -join ', ') (rerun with -Yes or -No for each)" }
if ($UserLines) { Write-Host "not installed by this script: do these yourself, then rerun it:"; $UserLines | ForEach-Object { Write-Host $_ } }
Write-Host '== tools\check.py setup'
& $PyExe @PyArgs -I (Join-Path $Root 'tools\check.py') setup
# A shell opened before this run keeps its old PATH: Python, Node and playwright-cli installed now are not on it
Write-Host "A shell opened before this run finds what it installed only after this line: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"
exit $(if ($UserLines) { 1 } else { 0 })
