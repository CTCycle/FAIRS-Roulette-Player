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
$script:NextProgressId = 1
$script:ActiveProgressActivities = [Collections.Generic.Dictionary[int, string]]::new()
$script:OwnedProcessIds = [Collections.Generic.HashSet[int]]::new()
$script:OwnedProcessRecords = @{}
$script:LauncherInteractive = -not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected

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
function Write-Step([string]$Message) { Clear-LauncherProgress; Write-Host "[STEP] $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Clear-LauncherProgress; Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info([string]$Message) { Clear-LauncherProgress; Write-Host "[INFO] $Message" -ForegroundColor DarkCyan }
function Write-Fatal([string]$Message) { Clear-LauncherProgress; Write-Host "[FATAL] $Message" -ForegroundColor Red }
function Test-InteractiveConsole {
    return $script:LauncherInteractive
}

function Start-LauncherProgress {
    param([Parameter(Mandatory)][string]$Activity, [Parameter(Mandatory)][string]$Status)
    $id = $script:NextProgressId++
    $script:ActiveProgressActivities[$id] = $Activity
    if (Test-InteractiveConsole) {
        Write-Progress -Id $id -Activity $Activity -Status $Status
    }
    return $id
}

function Update-LauncherProgress {
    param(
        [Parameter(Mandatory)][int]$Id,
        [Parameter(Mandatory)][string]$Activity,
        [Parameter(Mandatory)][string]$Status,
        [Nullable[int]]$PercentComplete
    )
    if (-not $script:ActiveProgressActivities.ContainsKey($Id)) { return }
    $activity = $script:ActiveProgressActivities[$Id]
    $progress = @{ Id = $Id; Activity = $activity; Status = $Status }
    if ($null -ne $PercentComplete) { $progress.PercentComplete = $PercentComplete }
    if (Test-InteractiveConsole) {
        Write-Progress @progress
    }
}

function Complete-LauncherProgress([int]$Id) {
    if ($script:ActiveProgressActivities.ContainsKey($Id)) {
        $activity = $script:ActiveProgressActivities[$Id]
        try {
            if (Test-InteractiveConsole) { Write-Progress -Id $Id -Activity $activity -Completed }
        }
        finally {
            [void]$script:ActiveProgressActivities.Remove($Id)
        }
    }
}

function Clear-LauncherProgress {
    foreach ($id in @($script:ActiveProgressActivities.Keys)) {
        Complete-LauncherProgress -Id $id
    }
}

function Invoke-TrackedLauncherAction {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Action
    )
    Write-Step "Starting $Name"
    try {
        & $Action
        Write-Ok "$Name completed"
    }
    catch {
        Write-Fatal "$Name failed: $($_.Exception.Message)"
        throw
    }
    finally {
        Clear-LauncherProgress
    }
}

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

