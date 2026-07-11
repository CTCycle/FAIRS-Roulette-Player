[CmdletBinding()]
param([string]$ArtifactRoot = '')
$ErrorActionPreference = 'Stop'
$root = if ($ArtifactRoot) { [IO.Path]::GetFullPath($ArtifactRoot) } else { Join-Path $PSScriptRoot '..\..\windows' }
$zip = Join-Path $root 'FAIRS-v2.4.0-windows-x64-portable.zip'
$temp = Join-Path ([IO.Path]::GetTempPath()) ("fairs-smoke-" + [guid]::NewGuid())
Expand-Archive $zip $temp
$process = Start-Process (Join-Path $temp 'FAIRS.exe') -WorkingDirectory $temp -PassThru
try {
    Start-Sleep -Seconds 5
    if ($process.HasExited) { throw "Portable executable exited with code $($process.ExitCode)." }
    Write-Host '[OK] Portable process remained running during smoke test.'
} finally { if (-not $process.HasExited) { taskkill.exe /PID $process.Id /T /F | Out-Null }; Remove-Item $temp -Recurse -Force }
