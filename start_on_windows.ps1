# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

# -----------------------------------------------------------------------------
# Launcher paths and runtime locations
# -----------------------------------------------------------------------------
[CmdletBinding()]
param(
    [switch]$Launch
)

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
$backendInstallStatePath = Join-Path $venvDir '.fairs-install-state.json'
$frontendDependencyStatePath = Join-Path $clientDir 'node_modules\.fairs-install-state.json'
$frontendBuildStatePath = Join-Path $clientDir 'dist\.fairs-build-state.json'
$envFile = Join-Path $repoRoot 'settings\.env'
$envExample = Join-Path $repoRoot 'settings\.env.example'
$runtimeCacheDir = Join-Path $runtimeRoot 'cache'
$cacheDirectories = [ordered]@{
    uv = Join-Path $runtimeCacheDir 'uv'
    npm = Join-Path $runtimeCacheDir 'npm'
    pip = Join-Path $runtimeCacheDir 'pip'
    python = Join-Path $runtimeCacheDir 'python'
    pytest = Join-Path $runtimeCacheDir 'pytest'
    'pytest-tmp' = Join-Path $runtimeCacheDir 'pytest-tmp'
    ruff = Join-Path $runtimeCacheDir 'ruff'
    mypy = Join-Path $runtimeCacheDir 'mypy'
    coverage = Join-Path $runtimeCacheDir 'coverage'
    'playwright-browsers' = Join-Path $runtimeCacheDir 'playwright-browsers'
    vite = Join-Path $runtimeCacheDir 'vite'
    typescript = Join-Path $runtimeCacheDir 'typescript'
    keras = Join-Path $runtimeCacheDir 'keras'
    torch = Join-Path $runtimeCacheDir 'torch'
    'torch-inductor' = Join-Path $runtimeCacheDir 'torch-inductor'
    triton = Join-Path $runtimeCacheDir 'triton'
    matplotlib = Join-Path $runtimeCacheDir 'matplotlib'
    xdg = Join-Path $runtimeCacheDir 'xdg'
    cuda = Join-Path $runtimeCacheDir 'cuda'
}
$script:NextProgressId = 1
$script:ActiveProgressActivities = [Collections.Generic.Dictionary[int, string]]::new()
$script:LauncherInteractive = -not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected

