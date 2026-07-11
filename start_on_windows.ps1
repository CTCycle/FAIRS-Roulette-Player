[CmdletBinding()]
param([Parameter(Position = 0)][ValidateSet('menu','launch','install','init-db','uninstall','build-desktop','clean-desktop','test','clean-logs','clean-cache')][string]$Command = 'menu')

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$runtimeRoot = Join-Path $repoRoot 'runtimes'
$appDir = Join-Path $repoRoot 'app'
$serverDir = Join-Path $repoRoot 'app\server'
$clientDir = Join-Path $repoRoot 'app\client'
$envFile = Join-Path $repoRoot 'settings\.env'
$stateFile = Join-Path $runtimeRoot '.installation-state.json'

function Read-RuntimeManifest {
    $path = Join-Path $repoRoot 'release\runtime-manifest.json'
    if (-not (Test-Path $path)) { return [pscustomobject]@{} }
    return Get-Content -Raw $path | ConvertFrom-Json
}

function Initialize-LocalConfiguration {
    $example = Join-Path $repoRoot 'settings\.env.example'
    if (-not (Test-Path $envFile)) { Copy-Item $example $envFile; Write-Host '[OK] Created settings\.env' }
}

function Get-Tool([string]$name, [string]$fallback) {
    $candidate = Join-Path $runtimeRoot $fallback
    if (Test-Path $candidate) { return $candidate }
    $command = Get-Command "$name.cmd" -ErrorAction SilentlyContinue
    if (-not $command) { $command = Get-Command "$name.exe" -ErrorAction SilentlyContinue }
    if (-not $command) { $command = Get-Command $name -ErrorAction SilentlyContinue }
    if ($command) { return $command.Source }
    throw "Required tool '$name' was not found. Install it or place it under runtimes."
}

function Get-FileSha256([string]$path) {
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($path)
    try {
        return ([System.BitConverter]::ToString($sha256.ComputeHash($stream))).Replace('-', '')
    } finally {
        $stream.Dispose()
        $sha256.Dispose()
    }
}

function Get-InputHashes {
    $manifest = Join-Path $repoRoot 'release\runtime-manifest.json'
    $lockfiles = @($manifest, (Join-Path $serverDir 'uv.lock'), (Join-Path $clientDir 'package-lock.json'))
    $result = [ordered]@{}
    foreach ($file in $lockfiles) {
        if (-not (Test-Path $file)) { $result[$file] = $null } else { $result[$file] = Get-FileSha256 $file }
    }
    return $result
}

function Test-EnvironmentCurrent {
    if (-not (Test-Path $stateFile)) { return $false }
    $saved = Get-Content -Raw $stateFile | ConvertFrom-Json
    $current = Get-InputHashes
    foreach ($key in $current.Keys) { if ($saved.$key -ne $current[$key]) { return $false } }
    return (Test-Path (Join-Path $serverDir '.venv\Scripts\python.exe')) -and (Test-Path (Join-Path $clientDir 'node_modules'))
}

function Sync-BackendDependencies {
    $uv = Get-Tool 'uv' 'uv\uv.exe'
    & $uv sync --project $serverDir --extra test --frozen
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency sync failed with exit code $LASTEXITCODE." }
}

function Sync-FrontendDependencies {
    $npm = Get-Tool 'npm' 'nodejs\npm.cmd'
    if (Test-Path (Join-Path $clientDir 'package-lock.json')) { & $npm --prefix $clientDir ci } else { & $npm --prefix $clientDir install }
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency sync failed with exit code $LASTEXITCODE." }
}

function Install-DeveloperEnvironment {
    Initialize-LocalConfiguration
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    if (-not (Test-EnvironmentCurrent)) {
        Sync-BackendDependencies
        Sync-FrontendDependencies
        Get-InputHashes | ConvertTo-Json | Set-Content -Encoding UTF8 $stateFile
        Write-Host '[OK] Developer environment installed or refreshed.'
    } else { Write-Host '[OK] Developer environment is current.' }
}

