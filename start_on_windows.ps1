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
$venvDir = Join-Path $serverDir '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$envFile = Join-Path $repoRoot 'settings\.env'
$envExample = Join-Path $repoRoot 'settings\.env.example'
$uvCacheDir = Join-Path $runtimeRoot '.uv-cache'


$pythonVersion = '3.14.2'
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$nodeVersion = '22.12.0'
$nodeArchiveName = "node-v$nodeVersion-win-x64"
$nodeUrl = "https://nodejs.org/dist/v$nodeVersion/$nodeArchiveName.zip"
$uvUrl = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    'https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-pc-windows-msvc.zip'
} else {
    'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip'
}

function Write-Step([string]$Message) { Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info([string]$Message) { Write-Host "[INFO] $Message" -ForegroundColor DarkCyan }
function Write-Fatal([string]$Message) { Write-Host "[FATAL] $Message" -ForegroundColor Red }

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
    if (-not (Test-Path -LiteralPath $envFile)) {
        if (-not (Test-Path -LiteralPath $envExample)) { throw "Missing environment template: $envExample" }
        Copy-Item -LiteralPath $envExample -Destination $envFile
        Write-Ok 'Created settings\.env from settings\.env.example.'
    }
}

function Import-DotEnv {
    $defaults = [ordered]@{
        FASTAPI_HOST = '127.0.0.1'
        FASTAPI_PORT = '8000'
        UI_HOST = '127.0.0.1'
        UI_PORT = '8001'
        RELOAD = 'false'
        OPTIONAL_DEPENDENCIES = 'false'
        BACKEND_LOGS_VISIBLE = 'true'
        ALWAYS_REBUILD = 'true'
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
    if (-not (Test-Path -LiteralPath $nodeExe)) {
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

function Install-Dependencies([switch]$PruneCache) {
    Initialize-EnvironmentFile
    Import-DotEnv
    Ensure-PortableRuntimes

    $env:UV_CACHE_DIR = $uvCacheDir
    $env:UV_PROJECT_ENVIRONMENT = $venvDir
    $env:UV_LINK_MODE = 'copy'
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue

    Write-Step 'Installing Python dependencies with uv.'
    $syncArguments = @('sync', '--python', $pythonExe)
    if ($env:OPTIONAL_DEPENDENCIES -eq 'true') { $syncArguments += '--all-extras' }
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

    Write-Step 'Installing frontend dependencies.'
    Push-Location $clientDir
    try {
        if (Test-Path -LiteralPath (Join-Path $clientDir 'package-lock.json')) { & $npmCmd ci } else { & $npmCmd install }
        if ($LASTEXITCODE -ne 0) { throw "npm dependency installation failed with exit code $LASTEXITCODE." }
        if ($env:ALWAYS_REBUILD -eq 'true') {
            Write-Step 'Building frontend.'
            & $npmCmd run build
            if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code $LASTEXITCODE." }
        } else {
            Write-Info 'Skipping frontend build because ALWAYS_REBUILD=false.'
        }
    } finally { Pop-Location }

    if ($PruneCache -and (Test-Path -LiteralPath $uvCacheDir)) {
        Write-Step 'Pruning uv cache.'
        Remove-Item -LiteralPath $uvCacheDir -Recurse -Force
    }
    Write-Ok 'Dependencies are installed and the frontend build is ready.'
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

function Start-Application {
    Install-Dependencies
    Import-DotEnv
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

function Initialize-Database {
    Initialize-EnvironmentFile
    Import-DotEnv
    Ensure-PortableRuntimes
    $env:UV_CACHE_DIR = $uvCacheDir
    $env:UV_PROJECT_ENVIRONMENT = $venvDir
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue
    & $uvExe run --project $serverDir --python $pythonExe python (Join-Path $repoRoot 'app\scripts\initialize_database.py') --drop-existing --seed-catalogs --force-reseed-catalogs
    if ($LASTEXITCODE -ne 0) { throw "Database initialization failed with exit code $LASTEXITCODE." }
    Write-Ok 'Database initialization completed.'
}

function Invoke-TestSuite {
    & (Join-Path $repoRoot 'app\tests\run_tests.bat')
    if ($LASTEXITCODE -ne 0) { throw "Test suite failed with exit code $LASTEXITCODE." }
    Write-Ok 'Test suite completed.'
}

function Remove-Logs {
    $logDir = Join-Path $repoRoot 'app\resources\logs'
    if (Test-Path -LiteralPath $logDir) { Get-ChildItem -LiteralPath $logDir -Filter '*.log' -File -Recurse | Remove-Item -Force }
    Write-Ok 'Log files removed.'
}

function Remove-PythonCaches {
    Get-ChildItem -LiteralPath $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object Name -eq '__pycache__' |
        Remove-Item -Recurse -Force
}

function Clear-Cache {
    Remove-PythonCaches
    if (Test-Path -LiteralPath $uvCacheDir) { Remove-Item -LiteralPath $uvCacheDir -Recurse -Force }
    Write-Ok 'Python and uv caches cleared.'
}

function Uninstall-Application {
    $paths = @(
        $runtimeRoot,
        (Join-Path $serverDir '.venv'),
        (Join-Path $repoRoot '.venv'),
        (Join-Path $clientDir 'node_modules'),
        (Join-Path $clientDir '.angular'),
        (Join-Path $clientDir 'dist'),
        (Join-Path $clientDir 'package-lock.json'),
        (Join-Path $serverDir 'uv.lock'),
        (Join-Path $repoRoot 'uv.lock')
    )
    foreach ($path in $paths) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }
    Remove-PythonCaches
    Write-Ok 'Application runtimes, dependencies, build outputs, and lockfiles removed. User data was preserved.'
}

function Wait-ForMenu {
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
        Write-Host '  SETUP & MAINTENANCE' -ForegroundColor DarkCyan
        Write-MenuItem '2' 'Install / update dependencies' 'Prepare local runtimes and build the frontend' Yellow
        Write-MenuItem '3' 'Initialize database' 'Create and seed application data' Yellow
        Write-MenuItem '4' 'Run test suite' 'Execute automated checks' Yellow
        Write-Host ''
        Write-Host '  CLEANUP' -ForegroundColor DarkCyan
        Write-MenuItem '5' 'Remove logs' 'Delete application log files' DarkYellow
        Write-MenuItem '6' 'Clear cache' 'Remove Python and uv caches' DarkYellow
        Write-MenuItem '7' 'Uninstall application' 'Remove local runtimes and build outputs' Red
        Write-Host ''
        Write-Host '  -----------------------------------------------------' -ForegroundColor DarkCyan
        Write-MenuItem '8' 'Exit' 'Close this launcher' DarkGray
        Write-Host ''
        $selection = Read-Host '  Select an option (1-8)'
        if ($selection -notmatch '^[1-8]$') {
            Write-Fatal 'Invalid option. Select a number from 1 through 8.'
            Wait-ForMenu
            continue
        }
        if ($selection -eq '8') { break }
        try {
            switch ($selection) {
                '1' { Start-Application; exit 0 }
                '2' { Install-Dependencies -PruneCache }
                '3' { Initialize-Database }
                '4' { Invoke-TestSuite }
                '5' { Remove-Logs }
                '6' { Clear-Cache }
                '7' { Uninstall-Application }
            }
        } catch {
            Write-Fatal $_.Exception.Message
        }
        Wait-ForMenu
    }
}

Show-Menu