# -----------------------------------------------------------------------------
# Portable runtime versions and download sources
# -----------------------------------------------------------------------------
$pythonVersion = '3.14.7'
$dependencyStateSchemaVersion = 1
$frontendBuildStateSchemaVersion = 1
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
            if (Test-InteractiveConsole) {
                try { Write-Progress -Id $Id -Activity $activity -Completed } catch { }
            }
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
    New-Item -ItemType Directory -Path (@($runtimeCacheDir) + @($cacheDirectories.Values)) -Force | Out-Null

    $env:FAIRS_CACHE_DIR = $runtimeCacheDir
    $env:UV_CACHE_DIR = $cacheDirectories['uv']
    $env:NPM_CONFIG_CACHE = $cacheDirectories['npm']
    $env:PIP_CACHE_DIR = $cacheDirectories['pip']
    $env:PYTHONPYCACHEPREFIX = $cacheDirectories['python']
    $env:PYTEST_CACHE_DIR = $cacheDirectories['pytest']
    $env:PYTEST_BASETEMP_DIR = $cacheDirectories['pytest-tmp']
    $env:RUFF_CACHE_DIR = $cacheDirectories['ruff']
    $env:MYPY_CACHE_DIR = $cacheDirectories['mypy']
    $env:COVERAGE_FILE = Join-Path $cacheDirectories['coverage'] '.coverage'
    $env:PLAYWRIGHT_BROWSERS_PATH = $cacheDirectories['playwright-browsers']
    $env:KERAS_HOME = $cacheDirectories['keras']
    $env:TORCH_HOME = $cacheDirectories['torch']
    $env:TORCHINDUCTOR_CACHE_DIR = $cacheDirectories['torch-inductor']
    $env:TRITON_CACHE_DIR = $cacheDirectories['triton']
    $env:MPLCONFIGDIR = $cacheDirectories['matplotlib']
    $env:XDG_CACHE_HOME = $cacheDirectories['xdg']
    $env:CUDA_CACHE_PATH = $cacheDirectories['cuda']
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
        $found
    } else { @($item) }
    $entries = @($entries)
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
    if ($item.PSIsContainer -and -not $KeepRoot -and $preservedPaths.Count -eq 0 -and $enumerationErrors.Count -eq 0) {
        $entries += $item
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

function Clear-RuntimeCacheDirectory {
    if (-not (Test-Path -LiteralPath $runtimeCacheDir -PathType Container)) { return }

    $cacheEntries = @(Get-ChildItem -LiteralPath $runtimeCacheDir -Force -ErrorAction SilentlyContinue)
    foreach ($entry in $cacheEntries) {
        if (-not $entry.PSIsContainer -and $entry.Name -eq '.gitkeep') { continue }
        Remove-LauncherPath -Path $entry.FullName -PreserveNames @() -Activity "FAIRS: remove $($entry.Name)" | Out-Null
    }
}

function Get-ServerBytecodeCleanupPaths {
    if (-not (Test-Path -LiteralPath $serverDir -PathType Container)) { return @() }

    $serverPath = [IO.Path]::GetFullPath($serverDir).TrimEnd('\')
    $venvPath = [IO.Path]::GetFullPath($venvDir).TrimEnd('\') + '\'
    $pendingDirectories = [Collections.Generic.Stack[string]]::new()
    $bytecodePaths = [Collections.Generic.List[string]]::new()
    $pendingDirectories.Push($serverPath)

    while ($pendingDirectories.Count -gt 0) {
        $currentPath = $pendingDirectories.Pop()
        $directories = @(Get-ChildItem -LiteralPath $currentPath -Directory -Force -ErrorAction SilentlyContinue)
        foreach ($directory in $directories) {
            if (($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
            if ($directory.FullName.Equals($venvPath.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase) -or
                $directory.FullName.StartsWith($venvPath, [StringComparison]::OrdinalIgnoreCase)) { continue }
            if ($directory.Name -eq '__pycache__') {
                [void]$bytecodePaths.Add($directory.FullName)
                continue
            }
            $pendingDirectories.Push($directory.FullName)
        }
    }

    return @($bytecodePaths | Sort-Object Length -Descending)
}

function Get-CacheCleanupPaths {
    return @($runtimeCacheDir) + @(Get-ServerBytecodeCleanupPaths)
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
    $lines = @(Get-Content -LiteralPath $Path)
    if ($lines -contains 'import site') { return }
    if (-not ($lines -contains '#import site')) { throw "Portable Python site configuration is missing: $Path" }
    $lines -replace '^#import site$', 'import site' | Set-Content -LiteralPath $Path -Encoding ASCII
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
    $loadedKeys = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $databaseEnvironmentKeys = @(
        'DATABASE_URL', 'EMBEDDED_DATABASE', 'DATABASE_ENGINE', 'DATABASE_HOST',
        'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USERNAME', 'DATABASE_PASSWORD',
        'DATABASE_SSL', 'DATABASE_SSL_CA', 'DATABASE_CONNECT_TIMEOUT',
        'DATABASE_INSERT_BATCH_SIZE'
    )
    foreach ($rawLine in Get-Content -LiteralPath $envFile) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#') -or $line.StartsWith(';') -or -not $line.Contains('=')) { continue }
        $key, $value = $line.Split('=', 2)
        $key = $key.Trim()
        $value = $value.Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($key) {
            if ($databaseEnvironmentKeys -contains $key) { continue }
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
            [void]$loadedKeys.Add($key)
        }
    }

    $requiredLauncherVariables = @(
        'FASTAPI_HOST',
        'FASTAPI_PORT',
        'RELOAD'
    )
    $missingVariables = @($requiredLauncherVariables | Where-Object {
        -not $loadedKeys.Contains($_) -or
        [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_, 'Process'))
    })
    if ($missingVariables.Count -gt 0) {
        throw "settings\.env is missing required launcher variable(s): $($missingVariables -join ', '). Update it from settings\.env.example."
    }
    Assert-DataCacheIsolation
}

function Ensure-PortableRuntimes {
    New-Item -ItemType Directory -Path $runtimeRoot, $pythonDir, $uvDir, $nodeDir -Force | Out-Null

    Write-Step 'Setting up Python (embeddable) locally.'
    $pythonFound = $null
    $pythonNeedsInstall = -not (Test-Path -LiteralPath $pythonExe)
    if (-not $pythonNeedsInstall) {
        try {
            $pythonFound = (Invoke-CheckPyver $pythonExe).Trim()
            $pythonNeedsInstall = $pythonFound -ne $pythonVersion -or
                -not (Test-Path -LiteralPath $pythonPth)
            if (-not $pythonNeedsInstall) {
                Write-Info "Portable Python $pythonFound already matches the launcher baseline."
            }
        } catch {
            $pythonNeedsInstall = $true
            $pythonFound = $null
            Write-Info "Portable Python validation failed; replacing the runtime."
        }
    }
    if ($pythonNeedsInstall) {
        $pythonFound = $null
        if (Test-Path -LiteralPath $pythonDir) {
            [void](Remove-LauncherPath -Path $pythonDir -Activity 'FAIRS: replace portable Python runtime' -Strict)
        }
        New-Item -ItemType Directory -Path $pythonDir -Force | Out-Null
        Invoke-DownloadAndExtract $pythonUrl (Join-Path $pythonDir 'python.zip') $pythonDir
    }
    if (Test-Path -LiteralPath $pythonPth) { Invoke-PatchPth $pythonPth }
    if ($null -eq $pythonFound) { $pythonFound = (Invoke-CheckPyver $pythonExe).Trim() }
    if ($pythonFound -ne $pythonVersion) {
        throw "Portable Python $pythonFound does not match the launcher baseline $pythonVersion."
    }
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
    $nodeFound = $null
    $nodeNeedsInstall = $true
    if (Test-Path -LiteralPath $nodeExe) {
        $nodeFound = (& $nodeExe --version).Trim()
        $nodeNeedsInstall = $nodeFound -ne "v$nodeVersion" -or -not (Test-Path -LiteralPath $npmCmd)
        if (-not $nodeNeedsInstall) { Write-Info "Node.js $nodeFound already matches the launcher baseline." }
    }
    if ($nodeNeedsInstall) {
        $nodeFound = $null
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
    if ($null -eq $nodeFound) { $nodeFound = (& $nodeExe --version).Trim() }
    $env:PATH = "$nodeDir;$env:PATH"
    Write-Ok "Node.js ready: $nodeFound"
}

# -----------------------------------------------------------------------------
# Dependency installation and frontend build
# -----------------------------------------------------------------------------
function Write-JsonStateFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][System.Collections.IDictionary]$State
    )
    $parentDirectory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parentDirectory -Force | Out-Null
    $json = $State | ConvertTo-Json -Depth 4
    [IO.File]::WriteAllText($Path, $json, [Text.UTF8Encoding]::new($false))
}

function Read-JsonStateFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return $null
    }
}

function Get-ContentFingerprint {
    param(
        [Parameter(Mandatory)][object[]]$Files,
        [string[]]$Context = @()
    )
    $repositoryPrefix = ([IO.Path]::GetFullPath($repoRoot)).TrimEnd('\') + '\'
    $records = [Collections.Generic.List[string]]::new()
    foreach ($file in @($Files)) {
        $filePath = if ($file -is [IO.FileInfo]) { $file.FullName } else { [string]$file }
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            throw "Fingerprint input is missing: $filePath"
        }
        $fullPath = [IO.Path]::GetFullPath($filePath)
        if (-not $fullPath.StartsWith($repositoryPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Fingerprint input is outside the repository: $fullPath"
        }
        $relativePath = $fullPath.Substring($repositoryPrefix.Length).Replace('\', '/')
        $contentHash = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
        [void]$records.Add("$relativePath=$contentHash")
    }

    $orderedRecords = [string[]]$records.ToArray()
    [Array]::Sort($orderedRecords, [StringComparer]::Ordinal)
    $canonicalLines = [Collections.Generic.List[string]]::new()
    [void]$canonicalLines.Add('content-fingerprint-schema=1')
    foreach ($contextEntry in @($Context)) { [void]$canonicalLines.Add([string]$contextEntry) }
    foreach ($record in $orderedRecords) { [void]$canonicalLines.Add($record) }
    $canonicalText = $canonicalLines -join "`n"

    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonicalText))).Replace('-', '')).ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function Get-BackendDependencyInputFiles {
    return @(
        (Join-Path $serverDir 'pyproject.toml'),
        (Join-Path $serverDir 'uv.lock')
    )
}

