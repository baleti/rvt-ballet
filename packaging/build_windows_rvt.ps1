# Build the per-user Windows installer (no admin): stage app files, embeddable Python + dependencies, then Inno Setup.
# usage (PowerShell, from the repo root):  .\packaging\build_windows_rvt.ps1 [-PyVersion 3.12.10]
param([string]$PyVersion = '3.12.10', [switch]$SkipStage)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'dist'
if (-not $SkipStage) { python "$PSScriptRoot\stage_rvt.py" $dist }
$py = Join-Path $dist 'python'
if (-not (Test-Path $py)) {
  $zip = Join-Path $dist 'python-embed.zip'
  Invoke-WebRequest "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip" -OutFile $zip
  Expand-Archive $zip $py
  $pth = Get-ChildItem $py -Filter 'python*._pth' | Select-Object -First 1
  Add-Content $pth.FullName "`r`n..\app`r`nLib\site-packages`r`nimport site"
  Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile (Join-Path $dist 'get-pip.py')
  & "$py\python.exe" (Join-Path $dist 'get-pip.py') --no-warn-script-location
}
& "$py\python.exe" -m pip install --no-warn-script-location -r (Join-Path $dist 'requirements.txt')
$iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) { $iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" }
& $iscc "$PSScriptRoot\rvt-ballet.iss"