function Remove-LauncherPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path,
        [switch]$KeepRoot,
        [string[]]$PreserveNames = @('.gitkeep'),
        [switch]$Strict,
        [switch]$WhatIf,
        [string]$Activity = 'FAIRS: remove files'
    )

    $fullPath = [IO.Path]::GetFullPath($Path)
    $removed = [Collections.Generic.List[string]]::new()
    $skipped = [Collections.Generic.List[string]]::new()
    $preserved = [Collections.Generic.List[string]]::new()
    $enumerationErrors = [Collections.Generic.List[string]]::new()
    $result = [ordered]@{
        Target = $fullPath
        Path = $fullPath
        Planned = 0
        PlannedCount = 0
        Removed = 0
        RemovedCount = 0
        RemovedPaths = $removed
        Preserved = 0
        PreservedEntries = $preserved
        Skipped = 0
        SkippedPaths = $skipped
        EnumerationErrors = $enumerationErrors
        WhatIf = [bool]$WhatIf
    }
    try {
        $item = Get-Item -LiteralPath $fullPath -Force -ErrorAction Stop
    }
    catch {
        if ($_.CategoryInfo.Category -eq [System.Management.Automation.ErrorCategory]::ObjectNotFound) { return [pscustomobject]$result }
        [void]$enumerationErrors.Add("$fullPath ($($_.Exception.Message))")
        Write-Info "Skipped inaccessible path: $fullPath ($($_.Exception.Message))"
        if ($Strict) { throw }
        return [pscustomobject]$result
    }
    $entries = if ($item.PSIsContainer) {
        $errors = @()
        $found = @(Get-ChildItem -LiteralPath $item.FullName -Force -Recurse -ErrorAction SilentlyContinue -ErrorVariable errors)
        foreach ($errorRecord in $errors) {
            [void]$enumerationErrors.Add("$($errorRecord.Exception.Message)")
            Write-Info "Skipped inaccessible path below $fullPath ($($errorRecord.Exception.Message))"
        }
        if (-not $KeepRoot) { $found += $item }
        $found
    } else { @($item) }
    $protectedDirectories = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $preservedPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in @($entries)) {
        if ($entry.Name -in $PreserveNames) {
            [void]$preservedPaths.Add($entry.FullName)
            [void]$preserved.Add($entry.FullName)
            $ancestor = [IO.Path]::GetDirectoryName($entry.FullName)
            while ($ancestor -and $ancestor.StartsWith($item.FullName.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
                [void]$protectedDirectories.Add($ancestor)
                $ancestor = [IO.Path]::GetDirectoryName($ancestor)
            }
        }
    }
    $candidates = @($entries |
        Where-Object { -not $preservedPaths.Contains($_.FullName) -and -not $protectedDirectories.Contains($_.FullName) } |
        Sort-Object @{ Expression = { $_.FullName.Length }; Descending = $true }, @{ Expression = { $_.FullName.ToUpperInvariant() }; Descending = $false })
    $result.Planned = $candidates.Count
    $result.PlannedCount = $candidates.Count
    $result.Preserved = $preserved.Count
    $progressId = $null
    try {
        if ($candidates.Count -gt 0) { $progressId = Start-LauncherProgress -Activity $Activity -Status "0 of $($candidates.Count) items" }
        for ($index = 0; $index -lt $candidates.Count; $index++) {
            $entry = $candidates[$index]
            if ($null -ne $progressId) {
                Update-LauncherProgress -Id $progressId -Activity $Activity -Status "$($index + 1) of $($candidates.Count): $($entry.Name)" -PercentComplete ([int](($index + 1) * 100 / [Math]::Max(1, $candidates.Count)))
            }
            if ($WhatIf) { continue }
            try {
                Remove-Item -LiteralPath $entry.FullName -Force -Confirm:$false -ErrorAction Stop
                [void]$removed.Add($entry.FullName)
            }
            catch {
                [void]$skipped.Add("$($entry.FullName) ($($_.Exception.Message))")
                Write-Info "Skipped locked or protected path: $($entry.FullName) ($($_.Exception.Message))"
            }
        }
    }
    finally {
        if ($null -ne $progressId) { Complete-LauncherProgress -Id $progressId }
    }
    $result.Removed = $removed.Count
    $result.RemovedCount = $removed.Count
    $result.Skipped = $skipped.Count
    if ($Strict -and ($skipped.Count -gt 0 -or $enumerationErrors.Count -gt 0)) {
        throw "Removal of '$fullPath' was incomplete. Skipped $($skipped.Count) item(s) and encountered $($enumerationErrors.Count) enumeration error(s)."
    }
    return [pscustomobject]$result
}

function Remove-PathBestEffort([string]$Path) {
    $result = Remove-LauncherPath -Path $Path -Activity "FAIRS: remove $([IO.Path]::GetFileName($Path))"
    return $result.Skipped -eq 0 -and $result.EnumerationErrors.Count -eq 0
}

