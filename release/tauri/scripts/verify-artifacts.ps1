[CmdletBinding()]
param([string]$ArtifactRoot = '')
$ErrorActionPreference = 'Stop'
$root = if ($ArtifactRoot) { [IO.Path]::GetFullPath($ArtifactRoot) } else { Join-Path $PSScriptRoot '..\..\windows' }
$zip = Join-Path $root 'FAIRS-v2.4.0-windows-x64-portable.zip'
if (-not (Test-Path $zip)) { throw "Portable ZIP not found: $zip" }
$temp = Join-Path ([IO.Path]::GetTempPath()) ("fairs-verify-" + [guid]::NewGuid())
Expand-Archive $zip $temp
foreach ($required in @('FAIRS.exe','portable.flag','runtime')) { if (-not (Test-Path (Join-Path $temp $required))) { throw "Missing required portable entry: $required" } }
$forbidden = Get-ChildItem $temp -Recurse -File | Where-Object { $_.FullName -match '(?i)(node_modules|\.venv|database\.db|\.env|__pycache__|\.pyc$|\.whl$|\.zip$)' }
if ($forbidden) { throw "Forbidden portable content: $($forbidden.FullName -join ', ')" }
Remove-Item $temp -Recurse -Force
Write-Host '[OK] Portable artifact contents verified.'
