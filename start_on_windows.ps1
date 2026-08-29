# -----------------------------------------------------------------------------
# Launcher paths and runtime locations
# -----------------------------------------------------------------------------
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$runtimeRoot = Join-Path $repoRoot 'runtimes'
$pythonDir = Join-Path $runtimeRoot 'python'
$pythonExe = Join-Path $pythonDir 'python.exe'
$pythonPth = Join-Path $pythonDir 'python314._pth'
$uvDir = Join-Path $runtimeRoot 'uv'
$uvExe = Join-Path $uvDir 'uv.exe'
$nodeDir = Join-Path $runtimeRoot 'nodejs'
$nodeExe = Join-Path $nodeDir 'node.exe'
$npmCmd = Join-Path $nodeDir 'npm.cmd'
$serverDir = Join-Path $repoRoot 'app\server'
$clientDir = Join-Path $repoRoot 'app\client'
$testsDir = Join-Path $repoRoot 'app\tests'
$venvDir = Join-Path $serverDir '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$envFile = Join-Path $repoRoot 'settings\.env'
$envExample = Join-Path $repoRoot 'settings\.env.example'
$runtimeCacheDir = Join-Path $runtimeRoot 'cache'
$testCacheDir = Join-Path $testsDir 'cache'
$pytestCacheDir = Join-Path $testCacheDir 'pytest'
$ruffCacheDir = Join-Path $testCacheDir 'ruff'

# -----------------------------------------------------------------------------
# Portable runtime versions and download sources
# -----------------------------------------------------------------------------
$pythonVersion = '3.14.2'
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$nodeVersion = '22.13.0'
$nodeArchiveName = "node-v$nodeVersion-win-x64"
$nodeUrl = "https://nodejs.org/dist/v$nodeVersion/$nodeArchiveName.zip"
$uvUrl = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    'https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-pc-windows-msvc.zip'
} else {
    'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip'
}

# -----------------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------------
function Write-Step([string]$Message) { Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info([string]$Message) { Write-Host "[INFO] $Message" -ForegroundColor DarkCyan }
function Write-Fatal([string]$Message) { Write-Host "[FATAL] $Message" -ForegroundColor Red }

# -----------------------------------------------------------------------------
# Filesystem and cache helpers
# -----------------------------------------------------------------------------
function Set-CacheEnvironment {
    $runtimeCachePaths = @(
        $runtimeCacheDir,
        (Join-Path $runtimeCacheDir 'npm'),
        (Join-Path $runtimeCacheDir 'pip'),
        (Join-Path $runtimeCacheDir 'python')
    )
    $testCachePaths = @(
        $testCacheDir,
        $pytestCacheDir,
        $ruffCacheDir,
        (Join-Path $testCacheDir 'mypy'),
        (Join-Path $testCacheDir 'playwright-browsers')
    )
    New-Item -ItemType Directory -Path ($runtimeCachePaths + $testCachePaths) -Force | Out-Null

    $env:UV_CACHE_DIR = $runtimeCacheDir
    $env:NPM_CONFIG_CACHE = Join-Path $runtimeCacheDir 'npm'
    $env:PIP_CACHE_DIR = Join-Path $runtimeCacheDir 'pip'
    $env:PYTHONPYCACHEPREFIX = Join-Path $runtimeCacheDir 'python'
    $env:RUFF_CACHE_DIR = $ruffCacheDir
    $env:MYPY_CACHE_DIR = Join-Path $testCacheDir 'mypy'
    $env:COVERAGE_FILE = Join-Path $testCacheDir '.coverage'
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $testCacheDir 'playwright-browsers'
}

function Remove-PathBestEffort([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $true }

    $item = $null
    try {
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    } catch {
        Write-Info "Skipped inaccessible path: $Path"
        return $false
    }

    if ($item.PSIsContainer) {
        $children = @()
        try {
            $children = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop)
        } catch {
            Write-Info "Skipped inaccessible children under: $Path"
        }
        foreach ($child in $children) {
            Remove-PathBestEffort $child.FullName | Out-Null
        }
    }

    try {
        Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
        return $true
    } catch {
        Write-Info "Skipped locked or protected path: $Path"
        return $false
    }
}