# -----------------------------------------------------------------------------
# Runtime setup helpers
# -----------------------------------------------------------------------------
function Invoke-DownloadAndExtract([string]$Uri, [string]$ArchivePath, [string]$DestinationPath) {
    $previousProgressPreference = $ProgressPreference
    $activity = "FAIRS: download and extract $([IO.Path]::GetFileName($ArchivePath))"
    $progressId = Start-LauncherProgress -Activity $activity -Status "Downloading $Uri"
    try {
        $ProgressPreference = 'SilentlyContinue'
        New-Item -ItemType Directory -Path (Split-Path -Parent $ArchivePath), $DestinationPath -Force | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $ArchivePath
        $ProgressPreference = $previousProgressPreference
        Update-LauncherProgress -Id $progressId -Activity $activity -Status 'Extracting archive'
        Expand-Archive -LiteralPath $ArchivePath -DestinationPath $DestinationPath -Force
    } finally {
        $ProgressPreference = $previousProgressPreference
        Remove-Item -LiteralPath $ArchivePath -Force -ErrorAction SilentlyContinue
        Complete-LauncherProgress $progressId
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
    $activity = "FAIRS: wait for health $Url"
    $progressId = Start-LauncherProgress -Activity $activity -Status "Waiting up to $TimeoutSeconds seconds"
    try {
        do {
            $elapsed = [int](([DateTime]::Now - $deadline.AddSeconds(-$TimeoutSeconds)).TotalSeconds)
            Update-LauncherProgress -Id $progressId -Activity $activity -Status "Waiting for healthy response; ${elapsed}s elapsed"
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) { return }
            } catch { }
            Start-Sleep -Seconds 1
        } while ((Get-Date) -lt $deadline)
        throw "Backend did not become healthy within $TimeoutSeconds seconds."
    }
    finally {
        $ErrorActionPreference = $prevEap
        Complete-LauncherProgress $progressId
    }
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
        FASTAPI_PORT = '8890'
        UI_HOST = '127.0.0.1'
        UI_PORT = '8051'
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
if (Test-Path -LiteralPath $nodeDir) { [void](Remove-LauncherPath -Path $nodeDir -Activity 'FAIRS: replace portable Node.js runtime' -Strict) }
        New-Item -ItemType Directory -Path $nodeDir -Force | Out-Null
        Invoke-DownloadAndExtract $nodeUrl (Join-Path $nodeDir 'node.zip') $nodeDir
        $nestedNodeDir = Join-Path $nodeDir $nodeArchiveName
        if (Test-Path -LiteralPath (Join-Path $nestedNodeDir 'node.exe')) {
            Get-ChildItem -LiteralPath $nestedNodeDir -Force | Move-Item -Destination $nodeDir -Force
[void](Remove-LauncherPath -Path $nestedNodeDir -Activity 'FAIRS: flatten Node.js runtime archive' -Strict)
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
    Assert-ApplicationStopped
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
if (Test-Path -LiteralPath $venvDir) { [void](Remove-LauncherPath -Path $venvDir -Activity 'FAIRS: recreate Python environment' -Strict) }
            & $uvExe @syncArguments
        }
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }

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
    Import-DotEnv
    Assert-ApplicationStopped
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

function Register-LauncherProcess([int]$ProcessId) {
    if ($ProcessId -gt 0) {
        [void]$script:OwnedProcessIds.Add($ProcessId)
        try {
            $process = Get-Process -Id $ProcessId -ErrorAction Stop
            $script:OwnedProcessRecords[$ProcessId] = [pscustomobject]@{
                StartTime   = $process.StartTime
                CommandLine = Get-ProcessCommandLine $ProcessId
            }
        } catch {
            [void]$script:OwnedProcessRecords.Remove($ProcessId)
        }
    }
}

function Get-ProcessCommandLine([int]$ProcessId) {
    try {
        $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        return [string]$process.CommandLine
    } catch {
        return ''
    }
}

function Get-ProcessParentId([int]$ProcessId) {
    try {
        $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        return [int]$process.ParentProcessId
    } catch {
        return 0
    }
}

function Test-RecordedProcessIdentity([int]$ProcessId) {
    if (-not $script:OwnedProcessRecords.ContainsKey($ProcessId)) { return $false }
    $record = $script:OwnedProcessRecords[$ProcessId]
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        if ($process.StartTime -eq $record.StartTime) { return $true }
    } catch { }

    $currentCommandLine = Get-ProcessCommandLine $ProcessId
    return -not [string]::IsNullOrWhiteSpace($record.CommandLine) -and
        $currentCommandLine -eq $record.CommandLine
}