function Get-BackendDependencyFingerprint {
    Get-ContentFingerprint -Files (Get-BackendDependencyInputFiles) -Context @(
        "python_version=$pythonVersion"
    )
}

function Get-FrontendDependencyFingerprint {
    Get-ContentFingerprint -Files @(
        (Join-Path $clientDir 'package.json'),
        (Join-Path $clientDir 'package-lock.json')
    ) -Context @(
        "node_version=$nodeVersion"
    )
}

function Get-FrontendBuildInputFiles {
    $rootInputs = @(
        'index.html',
        'package.json',
        'package-lock.json',
        'tsconfig.json',
        'tsconfig.app.json',
        'tsconfig.node.json',
        'vite.config.ts'
    )
    $inputs = @(
        $rootInputs | ForEach-Object {
            $path = Join-Path $clientDir $_
            if (Test-Path -LiteralPath $path -PathType Leaf) { Get-Item -LiteralPath $path }
        }
    )
    foreach ($sourceDirectory in @('src', 'public')) {
        $path = Join-Path $clientDir $sourceDirectory
        if (Test-Path -LiteralPath $path -PathType Container) {
            $inputs += @(Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue)
        }
    }
    return @($inputs)
}

function Get-FrontendBuildFingerprint {
    Get-ContentFingerprint -Files (Get-FrontendBuildInputFiles) -Context @(
        "schema_version=$frontendBuildStateSchemaVersion",
        "node_version=$nodeVersion"
    )
}

function Read-FrontendBuildState {
    $state = Read-JsonStateFile -Path $frontendBuildStatePath
    if ($null -eq $state -or
        $state.schema_version -ne $frontendBuildStateSchemaVersion -or
        [string]::IsNullOrWhiteSpace([string]$state.fingerprint) -or
        [string]$state.node_version -ne $nodeVersion) {
        return $null
    }
    return $state
}

function Write-FrontendBuildState([string]$Fingerprint) {
    Write-JsonStateFile -Path $frontendBuildStatePath -State ([ordered]@{
            schema_version = $frontendBuildStateSchemaVersion
            fingerprint = $Fingerprint
            node_version = $nodeVersion
        })
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

function Test-FrontendBuildCurrent {
    if (-not (Test-FrontendBuildReady)) { return $false }
    try {
        $state = Read-FrontendBuildState
        if ($null -eq $state) { return $false }
        return [string]$state.fingerprint -eq (Get-FrontendBuildFingerprint)
    } catch {
        return $false
    }
}

function Test-BackendDependenciesCurrent {
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf) -or
        -not (Test-Path -LiteralPath $backendInstallStatePath -PathType Leaf)) {
        return $false
    }
    try {
        $state = Read-JsonStateFile -Path $backendInstallStatePath
        if ($null -eq $state -or
            $state.schema_version -ne $dependencyStateSchemaVersion -or
            [string]$state.python_version -ne $pythonVersion -or
            [string]::IsNullOrWhiteSpace([string]$state.fingerprint) -or
            [string]$state.fingerprint -ne (Get-BackendDependencyFingerprint)) {
            return $false
        }
    } catch {
        return $false
    }
    & $venvPython -c 'import fastapi, uvicorn' *> $null
    return $LASTEXITCODE -eq 0
}

function Test-FrontendDependenciesCurrent {
    $frontendPackage = Join-Path $clientDir 'package.json'
    $frontendLock = Join-Path $clientDir 'package-lock.json'
    $frontendInstallLock = Join-Path $clientDir 'node_modules\.package-lock.json'
    $frontendRunner = Join-Path $clientDir 'node_modules\.bin\vite.cmd'
    if (-not (Test-Path -LiteralPath $frontendPackage -PathType Leaf) -or
        -not (Test-Path -LiteralPath $frontendLock -PathType Leaf) -or
        -not (Test-Path -LiteralPath $frontendDependencyStatePath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $frontendInstallLock -PathType Leaf) -or
        -not (Test-Path -LiteralPath $frontendRunner -PathType Leaf)) {
        return $false
    }
    try {
        $state = Read-JsonStateFile -Path $frontendDependencyStatePath
        if ($null -eq $state -or
            $state.schema_version -ne $dependencyStateSchemaVersion -or
            [string]$state.node_version -ne $nodeVersion -or
            [string]::IsNullOrWhiteSpace([string]$state.fingerprint) -or
            [string]$state.fingerprint -ne (Get-FrontendDependencyFingerprint)) {
            return $false
        }
    } catch {
        return $false
    }
    return $true
}

function Sync-BackendDependencies {
    param(
        [ValidateSet('Standard', 'Development')]
        [string]$InstallationType = 'Standard'
    )
    Remove-Item -LiteralPath $backendInstallStatePath -Force -ErrorAction SilentlyContinue
    Write-Step 'Installing Python dependencies with uv.'
    $syncArguments = @('sync', '--locked', '--python', $pythonExe)
    if ($InstallationType -eq 'Development') { $syncArguments += '--all-extras' }
    Push-Location $serverDir
    try {
        & $uvExe @syncArguments
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }
    Write-JsonStateFile -Path $backendInstallStatePath -State ([ordered]@{
            schema_version = $dependencyStateSchemaVersion
            fingerprint = Get-BackendDependencyFingerprint
            python_version = $pythonVersion
            installation_type = $InstallationType
        })
}