# -----------------------------------------------------------------------------
# Runtime setup helpers
# -----------------------------------------------------------------------------
function Invoke-DownloadAndExtract([string]$Uri, [string]$ArchivePath, [string]$DestinationPath) {
    $ProgressPreference = 'SilentlyContinue'
    New-Item -ItemType Directory -Path (Split-Path -Parent $ArchivePath), $DestinationPath -Force | Out-Null
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $ArchivePath
        Expand-Archive -LiteralPath $ArchivePath -DestinationPath $DestinationPath -Force
    } finally {
        Remove-Item -LiteralPath $ArchivePath -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-PatchPth([string]$Path) {
    (Get-Content -LiteralPath $Path) -replace '^#import site$', 'import site' | Set-Content -LiteralPath $Path -Encoding ASCII
}

function Invoke-CheckPyver([string]$PythonExe) {
    $version = & $PythonExe -c 'import platform; print(platform.python_version())'
    if ($LASTEXITCODE -ne 0) { throw "Portable Python validation failed." }
    return $version
}

function Invoke-FindUv([string]$SearchRoot) {
    $uv = Get-ChildItem -LiteralPath $SearchRoot -Recurse -Filter 'uv.exe' -File | Select-Object -First 1
    if (-not $uv) { throw "uv.exe not found in $SearchRoot" }
    return $uv.FullName
}

function Invoke-HealthCheck([string]$Url, [int]$TimeoutSeconds = 60) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) { return }
        } catch { }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    $ErrorActionPreference = $prevEap
    throw "Backend did not become healthy within $TimeoutSeconds seconds."
}

function Initialize-EnvironmentFile {
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        if (-not (Test-Path -LiteralPath $envExample -PathType Leaf)) { throw "Missing environment template: $envExample" }
        try {
            [System.IO.File]::Copy($envExample, $envFile, $false)
        } catch [System.IO.IOException] {
            if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) { throw }
        }
        Write-Ok 'Created settings\.env from settings\.env.example.'
    }
}

function Import-DotEnv {
    Initialize-EnvironmentFile
    $defaults = [ordered]@{
        FASTAPI_HOST = '127.0.0.1'
        FASTAPI_PORT = '8000'
        UI_HOST = '127.0.0.1'
        UI_PORT = '8001'
        RELOAD = 'false'
        BACKEND_LOGS_VISIBLE = 'true'
    }
    foreach ($entry in $defaults.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
    }
    foreach ($rawLine in Get-Content -LiteralPath $envFile) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#') -or $line.StartsWith(';') -or -not $line.Contains('=')) { continue }
        $key, $value = $line.Split('=', 2)
        $key = $key.Trim()
        $value = $value.Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($key) { [Environment]::SetEnvironmentVariable($key, $value, 'Process') }
    }
}