function Test-LauncherOwnedProcess([int]$ProcessId) {
    $visited = [Collections.Generic.HashSet[int]]::new()
    $currentProcessId = $ProcessId
    for ($depth = 0; $depth -lt 16 -and $currentProcessId -gt 0; $depth++) {
        if (-not $visited.Add($currentProcessId)) { break }
        if (Test-RecordedProcessIdentity $currentProcessId) { return $true }

        $commandLine = Get-ProcessCommandLine $currentProcessId
        if (-not [string]::IsNullOrWhiteSpace($commandLine)) {
            $inRepository = $commandLine.IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
            $backendMarker = $commandLine.IndexOf('server.app:app', [StringComparison]::OrdinalIgnoreCase) -ge 0
            $frontendMarker = $commandLine.IndexOf('run preview', [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                $commandLine.IndexOf('vite preview', [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                $commandLine -match '(?i)node_modules[\\/].*\bvite(?:\.js)?\b.*\bpreview\b'
            if ($inRepository -and ($backendMarker -or $frontendMarker)) { return $true }
        }

        $parentProcessId = Get-ProcessParentId $currentProcessId
        if ($parentProcessId -le 0 -or $parentProcessId -eq $currentProcessId) { break }
        $currentProcessId = $parentProcessId
    }

    if ($script:OwnedProcessRecords.ContainsKey($ProcessId)) {
        [void]$script:OwnedProcessRecords.Remove($ProcessId)
        [void]$script:OwnedProcessIds.Remove($ProcessId)
    }
    return $false
}

function Get-ApplicationProcessIds([int[]]$Ports) {
    $processIds = [Collections.Generic.HashSet[int]]::new()
    foreach ($port in $Ports) {
        foreach ($processId in @(Get-PortProcessIds $port)) {
            [void]$processIds.Add([int]$processId)
        }
    }
    foreach ($processId in @($script:OwnedProcessIds)) {
        try {
            if (Get-Process -Id $processId -ErrorAction Stop) {
                [void]$processIds.Add([int]$processId)
            }
        } catch { }
    }
    return @($processIds | Sort-Object)
}

function Stop-LauncherProcess([int]$ProcessId) {
    try {
        if (-not (Get-Process -Id $ProcessId -ErrorAction Stop)) {
            [void]$script:OwnedProcessIds.Remove($ProcessId)
            [void]$script:OwnedProcessRecords.Remove($ProcessId)
            return
        }
    } catch {
        [void]$script:OwnedProcessIds.Remove($ProcessId)
        [void]$script:OwnedProcessRecords.Remove($ProcessId)
        return
    }
    if (-not (Test-LauncherOwnedProcess $ProcessId)) {
        throw "Refusing to stop unrelated PID $ProcessId. Its command line does not belong to this repository."
    }
    Write-Info "Stopping application PID $ProcessId."
    & taskkill.exe /PID $ProcessId /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
        try {
            Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
            throw "Could not stop application PID $ProcessId (taskkill exit code $LASTEXITCODE)."
        } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
            # The process may already have exited after taskkill terminated its tree.
        }
    }
    [void]$script:OwnedProcessIds.Remove($ProcessId)
    [void]$script:OwnedProcessRecords.Remove($ProcessId)
}

function Assert-ApplicationProcessOwnership([int[]]$ProcessIds) {
    $unowned = foreach ($processId in $ProcessIds) {
        if (-not (Test-LauncherOwnedProcess $processId)) {
            $commandLine = Get-ProcessCommandLine $processId
            if ([string]::IsNullOrWhiteSpace($commandLine)) {
                "PID $processId (command line unavailable)"
            } else {
                "PID $processId ($commandLine)"
            }
        }
    }
    if (@($unowned).Count -gt 0) {
        throw "Refusing to stop unrelated process(es). $($unowned -join '; ')"
    }
}

function Assert-ApplicationStopped {
    $fastApiPort = [int]$env:FASTAPI_PORT
    $uiPort = [int]$env:UI_PORT
    $processIds = @(Get-ApplicationProcessIds @($fastApiPort, $uiPort))
    if ($processIds.Count -eq 0) { return }

    $details = foreach ($processId in $processIds) {
        $commandLine = Get-ProcessCommandLine $processId
        if ([string]::IsNullOrWhiteSpace($commandLine)) {
            "PID $processId (command line unavailable)"
        } else {
            "PID $processId ($commandLine)"
        }
    }
    throw "Application processes are still running. Use Stop application first. $($details -join '; ')"
}

function Assert-SingleWorkerConfiguration {
    foreach ($variableName in @('WEB_CONCURRENCY', 'UVICORN_WORKERS', 'FAIRS_WORKERS')) {
        $rawValue = [Environment]::GetEnvironmentVariable($variableName, 'Process')
        if ([string]::IsNullOrWhiteSpace($rawValue)) { continue }
        $workerCount = 0
        if (-not [int]::TryParse($rawValue.Trim(), [ref]$workerCount) -or $workerCount -ne 1) {
            throw "$variableName=$rawValue is unsupported. FAIRS requires exactly one backend worker for process-local training and inference state."
        }
    }
}

function Stop-Application {
    Import-DotEnv
    $fastApiPort = [int]$env:FASTAPI_PORT
    $uiPort = [int]$env:UI_PORT
    $processIds = @(Get-ApplicationProcessIds @($fastApiPort, $uiPort))
    if ($processIds.Count -eq 0) {
        Write-Info 'No application processes are running.'
        return
    }

    Assert-ApplicationProcessOwnership $processIds
    foreach ($processId in $processIds) {
        Stop-LauncherProcess $processId
    }
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $remainingPorts = @(Get-PortProcessIds $fastApiPort) + @(Get-PortProcessIds $uiPort) |
            Sort-Object -Unique
        $remainingOwned = @(Get-ApplicationProcessIds @($fastApiPort, $uiPort))
        if ($remainingPorts.Count -eq 0 -and $remainingOwned.Count -eq 0) {
            Write-Ok 'Application stopped.'
            return
        }
        if ($remainingPorts.Count -eq 0 -and $remainingOwned.Count -gt 0) {
            Assert-ApplicationProcessOwnership $remainingOwned
            foreach ($processId in $remainingOwned) {
                Stop-LauncherProcess $processId
            }
            continue
        }
        Assert-ApplicationProcessOwnership $remainingPorts
        Start-Sleep -Seconds 1
    }
    throw "Application processes or configured ports are still occupied after shutdown."
}

# -----------------------------------------------------------------------------
# Application lifecycle
# -----------------------------------------------------------------------------
function Start-Application {
    Import-DotEnv
    Assert-ApplicationStopped
    Assert-SingleWorkerConfiguration
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

    $reloadArgument = if ($env:RELOAD -eq 'true') { ' --reload' } else { '' }
    if ($env:RELOAD -eq 'true') {
        Write-Info 'RELOAD=true is development-only; reloads discard in-memory training jobs and inference sessions.'
    }
    $backendArgs = "-m uvicorn server.app:app --app-dir `"$($repoRoot)\app`" --host $($env:FASTAPI_HOST) --port $fastApiPort --workers 1$reloadArgument --log-level info"
    Write-Step 'Launching backend.'
    if ($env:BACKEND_LOGS_VISIBLE -eq 'true') {
        $backendCommand = '"' + $venvPython + '" ' + $backendArgs
        $backendProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d', '/k', $backendCommand) -WorkingDirectory $repoRoot -PassThru
    } else {
        $backendProcess = Start-Process -FilePath $venvPython -ArgumentList $backendArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
    }
    Register-LauncherProcess $backendProcess.Id

    $backendUrl = "http://$($env:FASTAPI_HOST):$fastApiPort"
    Write-Step "Waiting for backend readiness at $backendUrl/api/health."
    try {
        Invoke-HealthCheck "$backendUrl/api/health" 60
    } catch {
        try { Stop-Application } catch { Write-Info "Backend cleanup reported: $($_.Exception.Message)" }
        throw "Backend did not become healthy within 60 seconds."
    }
    $backendPid = (Get-PortProcessIds $fastApiPort | Select-Object -First 1)
    if (-not $backendPid) {
        try { Stop-Application } catch { Write-Info "Backend cleanup reported: $($_.Exception.Message)" }
        throw "Backend reported readiness but no listener was found on port $fastApiPort."
    }

    Write-Step 'Launching frontend preview.'
    $frontendArgs = "/c `"`"$npmCmd`" run preview -- --host $($env:UI_HOST) --port $uiPort --strictPort`""
    $frontendProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList $frontendArgs -WorkingDirectory $clientDir -WindowStyle Hidden -PassThru
    Register-LauncherProcess $frontendProcess.Id
    $uiUrl = "http://$($env:UI_HOST):$uiPort"
    $frontendReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $uiUrl -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                $frontendReady = $true
                break
            }
        } catch { }
        Start-Sleep -Seconds 1
    }
    $frontendPid = (Get-PortProcessIds $uiPort | Select-Object -First 1)
    if (-not $frontendReady -or -not $frontendPid) {
        try { Stop-Application } catch { Write-Info "Application cleanup reported: $($_.Exception.Message)" }
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
    Assert-ApplicationStopped
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
    Import-DotEnv
    Assert-ApplicationStopped
    Set-CacheEnvironment
    & (Join-Path $repoRoot 'app\tests\run_tests.bat')
    if ($LASTEXITCODE -ne 0) { throw "Test suite failed with exit code $LASTEXITCODE." }
    Write-Ok 'Test suite completed.'
}