function Sync-FrontendDependencies {
    $frontendLock = Join-Path $clientDir 'package-lock.json'
    if (-not (Test-Path -LiteralPath $frontendLock -PathType Leaf)) {
        throw 'Frontend package-lock.json is required.'
    }
    Remove-Item -LiteralPath $frontendDependencyStatePath -Force -ErrorAction SilentlyContinue
    Write-Step 'Installing frontend dependencies.'
    Push-Location $clientDir
    try {
        & $npmCmd ci
        if ($LASTEXITCODE -ne 0) { throw "npm dependency installation failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }
    Write-JsonStateFile -Path $frontendDependencyStatePath -State ([ordered]@{
            schema_version = $dependencyStateSchemaVersion
            fingerprint = Get-FrontendDependencyFingerprint
            node_version = $nodeVersion
        })
}

function Invoke-FrontendBuild {
    Set-CacheEnvironment
    Remove-Item -LiteralPath $frontendBuildStatePath -Force -ErrorAction SilentlyContinue
    Write-Step 'Building frontend.'
    Push-Location $clientDir
    try {
        & $npmCmd run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }
    Write-FrontendBuildState -Fingerprint (Get-FrontendBuildFingerprint)
}

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
    Sync-BackendDependencies -InstallationType $InstallationType
    Sync-FrontendDependencies

    if ($PruneCache -and (Test-Path -LiteralPath $runtimeCacheDir)) {
        Write-Step 'Pruning runtime cache.'
        Remove-PathBestEffort $runtimeCacheDir | Out-Null
        Set-CacheEnvironment
    }
    if ($InstallationType -eq 'Development') {
        Write-Step 'Installing Playwright Chromium browser.'
        & $venvPython -m playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw "Playwright browser installation failed with exit code $LASTEXITCODE." }
    }
    Write-Ok 'Dependencies are installed.'
}

function Build-Frontend {
    Import-DotEnv
    Assert-ApplicationStopped
    Set-CacheEnvironment
    Invoke-FrontendBuild
}

function Get-PortProcessIds([int]$Port) {
    try {
        $owners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
            Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique)
        if ($owners.Count -gt 0) { return @($owners | ForEach-Object { [int]$_ }) }
    } catch { }

    $listeners = netstat.exe -ano | Select-String -Pattern ":$Port\s+.*(?:LISTENING|IN ASCOLTO)\s+(\d+)\s*$"
    return @($listeners | ForEach-Object {
        if ($_.Matches.Count) { [int]$_.Matches[0].Groups[1].Value }
    } | Sort-Object -Unique)
}

function Get-ConfiguredPortConflicts {
    param(
        [Parameter(Mandatory)][int]$BackendPort,
        [int]$FrontendPort = 0
    )
    $portEntries = @([pscustomobject]@{ Port = $BackendPort; Label = 'FASTAPI_PORT' })
    if ($FrontendPort -gt 0 -and $FrontendPort -ne $BackendPort) {
        $portEntries += [pscustomobject]@{ Port = $FrontendPort; Label = 'UI_PORT' }
    }
    $recordsByPid = @{}
    foreach ($portEntry in $portEntries) {
        foreach ($processId in @(Get-PortProcessIds -Port ([int]$portEntry.Port))) {
            if (-not $recordsByPid.ContainsKey([int]$processId)) {
                $recordsByPid[[int]$processId] = [ordered]@{
                    ProcessId = [int]$processId
                    Ports = [Collections.Generic.List[int]]::new()
                    PortLabels = [Collections.Generic.List[string]]::new()
                }
            }
            $record = $recordsByPid[[int]$processId]
            if (-not $record.Ports.Contains([int]$portEntry.Port)) { [void]$record.Ports.Add([int]$portEntry.Port) }
            if (-not $record.PortLabels.Contains([string]$portEntry.Label)) { [void]$record.PortLabels.Add([string]$portEntry.Label) }
        }
    }
    if ($recordsByPid.Count -eq 0) { return @() }

    $metadataByPid = @{}
    try {
        foreach ($process in @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)) {
            $processId = [int]$process.ProcessId
            if ($recordsByPid.ContainsKey($processId)) {
                $metadataByPid[$processId] = [pscustomobject]@{
                    ProcessName = [string]$process.Name
                    ExecutablePath = [string]$process.ExecutablePath
                }
            }
        }
    } catch {
        Write-Info "Could not read Win32 process metadata; process names and executable paths may be unavailable."
    }
    foreach ($processId in @($recordsByPid.Keys)) {
        if ($metadataByPid.ContainsKey([int]$processId)) { continue }
        try {
            $process = Get-Process -Id ([int]$processId) -ErrorAction Stop
            $executablePath = ''
            try { $executablePath = [string]$process.Path } catch { }
            $metadataByPid[[int]$processId] = [pscustomobject]@{
                ProcessName = [string]$process.ProcessName
                ExecutablePath = $executablePath
            }
        } catch { }
    }

    return @($recordsByPid.Values | ForEach-Object {
            $record = $_
            $metadata = $metadataByPid[[int]$record.ProcessId]
            $processName = if ($null -ne $metadata -and -not [string]::IsNullOrWhiteSpace($metadata.ProcessName)) {
                $metadata.ProcessName
            } else { 'Unknown' }
            $executablePath = if ($null -ne $metadata) { [string]$metadata.ExecutablePath } else { '' }
            [pscustomobject]@{
                ProcessId = [int]$record.ProcessId
                ProcessName = $processName
                ExecutablePath = $executablePath
                Ports = @($record.Ports | Sort-Object -Unique)
                PortLabels = @($record.PortLabels | Sort-Object -Unique)
            }
        } | Sort-Object ProcessId)
}