function Ensure-PortableRuntimes {
    New-Item -ItemType Directory -Path $runtimeRoot, $pythonDir, $uvDir, $nodeDir -Force | Out-Null

    Write-Step 'Setting up Python (embeddable) locally.'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        Invoke-DownloadAndExtract $pythonUrl (Join-Path $pythonDir 'python.zip') $pythonDir
    }
    if (Test-Path -LiteralPath $pythonPth) { Invoke-PatchPth $pythonPth }
    $pythonFound = Invoke-CheckPyver $pythonExe
    Write-Ok "Python ready: $pythonFound"

    Write-Step 'Installing uv (portable).'
    if (-not (Test-Path -LiteralPath $uvExe)) {
        Invoke-DownloadAndExtract $uvUrl (Join-Path $uvDir 'uv.zip') $uvDir
        $foundUv = Invoke-FindUv $uvDir
        if ([IO.Path]::GetFullPath($foundUv) -ne [IO.Path]::GetFullPath($uvExe)) {
            Copy-Item -LiteralPath $foundUv -Destination $uvExe -Force
        }
    }
    Write-Ok (& $uvExe --version)

    Write-Step 'Installing Node.js (portable).'
    $nodeNeedsInstall = $true
    if (Test-Path -LiteralPath $nodeExe) {
        $installedNodeVersion = (& $nodeExe --version).Trim()
        $nodeNeedsInstall = $installedNodeVersion -ne "v$nodeVersion" -or -not (Test-Path -LiteralPath $npmCmd)
        if (-not $nodeNeedsInstall) { Write-Info "Node.js $installedNodeVersion already matches the launcher baseline." }
    }
    if ($nodeNeedsInstall) {
        if (Test-Path -LiteralPath $nodeDir) { Remove-Item -LiteralPath $nodeDir -Recurse -Force }
        New-Item -ItemType Directory -Path $nodeDir -Force | Out-Null
        Invoke-DownloadAndExtract $nodeUrl (Join-Path $nodeDir 'node.zip') $nodeDir
        $nestedNodeDir = Join-Path $nodeDir $nodeArchiveName
        if (Test-Path -LiteralPath (Join-Path $nestedNodeDir 'node.exe')) {
            Get-ChildItem -LiteralPath $nestedNodeDir -Force | Move-Item -Destination $nodeDir -Force
            Remove-Item -LiteralPath $nestedNodeDir -Recurse -Force
        }
    }
    if (-not (Test-Path -LiteralPath $nodeExe) -or -not (Test-Path -LiteralPath $npmCmd)) {
        throw "Portable Node.js or npm is missing from $nodeDir."
    }
    $env:PATH = "$nodeDir;$env:PATH"
    Write-Ok "Node.js ready: $(& $nodeExe --version)"
}