# -----------------------------------------------------------------------------
# Cleanup and data management
# -----------------------------------------------------------------------------
function Confirm-DestructiveAction([string]$Description) {
    $confirmation = ([string](Read-Host "Continue to $Description? [y/N]")).Trim()
    if ($confirmation -notmatch '^(?i:y|yes)$') {
        Write-Info "Operation cancelled. No changes were made."
        return $false
    }
    return $true
}

function Remove-Logs {
    Import-DotEnv
    Assert-ApplicationStopped
    if (-not (Confirm-DestructiveAction 'remove application log files')) { return }

    $logDir = (Get-UserDataTargets).LogRoot
    Remove-UserLogFiles $logDir
    Write-Ok 'Log files removed.'
}

function Remove-UserLogFiles([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return }
    $logFiles = @(Get-ChildItem -LiteralPath $Path -Filter '*.log' -File -Recurse -Force -ErrorAction SilentlyContinue |
        Sort-Object @{ Expression = { $_.FullName.ToUpperInvariant() }; Descending = $false })
    $progressId = Start-LauncherProgress -Activity "FAIRS: remove logs from $Path" -Status "0 of $($logFiles.Count) files"
    try {
        for ($index = 0; $index -lt $logFiles.Count; $index++) {
            $logFile = $logFiles[$index]
            Update-LauncherProgress -Id $progressId -Activity "FAIRS: remove logs from $Path" -Status "$($index + 1) of $($logFiles.Count): $($logFile.Name)" -PercentComplete ([int](($index + 1) * 100 / [Math]::Max(1, $logFiles.Count)))
            Remove-PathBestEffort $logFile.FullName | Out-Null
        }
    }
    finally {
        Complete-LauncherProgress $progressId
    }
}