function Get-PortConflictDescription([object[]]$Conflicts) {
    return @($Conflicts | ForEach-Object {
            $portNames = @($_.PortLabels) -join ', '
            $ports = @($_.Ports) -join ', '
            $name = if ([string]::IsNullOrWhiteSpace([string]$_.ProcessName)) { 'Unknown' } else { $_.ProcessName }
            $executable = if ([string]::IsNullOrWhiteSpace([string]$_.ExecutablePath)) { 'path unavailable' } else { $_.ExecutablePath }
            "PID $($_.ProcessId) | $name | $portNames ($ports) | $executable"
        }) -join '; '
}

function Stop-PortConflictProcesses {
    param([Parameter(Mandatory)][object[]]$Conflicts)
    $seenProcessIds = [Collections.Generic.HashSet[int]]::new()
    $targetedProcessIds = [Collections.Generic.List[int]]::new()
    $stopErrors = [Collections.Generic.List[string]]::new()
    foreach ($conflict in @($Conflicts)) {
        $processId = [int]$conflict.ProcessId
        if (-not $seenProcessIds.Add($processId)) { continue }
        [void]$targetedProcessIds.Add($processId)
        if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { continue }
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
            if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
                [void]$stopErrors.Add("PID $processId ($($conflict.ProcessName)): $($_.Exception.Message)")
            }
        }
    }
    return [pscustomobject]@{
        TargetedProcessIds = @($targetedProcessIds)
        Errors = @($stopErrors)
    }
}

function Resolve-LaunchPortConflicts {
    param(
        [Parameter(Mandatory)][int]$BackendPort,
        [int]$FrontendPort = 0
    )
    $conflicts = @(Get-ConfiguredPortConflicts -BackendPort $BackendPort -FrontendPort $FrontendPort)
    if ($conflicts.Count -eq 0) { return $true }

    Write-Host ''
    Write-Host 'Configured launch port conflicts were found:' -ForegroundColor Yellow
    foreach ($conflict in $conflicts) {
        $portNames = @($conflict.PortLabels) -join ', '
        $ports = @($conflict.Ports) -join ', '
        $executable = if ([string]::IsNullOrWhiteSpace([string]$conflict.ExecutablePath)) { 'path unavailable' } else { $conflict.ExecutablePath }
        Write-Host "  PID $($conflict.ProcessId) | $($conflict.ProcessName) | $portNames ($ports) | $executable" -ForegroundColor Yellow
    }

    if (-not (Test-InteractiveConsole)) {
        throw "Configured launch port(s) are occupied. Noninteractive launch will not terminate unconfirmed processes. $((Get-PortConflictDescription $conflicts))"
    }
    if (-not (Confirm-DestructiveAction 'terminate the listed configured-port processes')) { return $false }

    $stopResult = Stop-PortConflictProcesses -Conflicts $conflicts
    $remainingConflicts = @()
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $remainingConflicts = @(Get-ConfiguredPortConflicts -BackendPort $BackendPort -FrontendPort $FrontendPort)
        if ($remainingConflicts.Count -eq 0) { break }
        if ($attempt -lt 19) { Start-Sleep -Milliseconds 250 }
    }
    if ($stopResult.Errors.Count -gt 0 -or $remainingConflicts.Count -gt 0) {
        $details = @()
        if ($stopResult.Errors.Count -gt 0) { $details += @($stopResult.Errors) }
        if ($remainingConflicts.Count -gt 0) { $details += "Remaining: $(Get-PortConflictDescription $remainingConflicts)" }
        throw "Could not clear the configured launch port(s). $($details -join '; ')"
    }
    return $true
}