# -----------------------------------------------------------------------------
# Dependency installation and frontend build
# -----------------------------------------------------------------------------
function Install-Dependencies {
    param(
        [switch]$PruneCache,
        [ValidateSet('Standard', 'Development')]
        [string]$InstallationType = 'Standard'
    )
    Import-DotEnv
    Ensure-PortableRuntimes

    Set-CacheEnvironment
    $env:UV_PROJECT_ENVIRONMENT = $venvDir
    $env:UV_LINK_MODE = 'copy'
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue

    Write-Step 'Installing Python dependencies with uv.'
    $syncArguments = @('sync', '--python', $pythonExe)
    if ($InstallationType -eq 'Development') { $syncArguments += '--all-extras' }
    Push-Location $serverDir
    try {
        & $uvExe @syncArguments
        if ($LASTEXITCODE -ne 0) {
            Write-Info 'Recreating a virtual environment that may reference an older repository location.'
            if (Test-Path -LiteralPath $venvDir) { Remove-Item -LiteralPath $venvDir -Recurse -Force }
            & $uvExe @syncArguments
        }
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }

    Write-Step 'Stopping any running frontend before updating dependencies.'
    Clear-Port ([int]$env:UI_PORT)
    Write-Step 'Installing frontend dependencies.'
    Push-Location $clientDir
    try {
        $frontendLock = Join-Path $clientDir 'package-lock.json'
        if (-not (Test-Path -LiteralPath $frontendLock)) {
            throw 'Frontend package-lock.json is required.'
        }
        & $npmCmd ci
        if ($LASTEXITCODE -ne 0) { throw "npm dependency installation failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }

    if ($PruneCache -and (Test-Path -LiteralPath $runtimeCacheDir)) {
        Write-Step 'Pruning runtime cache.'
        Remove-PathBestEffort $runtimeCacheDir | Out-Null
        Set-CacheEnvironment
    }
    Write-Ok 'Dependencies are installed.'
}

function Build-Frontend {
    Write-Step 'Building frontend.'
    Push-Location $clientDir
    try {
        & $npmCmd run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }
}

function Test-FrontendBuildReady {
    $frontendEntry = Join-Path $clientDir 'dist\index.html'
    $frontendAssets = Join-Path $clientDir 'dist\assets'
    if (-not (Test-Path -LiteralPath $frontendEntry -PathType Leaf) -or
        -not (Test-Path -LiteralPath $frontendAssets -PathType Container)) {
        return $false
    }
    if ((Get-Item -LiteralPath $frontendEntry).Length -eq 0) { return $false }
    if (-not (Get-ChildItem -LiteralPath $frontendAssets -File -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        return $false
    }
    return $true
}

function Test-DependenciesReady {
    $frontendPackage = Join-Path $clientDir 'package.json'
    $frontendLock = Join-Path $clientDir 'package-lock.json'
    $frontendModules = Join-Path $clientDir 'node_modules'
    $frontendInstallState = Join-Path $frontendModules '.package-lock.json'
    $frontendRunner = Join-Path $frontendModules '.bin\vite.cmd'
    $backendEntrypoint = Join-Path $serverDir 'app.py'

    if (-not (Test-Path -LiteralPath $pythonExe) -or
        -not (Test-Path -LiteralPath $uvExe) -or
        -not (Test-Path -LiteralPath $nodeExe) -or
        -not (Test-Path -LiteralPath $npmCmd) -or
        -not (Test-Path -LiteralPath $venvPython) -or
        -not (Test-Path -LiteralPath $backendEntrypoint) -or
        -not (Test-Path -LiteralPath $frontendPackage) -or
        -not (Test-Path -LiteralPath $frontendLock) -or
        -not (Test-Path -LiteralPath $frontendInstallState) -or
        -not (Test-Path -LiteralPath $frontendRunner)) {
        return $false
    }

    & $pythonExe --version *> $null
    if ($LASTEXITCODE -ne 0) { return $false }
    & $uvExe --version *> $null
    if ($LASTEXITCODE -ne 0) { return $false }
    & $nodeExe --version *> $null
    if ($LASTEXITCODE -ne 0) { return $false }
    & $venvPython -c 'import fastapi, uvicorn' *> $null
    if ($LASTEXITCODE -ne 0) { return $false }

    if (-not (Test-FrontendBuildReady)) { return $false }

    return $true
}

function Get-PortProcessIds([int]$Port) {
    $pattern = ":$Port\s+.*LISTENING\s+(\d+)$"
    return @(netstat.exe -ano -p TCP | ForEach-Object {
        if ($_ -match $pattern) { [int]$Matches[1] }
    } | Sort-Object -Unique)
}

function Clear-Port([int]$Port) {
    foreach ($processId in Get-PortProcessIds $Port) {
        Write-Info "Stopping PID $processId on port $Port."
        & taskkill.exe /PID $processId /T /F | Out-Null
    }
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if ((Get-PortProcessIds $Port).Count -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    throw "Port $Port is still occupied."
}

# -----------------------------------------------------------------------------
# Application lifecycle
# -----------------------------------------------------------------------------
function Start-Application {
    Import-DotEnv
    Ensure-PortableRuntimes
    Set-CacheEnvironment
    $env:UV_PROJECT_ENVIRONMENT = $venvDir
    $env:UV_LINK_MODE = 'copy'
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue
    if (-not (Test-DependenciesReady)) {
        Write-Step 'Required application environments or the frontend build are missing or unusable; recovering.'
        Install-Dependencies -InstallationType 'Standard'
        Build-Frontend
    }
    else {
        Write-Ok 'Application environments are ready; skipped dependency installation.'
    }
    $fastApiPort = [int]$env:FASTAPI_PORT
    $uiPort = [int]$env:UI_PORT
    Clear-Port $fastApiPort
    Clear-Port $uiPort

    $reloadArgument = if ($env:RELOAD -eq 'true') { ' --reload' } else { '' }
    $backendArgs = "-m uvicorn server.app:app --app-dir `"$($repoRoot)\app`" --host $($env:FASTAPI_HOST) --port $fastApiPort$reloadArgument --log-level info"
    Write-Step 'Launching backend.'
    if ($env:BACKEND_LOGS_VISIBLE -eq 'true') {
        $visibleBackendCommand = 'start "FAIRS Backend" /D "' + $repoRoot + '" cmd.exe /k ""' + $venvPython + '" ' + $backendArgs + '"'
        Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d', '/c', $visibleBackendCommand) -WorkingDirectory $repoRoot | Out-Null
        $backendProcess = $null
    } else {
        $backendProcess = Start-Process -FilePath $venvPython -ArgumentList $backendArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
    }

    $backendUrl = "http://$($env:FASTAPI_HOST):$fastApiPort"
    Write-Step "Waiting for backend readiness at $backendUrl/api/health."
    try {
        Invoke-HealthCheck "$backendUrl/api/health" 60
    } catch {
        if ($backendProcess) { & taskkill.exe /PID $backendProcess.Id /T /F | Out-Null }
        throw "Backend did not become healthy within 60 seconds."
    }
    $backendPid = (Get-PortProcessIds $fastApiPort | Select-Object -First 1)

    Write-Step 'Launching frontend preview.'
    $frontendArgs = "/c `"`"$npmCmd`" run preview -- --host $($env:UI_HOST) --port $uiPort --strictPort`""
    $frontendProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList $frontendArgs -WorkingDirectory $clientDir -WindowStyle Hidden -PassThru
    $uiUrl = "http://$($env:UI_HOST):$uiPort"
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $uiUrl -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    $frontendPid = (Get-PortProcessIds $uiPort | Select-Object -First 1)
    if (-not $frontendPid) {
        if ($backendPid) { & taskkill.exe /PID $backendPid /T /F | Out-Null }
        if (-not $frontendProcess.HasExited) { & taskkill.exe /PID $frontendProcess.Id /T /F | Out-Null }
        throw "Frontend preview did not become ready at $uiUrl."
    }

    Start-Process $uiUrl | Out-Null
    Write-Host ''
    Write-Ok 'FAIRS started successfully.'
    Write-Host "Backend: $backendUrl (PID $backendPid)"
    Write-Host "Frontend: $uiUrl (PID $frontendPid)"
}

# -----------------------------------------------------------------------------
# Database and validation operations
# -----------------------------------------------------------------------------
function Initialize-Database {
    Import-DotEnv
    Ensure-PortableRuntimes
    Set-CacheEnvironment
    $env:UV_PROJECT_ENVIRONMENT = $venvDir
    $previousPythonPath = $env:PYTHONPATH
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue
    $env:PYTHONPATH = Join-Path $repoRoot 'app'
    try {
        & $uvExe run --project $serverDir --python $pythonExe python (Join-Path $repoRoot 'app\scripts\initialize_database.py')
        if ($LASTEXITCODE -ne 0) { throw "Database initialization failed with exit code $LASTEXITCODE." }
    } finally {
        if ($null -eq $previousPythonPath) {
            Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONPATH = $previousPythonPath
        }
    }
    Write-Ok 'Database create/upgrade completed.'
}

function Invoke-TestSuite {
    Set-CacheEnvironment
    & (Join-Path $repoRoot 'app\tests\run_tests.bat')
    if ($LASTEXITCODE -ne 0) { throw "Test suite failed with exit code $LASTEXITCODE." }
    Write-Ok 'Test suite completed.'
}

# -----------------------------------------------------------------------------
# Cleanup and data management
# -----------------------------------------------------------------------------
function Confirm-Delete([string]$Description) {
    $confirmation = (Read-Host "Type DELETE to $Description").Trim()
    if ($confirmation -cne 'DELETE') {
        Write-Info "Operation cancelled. No data was deleted."
        return $false
    }
    return $true
}

function Remove-Logs {
    if (-not (Confirm-Delete 'remove application log files')) { return }

    $logDir = (Get-UserDataTargets).LogRoot
    Remove-UserLogFiles $logDir
    Write-Ok 'Log files removed.'
}

function Remove-UserLogFiles([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return }
    $logFiles = @(Get-ChildItem -LiteralPath $Path -Filter '*.log' -File -Recurse -Force -ErrorAction SilentlyContinue)
    foreach ($logFile in $logFiles) { Remove-PathBestEffort $logFile.FullName | Out-Null }
}

function Remove-PythonCaches {
    $pythonCacheDirs = @(Get-ChildItem -LiteralPath $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object Name -eq '__pycache__')
    foreach ($pythonCacheDir in $pythonCacheDirs) {
        Remove-PathBestEffort $pythonCacheDir.FullName | Out-Null
    }
}

function Clear-Cache {
    if (-not (Confirm-Delete 'clear Python, uv, and tool caches')) { return }

    foreach ($cachePath in @($runtimeCacheDir, $testCacheDir)) {
        Remove-PathBestEffort $cachePath | Out-Null
    }
    Remove-PythonCaches
    Set-CacheEnvironment
    Write-Ok 'Python, uv, and tool caches cleared. Locked or protected entries were skipped.'
}

function Resolve-LauncherPath([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) {
        return [IO.Path]::GetFullPath($Path)
    }
    return [IO.Path]::GetFullPath((Join-Path $repoRoot $Path))
}

function Get-UserDataTargets {
    Import-DotEnv

    $dataRoot = if ($env:FAIRS_DATA_DIR -and $env:FAIRS_DATA_DIR.Trim()) {
        Resolve-LauncherPath $env:FAIRS_DATA_DIR.Trim()
    } else {
        Join-Path $repoRoot 'app\resources'
    }
    $logRoot = Join-Path $dataRoot 'logs'

    return [pscustomobject]@{
        DatabaseFiles = @(
            (Join-Path $dataRoot 'database.db'),
            (Join-Path $dataRoot 'database.db-shm'),
            (Join-Path $dataRoot 'database.db-wal')
        )
        CheckpointRoot = Join-Path $dataRoot 'checkpoints'
        LogRoot = $logRoot
        ExternalDatabase = $env:EMBEDDED_DATABASE -eq 'false'
    }
}

function Remove-UserDataDirectory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return }
    $children = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        if ($child.Name -eq '.gitkeep') { continue }
        Remove-PathBestEffort $child.FullName | Out-Null
    }
}

function Remove-Checkpoints {
    if (-not (Confirm-Delete 'delete all saved checkpoints')) { return }

    $targets = Get-UserDataTargets
    Remove-UserDataDirectory $targets.CheckpointRoot
    New-Item -ItemType Directory -Path $targets.CheckpointRoot -Force | Out-Null
    Write-Ok 'All saved checkpoints were removed.'
}

function Remove-AllData {
    if (-not (Confirm-Delete 'delete local user data')) { return }

    $targets = Get-UserDataTargets
    foreach ($databaseFile in $targets.DatabaseFiles) {
        Remove-PathBestEffort $databaseFile | Out-Null
    }
    Remove-UserLogFiles $targets.LogRoot

    if (-not (Test-Path -LiteralPath $targets.LogRoot -PathType Container)) {
        New-Item -ItemType Directory -Path $targets.LogRoot -Force | Out-Null
    }
    if ($targets.ExternalDatabase) {
        Write-Info 'An external database is configured. Its remote data was not changed.'
    }
    Write-Ok 'Local database and user-generated log data were removed. Saved checkpoints were preserved.'
}

function Uninstall-Application {
    if (-not (Confirm-Delete 'remove local runtimes and build outputs')) { return }

    $paths = @(
        $runtimeRoot,
        (Join-Path $serverDir '.venv'),
        (Join-Path $repoRoot '.venv'),
        (Join-Path $clientDir 'node_modules'),
        (Join-Path $clientDir '.angular'),
        (Join-Path $clientDir 'dist')
    )
    foreach ($path in $paths) {
        Remove-PathBestEffort $path | Out-Null
    }
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    New-Item -ItemType File -Path (Join-Path $runtimeRoot '.gitkeep') -Force | Out-Null
    Remove-PythonCaches
    Write-Ok 'Application runtimes, dependencies, and build outputs removed. Dependency lockfiles and user data were preserved.'
}

# -----------------------------------------------------------------------------
# Repository maintenance
# -----------------------------------------------------------------------------
function Update-Application {
    Push-Location $repoRoot
    try {
        $currentBranch = (& git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Unable to determine the current Git branch.' }
        $branchLabel = if ($currentBranch) { $currentBranch } else { 'the detached checkout' }

        Write-Step "Pulling application updates from origin/main into $branchLabel."
        $gitOutput = @(& git pull origin main 2>&1)
        $gitExitCode = $LASTEXITCODE
        $gitOutput | ForEach-Object { Write-Host $_ }
        if ($gitExitCode -ne 0) { throw "Application update failed with exit code $gitExitCode." }
        Write-Ok 'Application update completed from origin/main.'
    } finally {
        Pop-Location
    }
}

function Check-ForUpdates {
    Push-Location $repoRoot
    try {
        & git show-ref --verify --quiet 'refs/remotes/origin/main'
        if ($LASTEXITCODE -ne 0) {
            Write-Info 'Update status is unavailable because no local origin/main reference exists.'
            Write-Info 'No fetch, download, or update was performed.'
            return
        }

        $currentBranch = (& git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Unable to determine the current Git branch.' }
        $branchLabel = if ($currentBranch) { $currentBranch } else { 'the detached checkout' }
        $incomingCount = [int]((& git rev-list --count 'HEAD..origin/main').Trim())
        if ($LASTEXITCODE -ne 0) { throw 'Unable to compare the checkout with origin/main.' }
        $localCount = [int]((& git rev-list --count 'origin/main..HEAD').Trim())
        if ($LASTEXITCODE -ne 0) { throw 'Unable to compare the checkout with origin/main.' }

        if ($incomingCount -gt 0) {
            Write-Info "Update available: origin/main has $incomingCount newer commit(s) than $branchLabel."
        } else {
            Write-Ok "No newer version is available from the local origin/main reference for $branchLabel."
        }
        if ($localCount -gt 0) {
            Write-Info "The current checkout also has $localCount commit(s) not present in origin/main."
        }
        Write-Info 'Status check only: no fetch, download, or update was performed.'
    } finally {
        Pop-Location
    }
}

# -----------------------------------------------------------------------------
# Menu presentation and dispatch
# -----------------------------------------------------------------------------
function Wait-ForMenu {
    if ([Console]::IsInputRedirected) { return }
    Write-Host ''
    Write-Host '  Press any key to return to the menu...' -ForegroundColor DarkGray
    [void][Console]::ReadKey($true)
}

function Write-MenuItem([string]$Number, [string]$Label, [string]$Description, [ConsoleColor]$Color = [ConsoleColor]::White) {
    Write-Host '  ' -NoNewline
    Write-Host (" {0} " -f $Number) -NoNewline -ForegroundColor Black -BackgroundColor $Color
    Write-Host "  $Label" -NoNewline -ForegroundColor $Color
    Write-Host "  $Description" -ForegroundColor DarkGray
}

function Read-InstallationType {
    $selection = (Read-Host 'Installation type [1=Development, 2=Standard]').Trim()
    switch ($selection) {
        '1' { return 'Development' }
        '2' { return 'Standard' }
        default { throw 'Invalid installation type. Enter 1 for Development or 2 for Standard.' }
    }
}

function Show-Menu {
    while ($true) {
        Clear-Host
        Write-Host ''
        Write-Host '  +---------------------------------------------------+' -ForegroundColor DarkCyan
        Write-Host '  |                                                   |' -ForegroundColor DarkCyan
        Write-Host '  |             FAIRS  /  ROULETTE PLAYER             |' -ForegroundColor Cyan
        Write-Host '  |          Local launcher and maintenance           |' -ForegroundColor DarkGray
        Write-Host '  |                                                   |' -ForegroundColor DarkCyan
        Write-Host '  +---------------------------------------------------+' -ForegroundColor DarkCyan
        Write-Host ''
        Write-Host '  START' -ForegroundColor DarkCyan
        Write-MenuItem '1' 'Launch application' 'Start the backend and player' Cyan
        Write-Host ''
        Write-Host '  APPLICATION UPDATES' -ForegroundColor DarkCyan
        Write-MenuItem '2' 'Update application' 'Pull application changes from the main branch' Yellow
        Write-MenuItem '3' 'Check for updates' 'Report local main-branch update status only' Yellow
        Write-Host ''
        Write-Host '  SETUP & VALIDATION' -ForegroundColor DarkCyan
        Write-MenuItem '4' 'Install / update dependencies' 'Prepare local runtimes and build the frontend' Yellow
        Write-MenuItem '5' 'Rebuild frontend' 'Build the frontend without updating dependencies' Yellow
        Write-MenuItem '6' 'Create / upgrade database' 'Create the selected database and apply migrations' Yellow
        Write-MenuItem '7' 'Run test suite' 'Execute automated checks' Yellow
        Write-Host ''
        Write-Host '  CLEANUP & DATA' -ForegroundColor DarkCyan
        Write-MenuItem '8' 'Remove logs' 'Delete application log files' DarkYellow
        Write-MenuItem '9' 'Clear cache' 'Remove Python, uv, and tool caches' DarkYellow
        Write-MenuItem '10' 'Remove checkpoints' 'Delete saved checkpoints only' Red
        Write-MenuItem '11' 'Remove All Data' 'Delete local database and logs, preserving checkpoints' Red
        Write-Host ''
        Write-Host '  APPLICATION FILES' -ForegroundColor DarkCyan
        Write-MenuItem '12' 'Uninstall application' 'Remove local runtimes and build outputs' Red
        Write-Host ''
        Write-Host '  -----------------------------------------------------' -ForegroundColor DarkCyan
        Write-MenuItem '13' 'Exit' 'Close this launcher' DarkGray
        Write-Host ''
        $selection = Read-Host '  Select an option (1-13)'
        if ($selection -notmatch '^(?:[1-9]|1[0-3])$') {
            Write-Fatal 'Invalid option. Select a number from 1 through 13.'
            Wait-ForMenu
            continue
        }
        if ($selection -eq '13') { break }
        try {
            switch ($selection) {
                '1' { Start-Application; exit 0 }
                '2' { Update-Application }
                '3' { Check-ForUpdates }
                '4' {
                    $installationType = Read-InstallationType
                    Install-Dependencies -PruneCache -InstallationType $installationType
                    Build-Frontend
                    Initialize-Database
                }
                '5' { Build-Frontend }
                '6' { Initialize-Database }
                '7' { Invoke-TestSuite }
                '8' { Remove-Logs }
                '9' { Clear-Cache }
                '10' { Remove-Checkpoints }
                '11' { Remove-AllData }
                '12' { Uninstall-Application }
            }
            if ([Console]::IsInputRedirected) { break }
        } catch {
            Write-Fatal $_.Exception.Message
            if ([Console]::IsInputRedirected) { exit 1 }
        }
        Wait-ForMenu
    }
}

Set-CacheEnvironment
Show-Menu