function Remove-PythonCaches {
    $pythonCacheDirs = @(Get-ChildItem -LiteralPath $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object Name -eq '__pycache__' |
        Sort-Object @{ Expression = { $_.FullName.Length }; Descending = $true }, @{ Expression = { $_.FullName.ToUpperInvariant() }; Descending = $false })
    foreach ($pythonCacheDir in $pythonCacheDirs) {
        Remove-PathBestEffort $pythonCacheDir.FullName | Out-Null
    }
}

function Clear-Cache {
    Import-DotEnv
    Assert-ApplicationStopped
    if (-not (Confirm-DestructiveAction 'clear Python, uv, and tool caches')) { return }

    $cachePaths = @($runtimeCacheDir, $testCacheDir)
    $progressId = Start-LauncherProgress -Activity 'FAIRS: clear caches' -Status "0 of $($cachePaths.Count) roots"
    try {
        for ($index = 0; $index -lt $cachePaths.Count; $index++) {
            $cachePath = $cachePaths[$index]
            Update-LauncherProgress -Id $progressId -Activity 'FAIRS: clear caches' -Status "$($index + 1) of $($cachePaths.Count): $cachePath" -PercentComplete ([int](($index + 1) * 100 / $cachePaths.Count))
            Remove-PathBestEffort $cachePath | Out-Null
        }
    }
    finally {
        Complete-LauncherProgress $progressId
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
    $children = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue |
        Sort-Object @{ Expression = { $_.FullName.ToUpperInvariant() }; Descending = $false })
    $progressId = Start-LauncherProgress -Activity "FAIRS: remove data from $Path" -Status "0 of $($children.Count) items"
    try {
        for ($index = 0; $index -lt $children.Count; $index++) {
            $child = $children[$index]
            if ($child.Name -eq '.gitkeep') { continue }
            Update-LauncherProgress -Id $progressId -Activity "FAIRS: remove data from $Path" -Status "$($index + 1) of $($children.Count): $($child.Name)" -PercentComplete ([int](($index + 1) * 100 / [Math]::Max(1, $children.Count)))
            Remove-PathBestEffort $child.FullName | Out-Null
        }
    }
    finally {
        Complete-LauncherProgress $progressId
    }
}

