[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$tauriDir = Join-Path $repoRoot "app\src-tauri"
$pathsToRemove = @(
  (Join-Path $tauriDir "target"),
  (Join-Path $tauriDir "bundle"),
  (Join-Path $tauriDir "gen"),
  (Join-Path $repoRoot "release\windows")
)

foreach ($path in $pathsToRemove) {
  if (Test-Path $path) {
    Remove-Item -LiteralPath $path -Recurse -Force
    Write-Host "[OK] Removed: $path"
  } else {
    Write-Host "[INFO] Not found: $path"
  }
}

Write-Host "[DONE] Build cleanup complete."