function Wait-Health([string]$url, [int]$timeoutSeconds = 60) {
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    do {
        try { $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2; if ($health.application -eq 'FAIRS') { return $true } } catch { }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Stop-TrackedProcess([System.Diagnostics.Process]$process) {
    if ($null -ne $process -and -not $process.HasExited) {
        & taskkill.exe /PID $process.Id /T /F | Out-Null
    }
}

function Start-DeveloperMode {
    Install-DeveloperEnvironment
    $python = Join-Path $serverDir '.venv\Scripts\python.exe'
    $npm = Get-Tool 'npm' 'nodejs\npm.cmd'
    $frontendStdout = Join-Path $runtimeRoot 'frontend.stdout.log'
    $frontendStderr = Join-Path $runtimeRoot 'frontend.stderr.log'
    $backend = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','server.app:app','--host','127.0.0.1','--port','8000','--reload' -WorkingDirectory $appDir -NoNewWindow -PassThru
    $frontend = Start-Process -FilePath $npm -ArgumentList 'run','dev','--','--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory $clientDir -WindowStyle Hidden -RedirectStandardOutput $frontendStdout -RedirectStandardError $frontendStderr -PassThru
    try {
        if (-not (Wait-Health 'http://127.0.0.1:8000')) { throw 'Backend did not become ready at http://127.0.0.1:8000.' }
        Start-Process 'http://127.0.0.1:5173' | Out-Null
        Write-Host '[READY] FAIRS developer mode: http://127.0.0.1:5173'
        Write-Host 'Press Ctrl+C to stop the processes created by this launcher.'
        while (-not $backend.HasExited -and -not $frontend.HasExited) { Start-Sleep -Seconds 1 }
    } finally { Stop-TrackedProcess $frontend; Stop-TrackedProcess $backend }
}

function Initialize-Database { Install-DeveloperEnvironment; & (Join-Path $serverDir '.venv\Scripts\python.exe') (Join-Path $repoRoot 'app\scripts\initialize_database.py'); if ($LASTEXITCODE) { throw 'Database initialization failed.' } }
function Uninstall-DeveloperEnvironment { foreach ($path in @((Join-Path $runtimeRoot 'uv'),(Join-Path $runtimeRoot 'nodejs'),(Join-Path $serverDir '.venv'),(Join-Path $clientDir 'node_modules'),(Join-Path $clientDir 'dist'),$stateFile)) { if (Test-Path $path) { Remove-Item -LiteralPath $path -Recurse -Force } }; Write-Host '[OK] Local developer environment removed.' }
function Invoke-TestSuite { & (Join-Path $repoRoot 'app\tests\run_tests.bat'); if ($LASTEXITCODE) { throw 'Test suite failed.' } }
function Clear-Logs { $path = Join-Path $repoRoot 'app\resources\logs'; if (Test-Path $path) { Get-ChildItem $path -File | Remove-Item -Force }; Write-Host '[OK] Logs cleared.' }
function Clear-Caches { Get-ChildItem $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue | Where-Object Name -in @('__pycache__','.pytest_cache','.ruff_cache') | Remove-Item -Recurse -Force; Write-Host '[OK] Caches cleared.' }
function Clear-DesktopArtifacts { & (Join-Path $repoRoot 'release\tauri\scripts\clean-tauri-build.ps1') }
function Invoke-DesktopBuild { & (Join-Path $repoRoot 'release\tauri\build_with_tauri.bat'); if ($LASTEXITCODE) { throw 'Desktop build failed.' } }

function Show-MainMenu {
    do {
        Write-Host "`nFAIRS developer tools`n1. Launch developer mode`n2. Install or update developer environment`n3. Initialize database`n4. Uninstall local developer environment`n5. Build Windows desktop release`n6. Remove desktop build artifacts`n7. Run test suite`n8. Remove logs`n9. Clear caches`n10. Exit"
        $choice = Read-Host 'Select an option'
        $map = @{ '1'='launch';'2'='install';'3'='init-db';'4'='uninstall';'5'='build-desktop';'6'='clean-desktop';'7'='test';'8'='clean-logs';'9'='clean-cache';'10'='exit' }
        if ($map[$choice] -eq 'exit') { return }
        if ($map[$choice]) { & $PSCommandPath $map[$choice] }
    } while ($true)
}

switch ($Command) {
    'menu' { Show-MainMenu }
    'launch' { Start-DeveloperMode }
    'install' { Install-DeveloperEnvironment }
    'init-db' { Initialize-Database }
    'uninstall' { Uninstall-DeveloperEnvironment }
    'build-desktop' { Invoke-DesktopBuild }
    'clean-desktop' { Clear-DesktopArtifacts }
    'test' { Invoke-TestSuite }
    'clean-logs' { Clear-Logs }
    'clean-cache' { Clear-Caches }
}