function Get-ApplicationProcessRecords {
    $processes = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    $repoRootPrefix = ([IO.Path]::GetFullPath($repoRoot)).TrimEnd('\') + '\'
    $repoRootPattern = [regex]::Escape($repoRootPrefix.TrimEnd('\'))
    $applicationCommandPattern = '(?i)(\buvicorn\b|server\.app:app|\bnpm(?:\.cmd)?\b[^\r\n]*\brun\s+preview\b|\bvite(?:\.cmd)?\b[^\r\n]*\bpreview\b)'
    $applicationProcessIds = [Collections.Generic.HashSet[int]]::new()

    foreach ($process in $processes) {
        $processId = [int]$process.ProcessId
        if ($processId -eq $PID) { continue }

        $commandLine = [string]$process.CommandLine
        $applicationCommand = $commandLine -match $repoRootPattern -and
            $commandLine -match $applicationCommandPattern

        if ($applicationCommand) {
            [void]$applicationProcessIds.Add($processId)
        }
    }

    do {
        $addedProcess = $false
        foreach ($process in $processes) {
            $processId = [int]$process.ProcessId
            $parentProcessId = [int]$process.ParentProcessId
            if (-not $applicationProcessIds.Contains($processId) -and
                $applicationProcessIds.Contains($parentProcessId)) {
                [void]$applicationProcessIds.Add($processId)
                $addedProcess = $true
            }
        }
    } while ($addedProcess)

    return @($processes | Where-Object {
        $applicationProcessIds.Contains([int]$_.ProcessId)
    } | Sort-Object ProcessId)
}

function Assert-ApplicationStopped {
    $fastApiPort = [int]$env:FASTAPI_PORT
    $ports = @($fastApiPort)
    $uiPort = 0
    if ([int]::TryParse([string]$env:UI_PORT, [ref]$uiPort) -and $uiPort -gt 0 -and $uiPort -ne $fastApiPort) {
        $ports += $uiPort
    }
    $processIds = @($ports | ForEach-Object { Get-PortProcessIds ([int]$_) }) | Sort-Object -Unique
    if ($processIds.Count -eq 0) { return }

    throw "Application is still running on configured port(s). Close the application terminal first. PIDs: $($processIds -join ', ')."
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

# -----------------------------------------------------------------------------
# Application lifecycle
# -----------------------------------------------------------------------------
function Start-Application {
    Import-DotEnv
    $fastApiPort = [int]$env:FASTAPI_PORT
    if (-not (Resolve-LaunchPortConflicts -BackendPort $fastApiPort)) {
        return $false
    }
    Assert-SingleWorkerConfiguration
    Ensure-PortableRuntimes
    Set-CacheEnvironment
    $env:UV_PROJECT_ENVIRONMENT = $venvDir
    $env:UV_LINK_MODE = 'copy'
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue
    if (-not (Test-BackendDependenciesCurrent)) {
        Write-Step 'Backend dependency state is missing or stale; synchronizing backend dependencies.'
        Sync-BackendDependencies -InstallationType 'Standard'
    } else {
        Write-Ok 'Backend dependencies are current; skipped backend synchronization.'
    }
    if (-not (Test-FrontendDependenciesCurrent)) {
        Write-Step 'Frontend dependency state is missing or stale; synchronizing frontend dependencies.'
        Sync-FrontendDependencies
    } else {
        Write-Ok 'Frontend dependencies are current; skipped frontend dependency synchronization.'
    }
    if (-not (Test-FrontendBuildCurrent)) {
        Write-Step 'Frontend source or build inputs changed; rebuilding frontend.'
        Invoke-FrontendBuild
    } else {
        Write-Ok 'Frontend build is current; skipped frontend build.'
    }

    if ($env:RELOAD -eq 'true') {
        Write-Info 'RELOAD=true is development-only; reloads discard in-memory training jobs and inference sessions.'
    }
    $browserHost = ([string]$env:FASTAPI_HOST).Trim()
    if ($browserHost -in @('0.0.0.0', '::', '[::]')) { $browserHost = '127.0.0.1' }
    if ($browserHost.Contains(':') -and -not $browserHost.StartsWith('[')) { $browserHost = "[$browserHost]" }
    $appUrl = 'http://{0}:{1}/' -f $browserHost, $fastApiPort
    $healthUrl = 'http://{0}:{1}/api/health' -f $browserHost, $fastApiPort
    $backendProcess = $null
    try {
        Write-Step 'Starting FastAPI with the built frontend.'
        $appDirArgument = '"{0}"' -f (Join-Path $repoRoot 'app')
        $backendArguments = '-m uvicorn server.app:app --app-dir {0} --host {1} --port {2} --workers 1' -f $appDirArgument, $env:FASTAPI_HOST, $fastApiPort
        if ($env:RELOAD -eq 'true') { $backendArguments += ' --reload' }
        $backendArguments += ' --log-level info'
        $startParameters = @{
            FilePath = $venvPython
            ArgumentList = $backendArguments
            WorkingDirectory = $repoRoot
            NoNewWindow = $true
            PassThru = $true
            ErrorAction = 'Stop'
        }
        $backendProcess = Start-Process @startParameters

        Write-Info "Waiting up to 60 seconds for $healthUrl to report healthy API readiness."
        $ready = $false
        $lastReadinessError = 'health response was not ready'
        $readinessDeadline = (Get-Date).AddSeconds(60)
        while ((Get-Date) -lt $readinessDeadline) {
            $backendProcess.Refresh()
            if ($backendProcess.HasExited) {
                throw "Backend exited before readiness (exit code $($backendProcess.ExitCode))."
            }
            try {
                $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3 -ErrorAction Stop
                if ($health.application -eq 'FAIRS' -and $health.status -in @('ok', 'recovery')) {
                    $ready = $true
                    break
                }
                $lastReadinessError = "unexpected health response (application=$($health.application), status=$($health.status))"
            } catch {
                $lastReadinessError = $_.Exception.Message
            }
            Start-Sleep -Milliseconds 750
        }
        if (-not $ready) {
            throw "Backend did not become ready within 60 seconds at $healthUrl ($lastReadinessError)."
        }

        try {
            Start-Process -FilePath $appUrl -ErrorAction Stop | Out-Null
        } catch {
            Write-Info "The browser could not be opened automatically ($($_.Exception.Message)). Open $appUrl manually."
        }
        Write-Host ''
        Write-Ok 'FAIRS is ready.'
        Write-Host "Application: $appUrl"
        Write-Info 'This launcher console owns the running app. Press Ctrl+C here to stop FAIRS; closing the browser leaves it running.'

        $ctrlCRequested = $false
        try {
            while ($true) {
                $backendProcess.Refresh()
                if ($backendProcess.HasExited) { break }
                Start-Sleep -Milliseconds 300
            }
        } catch [System.Management.Automation.PipelineStoppedException] {
            $ctrlCRequested = $true
            Write-Info 'Ctrl+C received. Waiting for FastAPI lifespan shutdown.'
        } finally {
            Stop-OwnedApplicationProcessTree -RootProcessId $backendProcess.Id -Process $backendProcess -GraceSeconds 20
        }

        $backendProcess.Refresh()
        if ($ctrlCRequested) {
            Write-Ok 'FAIRS stopped after Ctrl+C.'
        } elseif ($backendProcess.ExitCode -eq 0) {
            Write-Info 'The backend process exited normally.'
        } else {
            throw "Backend stopped with exit code $($backendProcess.ExitCode)."
        }
        return $true
    } catch {
        $launchError = $_
        if ($null -ne $backendProcess) {
            Stop-OwnedApplicationProcessTree -RootProcessId $backendProcess.Id -Process $backendProcess -GraceSeconds 5
        }
        throw $launchError
    }
}

function Stop-OwnedApplicationProcessTree {
    param(
        [Parameter(Mandatory)][int]$RootProcessId,
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [int]$GraceSeconds = 15
    )
    if (-not $Process.HasExited) {
        Write-Info "Requesting the backend process to close and allowing up to $GraceSeconds seconds for shutdown."
        try { [void]$Process.CloseMainWindow() } catch { }
        try { [void]$Process.WaitForExit($GraceSeconds * 1000) } catch { }
    }

    # Uvicorn or a training worker can outlive an unexpectedly exited parent.
    # Inspect the original process tree even when the root has already exited.
    $rootExited = $Process.HasExited
    try {
        $processes = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    } catch {
        if ($rootExited) {
            Write-Info "Could not inspect descendants of exited backend PID $RootProcessId ($($_.Exception.Message)). Use the confirmed Stop all app processes action if anything remains."
            return
        }
        throw
    }
    $depthById = @{ $RootProcessId = 0 }
    do {
        $addedProcess = $false
        foreach ($record in $processes) {
            $processId = [int]$record.ProcessId
            $parentProcessId = [int]$record.ParentProcessId
            if (-not $depthById.ContainsKey($processId) -and $depthById.ContainsKey($parentProcessId)) {
                $depthById[$processId] = [int]$depthById[$parentProcessId] + 1
                $addedProcess = $true
            }
        }
    } while ($addedProcess)

    $ownedProcesses = @($processes | Where-Object {
            $depthById.ContainsKey([int]$_.ProcessId) -and
            (([int]$_.ProcessId -ne $RootProcessId) -or -not $rootExited)
        } | Sort-Object { $depthById[[int]$_.ProcessId] } -Descending)
    if ($ownedProcesses.Count -eq 0) { return }
    foreach ($ownedRecord in $ownedProcesses) {
        $processId = [int]$ownedRecord.ProcessId
        try { Stop-Process -Id $processId -Force -ErrorAction Stop } catch {
            if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
                Write-Fatal "Could not stop launcher-owned process PID $($processId): $($_.Exception.Message)"
            }
        }
    }
    try { [void]$Process.WaitForExit(5000) } catch { }
    $remainingOwnedIds = [Collections.Generic.List[int]]::new()
    $cleanupDeadline = (Get-Date).AddSeconds(5)
    do {
        $remainingOwnedIds.Clear()
        foreach ($processId in @($depthById.Keys)) {
            if ($rootExited -and [int]$processId -eq $RootProcessId) { continue }
            if (Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue) {
                [void]$remainingOwnedIds.Add([int]$processId)
            }
        }
        if ($remainingOwnedIds.Count -eq 0 -or (Get-Date) -ge $cleanupDeadline) { break }
        Start-Sleep -Milliseconds 100
    } while ($true)
    if ($remainingOwnedIds.Count -gt 0) {
        throw "Launcher-owned backend process tree did not stop after the bounded cleanup attempt. Remaining PIDs: $($remainingOwnedIds -join ', ')."
    }
    Write-Info 'Stopped the remaining launcher-owned backend process tree after graceful shutdown did not finish.'
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
    if (-not $script:LauncherInteractive) {
        throw "The destructive action '$Description' requires an interactive console; no files were changed."
    }
    Clear-LauncherProgress
    $confirmation = ([string](Read-Host "Continue to $($Description)? [y/N]")).Trim()
    if ($confirmation -notmatch '^(?i:y|yes)$') {
        Write-Info "Operation cancelled. No changes were made."
        return $false
    }
    return $true
}

function Stop-ApplicationProcesses {
    $processes = @(Get-ApplicationProcessRecords)
    if ($processes.Count -eq 0) {
        Write-Info 'No FAIRS application processes were found.'
        return
    }

    if (-not (Confirm-DestructiveAction "stop all FAIRS application processes ($($processes.Count) found)")) {
        return
    }

    Write-Info 'Stopping FAIRS application processes and their child processes.'
    foreach ($process in $processes) {
        Write-Host "  $($process.Name) (PID $($process.ProcessId))"
    }

    $processesById = @{}
    foreach ($process in $processes) {
        $processesById[[int]$process.ProcessId] = $process
    }
    $orderedProcesses = @($processes | Sort-Object @{
            Expression = {
                $depth = 0
                $parentProcessId = [int]$_.ParentProcessId
                while ($processesById.ContainsKey($parentProcessId) -and $depth -lt 100) {
                    $depth++
                    $parentProcessId = [int]$processesById[$parentProcessId].ParentProcessId
                }
                $depth
            }
            Descending = $true
        })
    $stopErrors = [Collections.Generic.List[string]]::new()

    foreach ($process in $orderedProcesses) {
        $processId = [int]$process.ProcessId
        if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { continue }
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
            if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
                [void]$stopErrors.Add("$($process.Name) (PID $processId): $($_.Exception.Message)")
            }
        }
    }

    $remainingProcesses = @()
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        Start-Sleep -Milliseconds 300
        $remainingProcesses = @(Get-ApplicationProcessRecords)
        if ($remainingProcesses.Count -eq 0) { break }
        foreach ($process in $remainingProcesses) {
            try {
                Stop-Process -Id ([int]$process.ProcessId) -Force -ErrorAction Stop
            } catch {
                if (Get-Process -Id ([int]$process.ProcessId) -ErrorAction SilentlyContinue) {
                    [void]$stopErrors.Add("$($process.Name) (PID $($process.ProcessId)): $($_.Exception.Message)")
                }
            }
        }
    }

    if ($remainingProcesses.Count -gt 0 -or $stopErrors.Count -gt 0) {
        $remainingSummary = @($remainingProcesses | ForEach-Object {
                "$($_.Name) (PID $($_.ProcessId))"
            }) -join ', '
        $errorSummary = @($stopErrors) -join '; '
        $details = @($remainingSummary, $errorSummary | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join ' '
        throw "Could not stop all FAIRS application processes. $details"
    }

    Write-Ok "Stopped $($processes.Count) FAIRS application process(es)."
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

function Clear-Cache {
    Import-DotEnv
    Assert-ApplicationStopped
    if (-not (Confirm-DestructiveAction 'clear disposable caches and app/server Python bytecode')) { return }

    $cachePaths = @(Get-CacheCleanupPaths)
    $progressId = Start-LauncherProgress -Activity 'FAIRS: clear caches' -Status "0 of $($cachePaths.Count) roots"
    try {
        for ($index = 0; $index -lt $cachePaths.Count; $index++) {
            $cachePath = $cachePaths[$index]
            Update-LauncherProgress -Id $progressId -Activity 'FAIRS: clear caches' -Status "$($index + 1) of $($cachePaths.Count): $cachePath" -PercentComplete ([int](($index + 1) * 100 / $cachePaths.Count))
            if ([IO.Path]::GetFullPath($cachePath).Equals([IO.Path]::GetFullPath($runtimeCacheDir), [StringComparison]::OrdinalIgnoreCase)) {
                Clear-RuntimeCacheDirectory
            }
            else {
                Remove-PathBestEffort $cachePath | Out-Null
            }
        }
    }
    finally {
        Complete-LauncherProgress $progressId
    }
    Write-Ok 'Disposable cache folders and app/server Python bytecode were cleared. Locked or protected entries were skipped.'
}

function Resolve-LauncherPath([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) {
        return [IO.Path]::GetFullPath($Path)
    }
    return [IO.Path]::GetFullPath((Join-Path $repoRoot $Path))
}

function Assert-DataCacheIsolation {
    $configuredDataDir = [Environment]::GetEnvironmentVariable('FAIRS_DATA_DIR', 'Process')
    if ([string]::IsNullOrWhiteSpace($configuredDataDir)) { return }

    $dataPath = [IO.Path]::GetFullPath((Resolve-LauncherPath $configuredDataDir.Trim()))
    $cachePath = [IO.Path]::GetFullPath($runtimeCacheDir)
    $dataPrefix = $dataPath.TrimEnd('\') + '\'
    $cachePrefix = $cachePath.TrimEnd('\') + '\'
    if ($dataPath.Equals($cachePath, [StringComparison]::OrdinalIgnoreCase) -or
        $dataPath.StartsWith($cachePrefix, [StringComparison]::OrdinalIgnoreCase) -or
        $cachePath.StartsWith($dataPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "FAIRS_DATA_DIR '$dataPath' overlaps the canonical disposable cache root '$cachePath'. Choose a persistent data directory outside runtimes/cache."
    }
}

function Get-UserDataTargets {
    Import-DotEnv

    $dataRoot = if ($env:FAIRS_DATA_DIR -and $env:FAIRS_DATA_DIR.Trim()) {
        Resolve-LauncherPath $env:FAIRS_DATA_DIR.Trim()
    } else {
        Join-Path $repoRoot 'data'
    }
    $logRoot = Join-Path $dataRoot 'logs'
    $databaseFiles = @(
        (Join-Path $dataRoot 'database.db'),
        (Join-Path $dataRoot 'database.db-shm'),
        (Join-Path $dataRoot 'database.db-wal')
    )
    $externalDatabase = $false
    $databaseConfigPath = Join-Path $dataRoot 'database-config.json'
    if (Test-Path -LiteralPath $databaseConfigPath -PathType Leaf) {
        try {
            $databaseConfig = Get-Content -LiteralPath $databaseConfigPath -Raw | ConvertFrom-Json
            if (($databaseConfig.schema_version -isnot [int] -and $databaseConfig.schema_version -isnot [long]) -or
                $databaseConfig.schema_version -ne 1) {
                throw 'Unsupported database configuration schema version.'
            }
            if ($databaseConfig.backend -eq 'sqlite' -and $databaseConfig.sqlite.path) {
                $sqlitePath = [IO.Path]::GetFullPath([string]$databaseConfig.sqlite.path)
                $databaseFiles = @($sqlitePath, "$sqlitePath-shm", "$sqlitePath-wal")
            } elseif ($databaseConfig.backend -eq 'postgresql' -and
                $databaseConfig.postgresql.engine -eq 'postgresql+psycopg') {
                $externalDatabase = $true
                $databaseFiles = @()
            } else {
                throw 'Unknown database backend or missing SQLite path.'
            }
        } catch {
            throw "Cannot determine the active database from '$databaseConfigPath'; refusing data removal."
        }
    }

    return [pscustomobject]@{
        DatabaseFiles = $databaseFiles
        CheckpointRoot = Join-Path $dataRoot 'checkpoints'
        LogRoot = $logRoot
        ExternalDatabase = $externalDatabase
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
    if (-not (Confirm-DestructiveAction 'remove local runtimes, caches, dependencies, and build outputs')) { return }

    $paths = @(
        $runtimeRoot,
        $venvDir,
        (Join-Path $clientDir 'node_modules'),
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
    Write-Ok 'Application runtimes, caches, dependencies, and build outputs removed. Dependency lockfiles and user data were preserved.'
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
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Install'; Label = 'Install / update dependencies'; Description = 'Prepare local runtimes and build the frontend'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Rebuild'; Label = 'Rebuild frontend'; Description = 'Build the frontend without updating dependencies'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Database'; Label = 'Create / upgrade database'; Description = 'Create the selected database and apply migrations'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SETUP & VALIDATION'; Key = 'Tests'; Label = 'Run test suite'; Description = 'Execute automated checks'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SOURCE CONTROL'; Key = 'Check'; Label = 'Check for updates'; Description = 'Report local main-branch update status only'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'SOURCE CONTROL'; Key = 'Update'; Label = 'Update application'; Description = 'Pull application changes from the main branch'; Color = [ConsoleColor]::Yellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Logs'; Label = 'Remove logs'; Description = 'Delete application log files'; Color = [ConsoleColor]::DarkYellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Cache'; Label = 'Clear cache'; Description = 'Remove disposable caches and app/server Python bytecode'; Color = [ConsoleColor]::DarkYellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Checkpoints'; Label = 'Remove checkpoints'; Description = 'Delete saved checkpoints only'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'AllData'; Label = 'Remove all data'; Description = 'Delete local database and logs, preserving checkpoints'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Uninstall'; Label = 'Uninstall application'; Description = 'Remove local runtimes, caches, dependencies, and build outputs'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'StopProcesses'; Label = 'Stop all app processes'; Description = 'Terminate the backend, frontend, and child processes'; Color = [ConsoleColor]::Red }
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
                    'Launch' { [void](Start-Application) }
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
                    'StopProcesses' { Stop-ApplicationProcesses }
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

if ($Launch) {
    $launchExitCode = 0
    try {
        Set-CacheEnvironment
        if (-not (Start-Application)) { $launchExitCode = 2 }
    } catch {
        Write-Fatal "Launch failed: $($_.Exception.Message)"
        $launchExitCode = 1
    } finally {
        Clear-LauncherProgress
    }
    exit $launchExitCode
}

Set-CacheEnvironment
Show-Menu
Clear-LauncherProgress
