[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$client = Join-Path $repoRoot 'app\client'
$tauri = Join-Path $repoRoot 'app\src-tauri'
$runtime = Join-Path $tauri 'runtime'
$output = Join-Path $repoRoot 'release\windows'

if (-not (Test-Path (Join-Path $client 'package-lock.json'))) { throw 'Missing app/client/package-lock.json.' }
if (-not (Test-Path (Join-Path $repoRoot 'app\server\uv.lock'))) { throw 'Missing app/server/uv.lock.' }
if ((git -C $repoRoot status --porcelain)) { throw 'Release build requires a clean checkout.' }

try {
    & npm --prefix $client ci
    if ($LASTEXITCODE) { throw 'npm ci failed.' }
    & npm --prefix $client run build
    if ($LASTEXITCODE) { throw 'Frontend build failed.' }
    & (Join-Path $PSScriptRoot 'scripts\prepare-runtime.ps1')
    if ($LASTEXITCODE) { throw 'Embedded runtime preparation failed.' }
    & npm --prefix $client run tauri:build
    if ($LASTEXITCODE) { throw 'Tauri build failed.' }
    & (Join-Path $PSScriptRoot 'scripts\export-windows-artifacts.ps1')
    if ($LASTEXITCODE) { throw 'Artifact export failed.' }
} finally {
    if (Test-Path $runtime) { Remove-Item $runtime -Recurse -Force }
}