function Remove-Checkpoints {
    Import-DotEnv
    Assert-ApplicationStopped
    if (-not (Confirm-DestructiveAction 'delete all saved checkpoints')) { return }

    $targets = Get-UserDataTargets
    Remove-UserDataDirectory $targets.CheckpointRoot
    New-Item -ItemType Directory -Path $targets.CheckpointRoot -Force | Out-Null
    Write-Ok 'All saved checkpoints were removed.'
}

function Remove-AllData {
    Import-DotEnv
    Assert-ApplicationStopped
    if (-not (Confirm-DestructiveAction 'delete local user data')) { return }

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
    Import-DotEnv
    Assert-ApplicationStopped
    if (-not (Confirm-DestructiveAction 'remove local runtimes and build outputs')) { return }

    $paths = @(
        $runtimeRoot,
        (Join-Path $serverDir '.venv'),
        (Join-Path $repoRoot '.venv'),
        (Join-Path $clientDir 'node_modules'),
        (Join-Path $clientDir '.angular'),
        (Join-Path $clientDir 'dist')
    )
    $progressId = Start-LauncherProgress -Activity 'FAIRS: uninstall application' -Status "0 of $($paths.Count) paths"
    try {
        for ($index = 0; $index -lt $paths.Count; $index++) {
            $path = $paths[$index]
            Update-LauncherProgress -Id $progressId -Activity 'FAIRS: uninstall application' -Status "$($index + 1) of $($paths.Count): $path" -PercentComplete ([int](($index + 1) * 100 / $paths.Count))
            Remove-PathBestEffort $path | Out-Null
        }
    }
    finally {
        Complete-LauncherProgress $progressId
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
    Import-DotEnv
    Assert-ApplicationStopped
    Push-Location $repoRoot
    try {
        $branchOutput = @(& git branch --show-current 2>$null)
        $branchExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        $currentBranch = (@($branchOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
        if ($branchExitCode -ne 0) { throw 'Unable to determine the current Git branch.' }
        if ([string]::IsNullOrWhiteSpace($currentBranch)) { throw 'Update requires a non-detached Git checkout.' }
        if ($currentBranch -ne 'main') {
            throw "Update requires the main branch to be checked out; current branch is '$currentBranch'. No files were changed."
        }
        $statusOutput = @(& git status --porcelain 2>$null)
        $statusExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($statusExitCode -ne 0) { throw 'Unable to inspect the Git working tree before updating.' }
        $changes = @($statusOutput | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
        if ($changes.Count -gt 0) { throw 'Update requires a clean Git working tree. Commit or safely preserve local changes before retrying.' }

        Write-Step 'Pulling application updates from origin/main (fast-forward only).'
        $gitOutput = @(& git pull --ff-only origin main 2>&1)
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
    Clear-LauncherProgress
    if (-not $script:LauncherInteractive) { return }
    Write-Host ''
    Write-Host '  Press any key to return to the menu...' -ForegroundColor DarkGray
    try { [void][Console]::ReadKey($true) } catch { }
}

function Get-LauncherMenuEntries {
    @(
        [pscustomobject]@{ Section = 'APPLICATION'; Key = 'Launch'; Label = 'Launch application'; Description = 'Start the backend and player'; Color = [ConsoleColor]::Cyan }
        [pscustomobject]@{ Section = 'APPLICATION'; Key = 'Stop'; Label = 'Stop application'; Description = 'Stop only this repository''s backend and player'; Color = [ConsoleColor]::Cyan }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Install'; Label = 'Install / update dependencies'; Description = 'Prepare local runtimes and build the frontend'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Rebuild'; Label = 'Rebuild frontend'; Description = 'Build the frontend without updating dependencies'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Database'; Label = 'Create / upgrade database'; Description = 'Create the selected database and apply migrations'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Tests'; Label = 'Run test suite'; Description = 'Execute automated checks'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SOURCE CONTROL'; Key = 'Check'; Label = 'Check for updates'; Description = 'Report local main-branch update status only'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SOURCE CONTROL'; Key = 'Update'; Label = 'Update application'; Description = 'Pull application changes from the main branch'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Logs'; Label = 'Remove logs'; Description = 'Delete application log files'; Color = [ConsoleColor]::DarkYellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Cache'; Label = 'Clear cache'; Description = 'Remove Python, uv, and tool caches'; Color = [ConsoleColor]::DarkYellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Checkpoints'; Label = 'Remove checkpoints'; Description = 'Delete saved checkpoints only'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'AllData'; Label = 'Remove all data'; Description = 'Delete local database and logs, preserving checkpoints'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Uninstall'; Label = 'Uninstall application'; Description = 'Remove local runtimes and build outputs'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'EXIT'; Key = 'Exit'; Label = 'Exit'; Description = 'Close this launcher'; Color = [ConsoleColor]::DarkGray }
    )
}

function Write-MenuItem {
    param(
        [Parameter(Mandatory)]$Entry,
        [Parameter(Mandatory)][int]$NumberWidth,
        [Parameter(Mandatory)][int]$LabelWidth
    )
    Write-Host ("  {0,$NumberWidth}. {1,-$LabelWidth}  {2}" -f $Entry.Number, $Entry.Label, $Entry.Description) -ForegroundColor $Entry.Color
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
        Clear-LauncherProgress
        $entries = @(Get-LauncherMenuEntries)
        for ($index = 0; $index -lt $entries.Count; $index++) {
            $entries[$index] | Add-Member -NotePropertyName Number -NotePropertyValue ($index + 1) -Force
        }
        $numberWidth = [math]::Max(1, $entries.Count.ToString().Length)
        $labelWidth = [math]::Max(1, (($entries | ForEach-Object { $_.Label.Length } | Measure-Object -Maximum).Maximum))
        if (Test-InteractiveConsole) {
            Clear-Host
        }
        Write-Host ''
        Write-Host '  +---------------------------------------------------+' -ForegroundColor DarkCyan
        Write-Host '  |                                                   |' -ForegroundColor DarkCyan
        Write-Host '  |             FAIRS  /  ROULETTE PLAYER             |' -ForegroundColor Cyan
        Write-Host '  |          Local launcher and maintenance           |' -ForegroundColor DarkGray
        Write-Host '  |                                                   |' -ForegroundColor DarkCyan
        Write-Host '  +---------------------------------------------------+' -ForegroundColor DarkCyan
        Write-Host ''
        $lastSection = $null
        foreach ($entry in $entries) {
            if ($entry.Section -ne $lastSection) {
                if ($null -ne $lastSection) { Write-Host '' }
                Write-Host ("  {0}" -f $entry.Section) -ForegroundColor DarkCyan
                $lastSection = $entry.Section
            }
            Write-MenuItem -Entry $entry -NumberWidth $numberWidth -LabelWidth $labelWidth
        }
        Write-Host ''
        Write-Host '  -----------------------------------------------------' -ForegroundColor DarkCyan
        Write-Host ''
        $selection = Read-Host ("  Select an option (1-{0})" -f $entries.Count)
        $selectedNumber = 0
        if (-not [int]::TryParse($selection, [ref]$selectedNumber) -or $selectedNumber -lt 1 -or $selectedNumber -gt $entries.Count) {
            Write-Fatal ("Invalid option. Select a number from 1 through {0}." -f $entries.Count)
            Wait-ForMenu
            continue
        }
        $selectedEntry = $entries[$selectedNumber - 1]
        if ($selectedEntry.Key -eq 'Exit') { break }
        try {
        Invoke-TrackedLauncherAction -Name "menu option $($selectedEntry.Number)" -Action {
            switch ($selectedEntry.Key) {
                'Launch' { Start-Application; exit 0 }
                'Stop' { Stop-Application }
                'Update' { Update-Application }
                'Check' { Check-ForUpdates }
                'Install' {
                    $installationType = Read-InstallationType
                    Install-Dependencies -PruneCache -InstallationType $installationType
                    Build-Frontend
                    Initialize-Database
                }
                'Rebuild' { Build-Frontend }
                'Database' { Initialize-Database }
                'Tests' { Invoke-TestSuite }
                'Logs' { Remove-Logs }
                'Cache' { Clear-Cache }
                'Checkpoints' { Remove-Checkpoints }
                'AllData' { Remove-AllData }
                'Uninstall' { Uninstall-Application }
            }
        }
            if (-not $script:LauncherInteractive) { break }
        } catch {
            Write-Fatal $_.Exception.Message
            if (-not $script:LauncherInteractive) { exit 1 }
        }
        Wait-ForMenu
    }
}

Set-CacheEnvironment
Show-Menu
Clear-LauncherProgress
