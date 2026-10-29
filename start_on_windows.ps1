# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

# -----------------------------------------------------------------------------
# Launcher paths and runtime locations
# -----------------------------------------------------------------------------
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Launch,
    [ValidateSet('Cache', 'Uninstall')]
    [string]$Action,
    [switch]$CompleteRemoval
)

$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 started from PowerShell 7 inherits PowerShell 7 module paths,
# which hides built-in cmdlets such as Get-FileHash; keep only 5.1-compatible entries.
if ($PSVersionTable.PSEdition -eq 'Desktop' -and $env:PSModulePath) {
    $env:PSModulePath = (($env:PSModulePath -split ';') | Where-Object {
        $_ -and $_ -notmatch '[\\/]PowerShell[\\/]'
    }) -join ';'
}
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
function Write-LaunchTiming {
    param(
        [Parameter(Mandatory)][string]$Phase,
        [Parameter(Mandatory)][long]$ElapsedMilliseconds
    )
    Write-Host ('[TIME] {0,-42} {1,8} ms' -f "$($Phase):", $ElapsedMilliseconds) -ForegroundColor Gray
}
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

function New-CleanupTarget {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$AllowedRoot,
        [ValidateSet('Tree', 'File')][string]$Mode = 'Tree',
        [switch]$KeepRoot,
        [string[]]$PreserveNames = @()
    )
    [pscustomobject]@{
        Path = $Path
        AllowedRoot = $AllowedRoot
        Mode = $Mode
        KeepRoot = [bool]$KeepRoot
        PreserveNames = @($PreserveNames)
    }
}

function Reset-CleanupDiscoveryNotes {
    if ($null -eq $script:CleanupDiscoveryNotes) {
        $script:CleanupDiscoveryNotes = [Collections.Generic.List[string]]::new()
    } else {
        $script:CleanupDiscoveryNotes.Clear()
    }
}

function Add-CleanupDiscoverySkip([string]$Message) {
    if ($null -eq $script:CleanupDiscoveryNotes) {
        $script:CleanupDiscoveryNotes = [Collections.Generic.List[string]]::new()
    }
    [void]$script:CleanupDiscoveryNotes.Add($Message)
}

function Test-CleanupPathWithinRoot([string]$Path, [string]$AllowedRoot, [switch]$AllowEqual) {
    if ([string]::IsNullOrWhiteSpace($Path) -or [string]::IsNullOrWhiteSpace($AllowedRoot)) {
        throw 'Cleanup paths and allowed roots must not be empty.'
    }
    $fullPath = [IO.Path]::GetFullPath($Path)
    $fullRoot = [IO.Path]::GetFullPath($AllowedRoot)
    if ($fullPath.Equals($fullRoot, [StringComparison]::OrdinalIgnoreCase)) {
        if ($AllowEqual) { return $fullPath }
        throw "Refusing to remove an allowed root itself: '$fullPath'."
    }
    $rootPrefix = $fullRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Cleanup target '$fullPath' is outside its recognized root '$fullRoot'."
    }
    return $fullPath
}

function Assert-NoReparseAncestors([string]$Path, [string]$AllowedRoot) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $fullRoot = [IO.Path]::GetFullPath($AllowedRoot)
    [void](Test-CleanupPathWithinRoot -Path $fullPath -AllowedRoot $fullRoot)
    $current = Split-Path -Parent $fullPath
    while ($current) {
        $item = Get-Item -LiteralPath $current -Force -ErrorAction Stop
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Cleanup path traverses a symbolic link or junction: '$current'."
        }
        $parent = Split-Path -Parent $current
        if (-not $parent -or $parent.Equals($current, [StringComparison]::OrdinalIgnoreCase)) { return }
        $current = $parent
    }
    throw "Cannot validate the ancestor chain for cleanup path '$fullPath'."
}

function Test-CleanupDirectorySafeToScan([string]$Path) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    try {
        Assert-NoReparseAncestors -Path (Join-Path $fullPath '.fairs-cleanup-scan-probe') -AllowedRoot $fullPath
        return $true
    } catch {
        Add-CleanupDiscoverySkip "$fullPath (directory scan skipped: $($_.Exception.Message))"
        return $false
    }
}

function Get-CleanupInventory {
    param([Parameter(Mandatory)][AllowNull()][AllowEmptyCollection()][object[]]$Targets)

    $entries = [Collections.Generic.List[object]]::new()
    $skipped = [Collections.Generic.List[string]]::new()
    $failed = [Collections.Generic.List[string]]::new()
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($note in @($script:CleanupDiscoveryNotes)) { [void]$skipped.Add($note) }
    if ($null -ne $script:CleanupDiscoveryNotes) { $script:CleanupDiscoveryNotes.Clear() }

    foreach ($target in @($Targets)) {
        try {
            $fullPath = Test-CleanupPathWithinRoot -Path $target.Path -AllowedRoot $target.AllowedRoot -AllowEqual:$target.KeepRoot
            Assert-NoReparseAncestors -Path $fullPath -AllowedRoot $target.AllowedRoot
            $rootItem = Get-Item -LiteralPath $fullPath -Force -ErrorAction Stop
        }
        catch {
            if ($_.CategoryInfo.Category -eq [System.Management.Automation.ErrorCategory]::ObjectNotFound) {
                [void]$skipped.Add("$($target.Path) (already absent)")
            } else {
                [void]$failed.Add("$($target.Path) ($($_.Exception.Message))")
            }
            continue
        }

        if ($target.Mode -eq 'File' -and $rootItem.PSIsContainer) {
            [void]$failed.Add("$fullPath (expected a file but found a directory)")
            continue
        }
        if ($target.KeepRoot -and (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            [void]$skipped.Add("$fullPath (root is a symbolic link or junction)")
            continue
        }

        $pending = [Collections.Generic.Stack[object]]::new()
        if ($target.Mode -eq 'File') {
            $pending.Push([pscustomobject]@{ Item = $rootItem; Visited = $true; IsRoot = $true })
        } elseif (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            [void]$skipped.Add("$fullPath (refusing to traverse a symbolic link or junction)")
            continue
        } else {
            $pending.Push([pscustomobject]@{ Item = $rootItem; Visited = $false; IsRoot = $true })
        }

        while ($pending.Count -gt 0) {
            $work = $pending.Pop()
            $item = $work.Item
            $isReparsePoint = (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
            if ($item.PSIsContainer -and -not $isReparsePoint -and -not $work.Visited) {
                $pending.Push([pscustomobject]@{ Item = $item; Visited = $true; IsRoot = $work.IsRoot })
                try {
                    $children = @(Get-ChildItem -LiteralPath $item.FullName -Force -ErrorAction Stop)
                    foreach ($child in $children) {
                        if ($work.IsRoot -and $child.Name -in $target.PreserveNames) {
                            [void]$skipped.Add("$($child.FullName) (preserved marker)")
                            continue
                        }
                        $pending.Push([pscustomobject]@{ Item = $child; Visited = $false; IsRoot = $false })
                    }
                } catch {
                    [void]$failed.Add("$($item.FullName) ($($_.Exception.Message))")
                }
                continue
            }

            if ($work.IsRoot -and $target.KeepRoot) { continue }
            try {
                $candidatePath = Test-CleanupPathWithinRoot -Path $item.FullName -AllowedRoot $target.AllowedRoot
                if ($seen.Add($candidatePath)) {
                    [void]$entries.Add([pscustomobject]@{
                        Path = $candidatePath
                        AllowedRoot = $target.AllowedRoot
                        IsDirectory = [bool]$item.PSIsContainer
                        IsReparsePoint = [bool]$isReparsePoint
                        ReportPath = $fullPath
                        ReportScope = if ($target.Mode -eq 'File') { 'file' } elseif ($target.KeepRoot) { 'contents of' } else { 'tree' }
                    })
                }
            } catch {
                [void]$failed.Add("$($item.FullName) ($($_.Exception.Message))")
            }
        }
    }

    $orderedEntries = @($entries | Sort-Object @{ Expression = { $_.Path.Length }; Descending = $true }, @{ Expression = { $_.Path.ToUpperInvariant() }; Descending = $false })
    return [pscustomobject]@{ Entries = $orderedEntries; Skipped = @($skipped); Failed = @($failed) }
}

function Write-CleanupPreview {
    param([Parameter(Mandatory)]$Inventory, [string]$Title = 'Cleanup preview')
    Write-Host "[INFO] $Title" -ForegroundColor Cyan
    if ($Inventory.Entries.Count -eq 0) { Write-Host '  No existing paths will be removed.' -ForegroundColor DarkGray }
    foreach ($location in @(Get-CleanupReportLocations -Entries $Inventory.Entries)) {
        $verb = if ($location.Scope -eq 'contents of') { 'REMOVE CONTENTS OF' } elseif ($location.Scope -eq 'file') { 'REMOVE FILE' } else { 'REMOVE TREE' }
        Write-Host "  [$verb] $($location.Path) ($($location.Count) paths)" -ForegroundColor DarkYellow
    }
    foreach ($path in $Inventory.Skipped) { Write-Host "  [SKIP]   $path" -ForegroundColor DarkGray }
    foreach ($path in $Inventory.Failed) { Write-Host "  [FAIL]   $path" -ForegroundColor Red }
}

function Get-CleanupReportLocations {
    param([Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Entries)
    $locations = @{}
    foreach ($entry in $Entries) {
        $path = if ($entry.PSObject.Properties['ReportPath']) { $entry.ReportPath } else { $entry.Path }
        $scope = if ($entry.PSObject.Properties['ReportScope']) { $entry.ReportScope } else { 'path' }
        if (-not $locations.ContainsKey($path)) {
            $locations[$path] = [pscustomobject]@{ Path = $path; Scope = $scope; Count = 0 }
        }
        $locations[$path].Count++
    }
    return @($locations.Values | Sort-Object Path)
}

function Invoke-CleanupInventory {
    param(
        [Parameter(Mandatory)]$Inventory,
        [string]$Activity = 'FAIRS: remove files',
        [switch]$WhatIf
    )

    $removed = [Collections.Generic.List[string]]::new()
    $removedEntries = [Collections.Generic.List[object]]::new()
    $skipped = [Collections.Generic.List[string]]::new()
    $failed = [Collections.Generic.List[string]]::new()
    foreach ($path in $Inventory.Skipped) { [void]$skipped.Add($path) }
    foreach ($path in $Inventory.Failed) { [void]$failed.Add($path) }

    $progressId = $null
    try {
        if ($Inventory.Entries.Count -gt 0) { $progressId = Start-LauncherProgress -Activity $Activity -Status "0 of $($Inventory.Entries.Count) paths" }
        for ($index = 0; $index -lt $Inventory.Entries.Count; $index++) {
            $entry = $Inventory.Entries[$index]
            if ($null -ne $progressId) {
                Update-LauncherProgress -Id $progressId -Activity $Activity -Status "$($index + 1) of $($Inventory.Entries.Count): $([IO.Path]::GetFileName($entry.Path))" -PercentComplete ([int](($index + 1) * 100 / [Math]::Max(1, $Inventory.Entries.Count)))
            }
            if ($WhatIf) { continue }
            try {
                [void](Test-CleanupPathWithinRoot -Path $entry.Path -AllowedRoot $entry.AllowedRoot)
                Assert-NoReparseAncestors -Path $entry.Path -AllowedRoot $entry.AllowedRoot
                $item = Get-Item -LiteralPath $entry.Path -Force -ErrorAction Stop
                $isReparsePoint = (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
                if ($isReparsePoint -and $item.PSIsContainer) {
                    [IO.Directory]::Delete($entry.Path, $false)
                } elseif ($item.PSIsContainer) {
                    [IO.Directory]::Delete($entry.Path, $false)
                } else {
                    if (-not $isReparsePoint -and ($item.Attributes -band [IO.FileAttributes]::ReadOnly) -ne 0) {
                        [IO.File]::SetAttributes($entry.Path, $item.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly))
                    }
                    [IO.File]::Delete($entry.Path)
                }
                [void]$removed.Add($entry.Path)
                [void]$removedEntries.Add($entry)
            } catch {
                if (-not (Test-Path -LiteralPath $entry.Path -PathType Any -ErrorAction SilentlyContinue)) {
                    [void]$skipped.Add("$($entry.Path) (no longer present)")
                } else {
                    [void]$failed.Add("$($entry.Path) ($($_.Exception.Message))")
                }
            }
        }
    } finally {
        if ($null -ne $progressId) { Complete-LauncherProgress $progressId }
    }
    return [pscustomobject]@{
        Removed = @($removed)
        RemovedLocations = @(Get-CleanupReportLocations -Entries @($removedEntries))
        Skipped = @($skipped)
        Failed = @($failed)
        Planned = @($Inventory.Entries | ForEach-Object { $_.Path })
    }
}

function Write-CleanupSummary([string]$Action, $Result) {
    Write-Host "[INFO] $Action summary: $($Result.Removed.Count) cleaned, $($Result.Skipped.Count) skipped, $($Result.Failed.Count) failed." -ForegroundColor Cyan
    foreach ($location in @($Result.RemovedLocations)) {
        Write-Host "  [CLEANED] $($location.Path) ($($location.Count) paths)" -ForegroundColor Green
    }
    foreach ($path in $Result.Skipped) { Write-Host "  [SKIPPED] $path" -ForegroundColor DarkGray }
    foreach ($path in $Result.Failed) { Write-Host "  [FAILED]  $path" -ForegroundColor Red }
}

function Remove-LauncherPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path,
        [string]$AllowedRoot,
        [switch]$KeepRoot,
        [string[]]$PreserveNames = @('.gitkeep'),
        [switch]$Strict,
        [switch]$WhatIf,
        [string]$Activity = 'FAIRS: remove files'
    )

    $resolvedAllowedRoot = if ($AllowedRoot) { $AllowedRoot } else { Split-Path -Parent ([IO.Path]::GetFullPath($Path)) }
    if (-not $resolvedAllowedRoot) { $resolvedAllowedRoot = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path)) }
    $target = New-CleanupTarget -Path $Path -AllowedRoot $resolvedAllowedRoot -Mode 'Tree' -KeepRoot:$KeepRoot -PreserveNames $PreserveNames
    $inventory = Get-CleanupInventory -Targets @($target)
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity $Activity -WhatIf:$WhatIf
    if ($Strict -and ($result.Failed.Count -gt 0 -or ($result.Skipped | Where-Object { $_ -notlike '*(already absent)' }).Count -gt 0)) {
        throw "Removal of '$Path' was incomplete. $($result.Skipped.Count) path(s) skipped and $($result.Failed.Count) path(s) failed."
    }
    return [pscustomobject]@{
        Target = [IO.Path]::GetFullPath($Path)
        Path = [IO.Path]::GetFullPath($Path)
        Planned = $result.Planned.Count
        PlannedCount = $result.Planned.Count
        PlannedPaths = $result.Planned
        Removed = $result.Removed.Count
        RemovedCount = $result.Removed.Count
        RemovedPaths = $result.Removed
        Preserved = @($result.Skipped | Where-Object { $_ -like '*(preserved marker)' }).Count
        PreservedEntries = @($result.Skipped | Where-Object { $_ -like '*(preserved marker)' })
        Skipped = $result.Skipped.Count
        SkippedPaths = $result.Skipped
        EnumerationErrors = $result.Failed
        FailedPaths = $result.Failed
        WhatIf = [bool]$WhatIf
    }
}

function Remove-PathBestEffort([string]$Path, [string]$AllowedRoot) {
    $result = Remove-LauncherPath -Path $Path -AllowedRoot $AllowedRoot -Activity "FAIRS: remove $([IO.Path]::GetFileName($Path))"
    return $result.FailedPaths.Count -eq 0 -and @($result.SkippedPaths | Where-Object { $_ -notlike '*(already absent)' }).Count -eq 0
}

function Add-CleanupTargetIfPresent {
    param([Collections.Generic.List[object]]$Targets, [string]$Path, [string]$AllowedRoot, [string]$Mode = 'Tree', [switch]$KeepRoot, [string[]]$PreserveNames = @())
    if (Test-Path -LiteralPath $Path -PathType Any) {
        [void]$Targets.Add((New-CleanupTarget -Path $Path -AllowedRoot $AllowedRoot -Mode $Mode -KeepRoot:$KeepRoot -PreserveNames $PreserveNames))
    }
}

function Get-DiscoveredCacheTargets {
    param([string[]]$Roots)
    $recognizedDirectoryNames = @('__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache', '.cache', '.vite', 'htmlcov')
    $knownBuildOutputPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in @(
        (Join-Path $clientDir 'dist'), (Join-Path $clientDir 'dist-ssr'),
        (Join-Path $serverDir 'build'), (Join-Path $serverDir 'dist')
    )) { [void]$knownBuildOutputPaths.Add([IO.Path]::GetFullPath($path)) }
    $targets = [Collections.Generic.List[object]]::new()
    foreach ($scanRoot in $Roots) {
        if (-not (Test-Path -LiteralPath $scanRoot -PathType Container)) { continue }
        if (-not (Test-CleanupDirectorySafeToScan -Path $scanRoot)) { continue }
        $pending = [Collections.Generic.Stack[string]]::new()
        $pending.Push([IO.Path]::GetFullPath($scanRoot))
        while ($pending.Count -gt 0) {
            $current = $pending.Pop()
            try {
                $children = @(Get-ChildItem -LiteralPath $current -Force -ErrorAction Stop)
            } catch {
                Add-CleanupDiscoverySkip "$current (cache discovery skipped: $($_.Exception.Message))"
                continue
            }
            foreach ($child in $children) {
                if ($child.PSIsContainer) {
                    if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                        if ($child.Name -in $recognizedDirectoryNames) {
                            [void]$targets.Add((New-CleanupTarget -Path $child.FullName -AllowedRoot $scanRoot))
                        }
                        continue
                    }
                    if ($child.Name -in $recognizedDirectoryNames) {
                        [void]$targets.Add((New-CleanupTarget -Path $child.FullName -AllowedRoot $scanRoot))
                    } elseif ($child.Name -eq '.git' -or $knownBuildOutputPaths.Contains([IO.Path]::GetFullPath($child.FullName))) {
                        continue
                    } else {
                        $pending.Push($child.FullName)
                    }
                    continue
                }
                if ($child.Extension -in @('.pyc', '.pyo', '.tsbuildinfo') -or $child.Name -like '.coverage*') {
                    [void]$targets.Add((New-CleanupTarget -Path $child.FullName -AllowedRoot $scanRoot -Mode 'File'))
                }
            }
        }
    }
    return @($targets)
}

function Get-CacheCleanupTargets {
    Assert-DataCacheIsolation
    $targets = [Collections.Generic.List[object]]::new()
    Add-CleanupTargetIfPresent $targets $runtimeCacheDir $runtimeRoot -KeepRoot -PreserveNames @('.gitkeep')
    $scanRoots = @($serverDir, $clientDir, $testsDir)
    foreach ($target in @(Get-DiscoveredCacheTargets -Roots $scanRoots)) { [void]$targets.Add($target) }

    foreach ($path in @(
        (Join-Path $clientDir 'dist'), (Join-Path $clientDir 'dist-ssr'),
        (Join-Path $serverDir 'build'), (Join-Path $serverDir 'dist')
    )) { Add-CleanupTargetIfPresent $targets $path $repoRoot }
    if (Test-Path -LiteralPath $serverDir -PathType Container) {
        try {
            foreach ($entry in @(Get-ChildItem -LiteralPath $serverDir -Directory -Force -ErrorAction Stop | Where-Object { $_.Name -like '*.egg-info' })) {
                [void]$targets.Add((New-CleanupTarget -Path $entry.FullName -AllowedRoot $serverDir))
            }
        } catch { Add-CleanupDiscoverySkip "$serverDir (build-artifact discovery skipped: $($_.Exception.Message))" }
    }
    Add-KnownTemporaryTargets -Targets $targets
    Add-QaOutputTargets -Targets $targets
    $uniqueTargets = @(Remove-DuplicateCleanupTargets -Targets @($targets))
    Assert-NoPersistentDataTreeOverlap -Targets $uniqueTargets
    Assert-NoDatabaseCleanupOverlap -Targets $uniqueTargets
    return $uniqueTargets
}

function Remove-DuplicateCleanupTargets([object[]]$Targets) {
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($target in $Targets) {
        $key = [IO.Path]::GetFullPath($target.Path)
        if ($seen.Add($key)) { $target }
    }
}

function Add-KnownTemporaryTargets {
    param([Collections.Generic.List[object]]$Targets)
    foreach ($path in @(
        (Join-Path $pythonDir 'python.zip'),
        (Join-Path $uvDir 'uv.zip'),
        (Join-Path $nodeDir 'node.zip')
    )) { Add-CleanupTargetIfPresent $Targets $path $runtimeRoot -Mode 'File' }

    $settingsDir = Join-Path $repoRoot 'settings'
    if ((Test-Path -LiteralPath $settingsDir -PathType Container) -and (Test-CleanupDirectorySafeToScan -Path $settingsDir)) {
        try {
            foreach ($file in @(Get-ChildItem -LiteralPath $settingsDir -File -Force -Filter '.env.*.tmp' -ErrorAction Stop)) {
                [void]$Targets.Add((New-CleanupTarget -Path $file.FullName -AllowedRoot $settingsDir -Mode 'File'))
            }
        } catch { Add-CleanupDiscoverySkip "$settingsDir (temporary-file discovery skipped: $($_.Exception.Message))" }
    }

    $dataRoot = if ($env:FAIRS_DATA_DIR -and $env:FAIRS_DATA_DIR.Trim()) { Resolve-LauncherPath $env:FAIRS_DATA_DIR.Trim() } else { Join-Path $repoRoot 'data' }
    $databaseTemporaryPattern = '^\.database-config\.json\..+\.tmp$'
    if ((Test-Path -LiteralPath $dataRoot -PathType Container) -and (Test-CleanupDirectorySafeToScan -Path $dataRoot)) {
        try {
            foreach ($file in @(Get-ChildItem -LiteralPath $dataRoot -File -Force -ErrorAction Stop | Where-Object { $_.Name -match $databaseTemporaryPattern })) {
                [void]$Targets.Add((New-CleanupTarget -Path $file.FullName -AllowedRoot $dataRoot -Mode 'File'))
            }
        } catch { Add-CleanupDiscoverySkip "$dataRoot (temporary-file discovery skipped: $($_.Exception.Message))" }
    }

    $checkpointRoot = Join-Path $dataRoot 'checkpoints'
    if ((Test-Path -LiteralPath $checkpointRoot -PathType Container) -and (Test-CleanupDirectorySafeToScan -Path $checkpointRoot)) {
        $pending = [Collections.Generic.Stack[string]]::new()
        $pending.Push($checkpointRoot)
        while ($pending.Count -gt 0) {
            $current = $pending.Pop()
            try { $children = @(Get-ChildItem -LiteralPath $current -Force -ErrorAction Stop) }
            catch { Add-CleanupDiscoverySkip "$current (temporary-file discovery skipped: $($_.Exception.Message))"; continue }
            foreach ($child in $children) {
                if ($child.PSIsContainer) {
                    if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                        Add-CleanupDiscoverySkip "$($child.FullName) (temporary-file discovery skipped: symbolic link or junction)"
                        continue
                    }
                    if ($current.Equals($checkpointRoot, [StringComparison]::OrdinalIgnoreCase) -and
                        $child.Name -match '^\..+\.(staging|backup|publish)-[0-9a-f]{32}$') {
                        [void]$Targets.Add((New-CleanupTarget -Path $child.FullName -AllowedRoot $dataRoot))
                    } else { $pending.Push($child.FullName) }
                    continue
                }
                if ($child.Name -match '^\.(complete|configuration\.json|session_history\.json|replay_memory\.pkl|saved_model\.keras|strategy\.keras)\.[0-9a-f]{32}\.tmp(?:\.keras)?$') {
                    [void]$Targets.Add((New-CleanupTarget -Path $child.FullName -AllowedRoot $dataRoot -Mode 'File'))
                }
            }
        }
    }
}

function Add-QaOutputTargets {
    param([Collections.Generic.List[object]]$Targets)
    $qaRoot = Join-Path $repoRoot 'assets\QA'
    Add-CleanupTargetIfPresent $Targets (Join-Path $qaRoot 'frontend-e2e-artifacts') $qaRoot
    if ((Test-Path -LiteralPath $qaRoot -PathType Container) -and (Test-CleanupDirectorySafeToScan -Path $qaRoot)) {
        try {
            $qaOutputPatterns = @(
                'frontend-e2e-junit-*.xml', 'frontend-viewport-1100-*.png', 'frontend-viewport-1099-*.png',
                'fairs_startup_loading.png', 'fairs_startup_loading_*x*.png',
                'val12-inference-history-replay.png', 'val13-inference-replacement-rollback.png',
                'val14-inference-restart-recovered.png', 'val15-strategy-suggestion.png', 'val17-*.png'
            )
            foreach ($file in @(Get-ChildItem -LiteralPath $qaRoot -File -Force -ErrorAction Stop | Where-Object {
                $candidateName = $_.Name
                @($qaOutputPatterns | Where-Object { $candidateName -like $_ }).Count -gt 0
            })) {
                [void]$Targets.Add((New-CleanupTarget -Path $file.FullName -AllowedRoot $qaRoot -Mode 'File'))
            }
        } catch { Add-CleanupDiscoverySkip "$qaRoot (test-output discovery skipped: $($_.Exception.Message))" }
    }
}

function Assert-NoDatabaseCleanupOverlap {
    param([AllowEmptyCollection()][object[]]$Targets)
    $data = Get-UserDataTargets
    if ($data.DatabaseResolutionError) { throw $data.DatabaseResolutionError }
    foreach ($databaseFile in $data.DatabaseFiles) {
        $databasePath = [IO.Path]::GetFullPath($databaseFile)
        foreach ($target in $Targets) {
            $targetPath = [IO.Path]::GetFullPath($target.Path)
            $targetPrefix = $targetPath.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
            if ($databasePath.Equals($targetPath, [StringComparison]::OrdinalIgnoreCase) -or
                ($target.Mode -eq 'Tree' -and $databasePath.StartsWith($targetPrefix, [StringComparison]::OrdinalIgnoreCase))) {
                throw "Cleanup target '$targetPath' overlaps the configured persistent database '$databasePath'; refusing cache or standard uninstall cleanup."
            }
        }
    }
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

function Import-DotEnv([switch]$NoCreate) {
    if (-not $NoCreate) { Initialize-EnvironmentFile }
    $loadedKeys = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $databaseEnvironmentKeys = @(
        'DATABASE_URL', 'EMBEDDED_DATABASE', 'DATABASE_ENGINE', 'DATABASE_HOST',
        'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USERNAME', 'DATABASE_PASSWORD',
        'DATABASE_SSL', 'DATABASE_SSL_CA', 'DATABASE_CONNECT_TIMEOUT',
        'DATABASE_INSERT_BATCH_SIZE'
    )
    if (Test-Path -LiteralPath $envFile -PathType Leaf) {
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
    if (-not $NoCreate -and $missingVariables.Count -gt 0) {
        throw "settings\.env is missing required launcher variable(s): $($missingVariables -join ', '). Update it from settings\.env.example."
    }
    if (-not $NoCreate) { Assert-DataCacheIsolation }
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
    $launchStopwatch = [Diagnostics.Stopwatch]::StartNew()
    $portPreflightStarted = $launchStopwatch.ElapsedMilliseconds
    try {
        Import-DotEnv
        $fastApiPort = [int]$env:FASTAPI_PORT
        $portPreflightReady = Resolve-LaunchPortConflicts -BackendPort $fastApiPort
        if ($portPreflightReady) { Assert-SingleWorkerConfiguration }
    } finally {
        Write-LaunchTiming -Phase 'Environment and port preflight' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $portPreflightStarted)
    }
    if (-not $portPreflightReady) { return $false }

    $runtimeSetupStarted = $launchStopwatch.ElapsedMilliseconds
    try {
        Ensure-PortableRuntimes
        Set-CacheEnvironment
        $env:UV_PROJECT_ENVIRONMENT = $venvDir
        $env:UV_LINK_MODE = 'copy'
        Remove-Item Env:PYTHONHOME, Env:PYTHONPATH, Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue
    } finally {
        Write-LaunchTiming -Phase 'Portable runtime and environment setup' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $runtimeSetupStarted)
    }

    $backendDependenciesStarted = $launchStopwatch.ElapsedMilliseconds
    try {
        if (-not (Test-BackendDependenciesCurrent)) {
            Write-Step 'Backend dependency state is missing or stale; synchronizing backend dependencies.'
            Sync-BackendDependencies -InstallationType 'Standard'
        } else {
            Write-Ok 'Backend dependencies are current; skipped backend synchronization.'
        }
    } finally {
        Write-LaunchTiming -Phase 'Backend dependency check and setup' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $backendDependenciesStarted)
    }

    $frontendDependenciesStarted = $launchStopwatch.ElapsedMilliseconds
    try {
        if (-not (Test-FrontendDependenciesCurrent)) {
            Write-Step 'Frontend dependency state is missing or stale; synchronizing frontend dependencies.'
            Sync-FrontendDependencies
        } else {
            Write-Ok 'Frontend dependencies are current; skipped frontend dependency synchronization.'
        }
    } finally {
        Write-LaunchTiming -Phase 'Frontend dependency check and setup' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $frontendDependenciesStarted)
    }

    $frontendBuildStarted = $launchStopwatch.ElapsedMilliseconds
    try {
        if (-not (Test-FrontendBuildCurrent)) {
            Write-Step 'Frontend source or build inputs changed; rebuilding frontend.'
            Invoke-FrontendBuild
        } else {
            Write-Ok 'Frontend build is current; skipped frontend build.'
        }
    } finally {
        Write-LaunchTiming -Phase 'Frontend production build check' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $frontendBuildStarted)
    }

    $launchPreparationStarted = $launchStopwatch.ElapsedMilliseconds
    try {
        if ($env:RELOAD -eq 'true') {
            Write-Info 'RELOAD=true is development-only; reloads discard in-memory training jobs and inference sessions.'
        }
        $browserHost = ([string]$env:FASTAPI_HOST).Trim()
        if ($browserHost -in @('0.0.0.0', '::', '[::]')) { $browserHost = '127.0.0.1' }
        if ($browserHost.Contains(':') -and -not $browserHost.StartsWith('[')) { $browserHost = "[$browserHost]" }
        $appUrl = 'http://{0}:{1}/' -f $browserHost, $fastApiPort
        $healthUrl = 'http://{0}:{1}/api/health' -f $browserHost, $fastApiPort
        $backendProcess = $null
    } finally {
        Write-LaunchTiming -Phase 'Backend launch preparation' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $launchPreparationStarted)
    }
    try {
        $backendProcessStartStarted = $launchStopwatch.ElapsedMilliseconds
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
            if (-not $backendProcess) { throw 'FastAPI process could not be started.' }
        } finally {
            Write-LaunchTiming -Phase 'Backend process start' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $backendProcessStartStarted)
        }

        $readinessStarted = $launchStopwatch.ElapsedMilliseconds
        try {
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

            $launchStopwatch.Stop()
            Write-LaunchTiming -Phase 'Total time to application readiness' -ElapsedMilliseconds $launchStopwatch.ElapsedMilliseconds

            try {
                Start-Process -FilePath $appUrl -ErrorAction Stop | Out-Null
            } catch {
                Write-Info "The browser could not be opened automatically ($($_.Exception.Message)). Open $appUrl manually."
            }
            Write-Host ''
            Write-Ok 'FAIRS is ready.'
            Write-Host "Application: $appUrl"
            Write-Info 'This launcher console owns the running app. Press Ctrl+C here to stop FAIRS; closing the browser leaves it running.'
        } finally {
            Write-LaunchTiming -Phase 'API and frontend readiness checks' -ElapsedMilliseconds ($launchStopwatch.ElapsedMilliseconds - $readinessStarted)
        }

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
function Confirm-DestructiveAction([string]$Description, [string]$RequiredText) {
    if (-not $script:LauncherInteractive) {
        throw "The destructive action '$Description' requires an interactive console; no files were changed."
    }
    Clear-LauncherProgress
    if ($RequiredText) {
        $confirmation = ([string](Read-Host "Type $RequiredText to $Description")).Trim()
        if ($confirmation -cne $RequiredText) {
            Write-Info 'Operation cancelled. No changes were made.'
            return $false
        }
        return $true
    }
    $confirmation = ([string](Read-Host "Continue to $($Description)? [y/N]")).Trim()
    if ($confirmation -notmatch '^(?i:y|yes)$') {
        Write-Info "Operation cancelled. No changes were made."
        return $false
    }
    return $true
}

function Invoke-ConfirmedCleanup {
    param(
        [Parameter(Mandatory)][AllowNull()][AllowEmptyCollection()][object[]]$Targets,
        [Parameter(Mandatory)][string]$Description,
        [Parameter(Mandatory)][string]$Activity,
        [string]$RequiredText
    )
    $inventory = Get-CleanupInventory -Targets @($Targets)
    Write-CleanupPreview -Inventory $inventory -Title $Description
    if (-not (Confirm-DestructiveAction -Description $Description -RequiredText $RequiredText)) { return $null }
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity $Activity
    Write-CleanupSummary -Action $Description -Result $result
    return $result
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
    Import-DotEnv -NoCreate
    Assert-ApplicationStopped
    Reset-CleanupDiscoveryNotes
    $targets = Get-LogCleanupTargets -LogRoot (Join-Path (Get-DataRootPath) 'logs')
    $result = Invoke-ConfirmedCleanup -Targets $targets -Description 'remove application log files' -Activity 'FAIRS: remove logs'
    if ($null -ne $result -and $result.Failed.Count -eq 0) { Write-Ok 'Application log files removed.' }
}

function Get-LogCleanupTargets([string]$LogRoot) {
    $targets = [Collections.Generic.List[object]]::new()
    if (-not (Test-Path -LiteralPath $LogRoot -PathType Container)) { return @() }
    if (-not (Test-CleanupDirectorySafeToScan -Path $LogRoot)) { return @() }
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push([IO.Path]::GetFullPath($LogRoot))
    while ($pending.Count -gt 0) {
        $current = $pending.Pop()
        try { $children = @(Get-ChildItem -LiteralPath $current -Force -ErrorAction Stop) }
        catch { Add-CleanupDiscoverySkip "$current (log discovery skipped: $($_.Exception.Message))"; continue }
        foreach ($child in $children) {
            if ($child.PSIsContainer) {
                if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
                    $pending.Push($child.FullName)
                } else {
                    Add-CleanupDiscoverySkip "$($child.FullName) (log discovery skipped: symbolic link or junction)"
                }
            } elseif ($child.Extension -ieq '.log') {
                [void]$targets.Add((New-CleanupTarget -Path $child.FullName -AllowedRoot $LogRoot -Mode 'File'))
            }
        }
    }
    return @($targets)
}

function Remove-UserLogFiles([string]$Path) {
    $targets = Get-LogCleanupTargets -LogRoot $Path
    $inventory = Get-CleanupInventory -Targets $targets
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity "FAIRS: remove logs from $Path"
    Write-CleanupSummary -Action "Remove logs from $Path" -Result $result
    return $result
}

function Clear-Cache {
    Import-DotEnv -NoCreate
    Assert-ApplicationStopped
    Reset-CleanupDiscoveryNotes
    $result = Invoke-ConfirmedCleanup -Targets (Get-CacheCleanupTargets) -Description 'clear disposable caches and regenerable artifacts' -Activity 'FAIRS: clear caches'
    if ($null -ne $result -and $result.Failed.Count -eq 0) { Write-Ok 'Disposable caches and regenerable artifacts cleared.' }
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
    if (Test-Path -LiteralPath $dataPath -PathType Container) {
        try {
            Assert-NoReparseAncestors -Path (Join-Path $dataPath '.fairs-cleanup-data-probe') -AllowedRoot $dataPath
        } catch {
            throw "FAIRS_DATA_DIR '$dataPath' traverses a symbolic link or junction; refusing cache and standard uninstall cleanup. $($_.Exception.Message)"
        }
    }
    $dataPrefix = $dataPath.TrimEnd('\') + '\'
    $cachePrefix = $cachePath.TrimEnd('\') + '\'
    if ($dataPath.Equals($cachePath, [StringComparison]::OrdinalIgnoreCase) -or
        $dataPath.StartsWith($cachePrefix, [StringComparison]::OrdinalIgnoreCase) -or
        $cachePath.StartsWith($dataPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "FAIRS_DATA_DIR '$dataPath' overlaps the canonical disposable cache root '$cachePath'. Choose a persistent data directory outside runtimes/cache."
    }
}

function Assert-NoPersistentDataTreeOverlap([object[]]$Targets) {
    $dataRoot = [IO.Path]::GetFullPath((Get-DataRootPath))
    $dataPrefix = $dataRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    foreach ($target in $Targets) {
        if ($target.Mode -ne 'Tree') { continue }
        $targetPath = [IO.Path]::GetFullPath($target.Path)
        $targetPrefix = $targetPath.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        if ($targetPath.StartsWith($dataPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            $checkpointRoot = [IO.Path]::GetFullPath((Join-Path $dataRoot 'checkpoints'))
            $isIncompleteCheckpointWorkspace = (Split-Path -Parent $targetPath).Equals($checkpointRoot, [StringComparison]::OrdinalIgnoreCase) -and
                (Split-Path -Leaf $targetPath) -match '^\..+\.(staging|backup|publish)-[0-9a-f]{32}$'
            if ($isIncompleteCheckpointWorkspace) { continue }
        }
        if ($targetPath.Equals($dataRoot, [StringComparison]::OrdinalIgnoreCase) -or
            $targetPath.StartsWith($dataPrefix, [StringComparison]::OrdinalIgnoreCase) -or
            $dataRoot.StartsWith($targetPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Cleanup tree '$targetPath' overlaps persistent FAIRS data root '$dataRoot'; refusing cache or standard uninstall cleanup."
        }
    }
}

function Get-UserDataTargets {
    $dataRoot = Get-DataRootPath
    $logRoot = Join-Path $dataRoot 'logs'
    $databaseFiles = @(
        (Join-Path $dataRoot 'database.db'),
        (Join-Path $dataRoot 'database.db-shm'),
        (Join-Path $dataRoot 'database.db-wal'),
        (Join-Path $dataRoot 'database.db-journal')
    )
    $externalDatabase = $false
    $databaseConfigPath = Join-Path $dataRoot 'database-config.json'
    $databaseResolutionError = $null
    $configItem = $null
    try {
        $configItem = Get-Item -LiteralPath $databaseConfigPath -Force -ErrorAction Stop
    } catch {
        if ($_.CategoryInfo.Category -ne [System.Management.Automation.ErrorCategory]::ObjectNotFound) {
            $databaseResolutionError = "Cannot inspect database configuration at '$databaseConfigPath'; refusing persistent data removal. $($_.Exception.Message)"
        }
    }
    if ($null -ne $configItem -and -not $databaseResolutionError) {
        try {
            if ($configItem.PSIsContainer) { throw 'Database configuration path is a directory.' }
            if (($configItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Database configuration is a symbolic link or junction.' }
            $databaseConfig = Get-Content -LiteralPath $databaseConfigPath -Raw | ConvertFrom-Json
            if (($databaseConfig.schema_version -isnot [int] -and $databaseConfig.schema_version -isnot [long]) -or
                $databaseConfig.schema_version -ne 1) {
                throw 'Unsupported database configuration schema version.'
            }
            if ($databaseConfig.backend -eq 'sqlite' -and $databaseConfig.sqlite.path) {
                $sqliteConfiguredPath = [string]$databaseConfig.sqlite.path
                $sqlitePath = if ([IO.Path]::IsPathRooted($sqliteConfiguredPath)) {
                    [IO.Path]::GetFullPath($sqliteConfiguredPath)
                } else {
                    [IO.Path]::GetFullPath((Join-Path $repoRoot $sqliteConfiguredPath))
                }
                $databaseFiles = @($sqlitePath, "$sqlitePath-shm", "$sqlitePath-wal", "$sqlitePath-journal")
            } elseif ($databaseConfig.backend -eq 'postgresql' -and
                $databaseConfig.postgresql.engine -eq 'postgresql+psycopg') {
                $externalDatabase = $true
                $databaseFiles = @()
            } else {
                throw 'Unknown database backend or missing SQLite path.'
            }
        } catch {
            $databaseResolutionError = "Cannot determine the active database from '$databaseConfigPath'; refusing persistent data removal. $($_.Exception.Message)"
        }
    }

    return [pscustomobject]@{
        DataRoot = $dataRoot
        DatabaseFiles = $databaseFiles
        DatabaseConfigFile = $databaseConfigPath
        CheckpointRoot = Join-Path $dataRoot 'checkpoints'
        LogRoot = $logRoot
        ExternalDatabase = $externalDatabase
        DatabaseResolutionError = $databaseResolutionError
    }
}

function Get-DataRootPath {
    $dataRoot = if ($env:FAIRS_DATA_DIR -and $env:FAIRS_DATA_DIR.Trim()) {
        Resolve-LauncherPath $env:FAIRS_DATA_DIR.Trim()
    } else {
        Join-Path $repoRoot 'data'
    }
    $fullDataRoot = [IO.Path]::GetFullPath($dataRoot)
    if ($fullDataRoot.Equals([IO.Path]::GetPathRoot($fullDataRoot), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to use a filesystem root as FAIRS_DATA_DIR: '$fullDataRoot'."
    }
    return $fullDataRoot
}

function Get-CompleteDataCleanupTargets {
    $data = Get-UserDataTargets
    if ($data.DatabaseResolutionError) { throw $data.DatabaseResolutionError }
    $targets = [Collections.Generic.List[object]]::new()
    foreach ($databaseFile in $data.DatabaseFiles) {
        $allowedRoot = Split-Path -Parent $databaseFile
        if (-not $allowedRoot) { $allowedRoot = [IO.Path]::GetPathRoot($databaseFile) }
        Add-CleanupTargetIfPresent $targets $databaseFile $allowedRoot -Mode 'File'
    }
    Add-CleanupTargetIfPresent $targets $data.CheckpointRoot $data.DataRoot -KeepRoot -PreserveNames @('.gitkeep')
    Add-CleanupTargetIfPresent $targets $data.DatabaseConfigFile $data.DataRoot -Mode 'File'
    Add-CleanupTargetIfPresent $targets $envFile (Join-Path $repoRoot 'settings') -Mode 'File'
    return @(Remove-DuplicateCleanupTargets -Targets @($targets))
}

function Get-StandardUninstallTargets {
    Assert-DataCacheIsolation
    $targets = [Collections.Generic.List[object]]::new()
    foreach ($path in @(
        (Join-Path $runtimeRoot 'python'), (Join-Path $runtimeRoot 'uv'), (Join-Path $runtimeRoot 'nodejs')
    )) { Add-CleanupTargetIfPresent $targets $path $runtimeRoot }
    Add-CleanupTargetIfPresent $targets $runtimeCacheDir $runtimeRoot -KeepRoot -PreserveNames @('.gitkeep')
    Add-CleanupTargetIfPresent $targets $venvDir $serverDir
    Add-CleanupTargetIfPresent $targets (Join-Path $clientDir 'node_modules') $clientDir
    foreach ($target in @(Get-CacheCleanupTargets)) { [void]$targets.Add($target) }
    $logTargets = Get-LogCleanupTargets -LogRoot (Join-Path (Get-DataRootPath) 'logs')
    foreach ($target in $logTargets) { [void]$targets.Add($target) }
    $uniqueTargets = @(Remove-DuplicateCleanupTargets -Targets @($targets))
    Assert-NoPersistentDataTreeOverlap -Targets $uniqueTargets
    Assert-NoDatabaseCleanupOverlap -Targets $uniqueTargets
    return $uniqueTargets
}

function Remove-UserDataDirectory([string]$Path) {
    $allowedRoot = Split-Path -Parent $Path
    $target = New-CleanupTarget -Path $Path -AllowedRoot $allowedRoot -KeepRoot -PreserveNames @('.gitkeep')
    $inventory = Get-CleanupInventory -Targets @($target)
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity "FAIRS: remove data from $Path"
    Write-CleanupSummary -Action "Remove data from $Path" -Result $result
    return $result
}

function Remove-Checkpoints {
    Import-DotEnv -NoCreate
    Assert-ApplicationStopped
    $targets = Get-UserDataTargets
    $target = New-CleanupTarget -Path $targets.CheckpointRoot -AllowedRoot $targets.DataRoot -KeepRoot -PreserveNames @('.gitkeep')
    $inventory = Get-CleanupInventory -Targets @($target)
    Write-CleanupPreview -Inventory $inventory -Title 'Delete saved checkpoints'
    if (-not (Confirm-DestructiveAction 'delete all saved checkpoints')) { return }
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity 'FAIRS: remove saved checkpoints'
    Write-CleanupSummary -Action 'Delete saved checkpoints' -Result $result
}

function Remove-AllData {
    Import-DotEnv -NoCreate
    Assert-ApplicationStopped
    Reset-CleanupDiscoveryNotes
    $targets = Get-UserDataTargets
    if ($targets.DatabaseResolutionError) { throw $targets.DatabaseResolutionError }
    $cleanupTargets = [Collections.Generic.List[object]]::new()
    foreach ($databaseFile in $targets.DatabaseFiles) {
        $allowedRoot = Split-Path -Parent $databaseFile
        if (-not $allowedRoot) { $allowedRoot = [IO.Path]::GetPathRoot($databaseFile) }
        Add-CleanupTargetIfPresent $cleanupTargets $databaseFile $allowedRoot -Mode 'File'
    }
    foreach ($target in (Get-LogCleanupTargets -LogRoot $targets.LogRoot)) { [void]$cleanupTargets.Add($target) }
    $inventory = Get-CleanupInventory -Targets @(Remove-DuplicateCleanupTargets -Targets @($cleanupTargets))
    Write-CleanupPreview -Inventory $inventory -Title 'Remove local database and logs (checkpoints and configuration are preserved)'
    if (-not (Confirm-DestructiveAction 'remove local database and application logs')) { return }
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity 'FAIRS: remove local data'
    Write-CleanupSummary -Action 'Remove local database and logs' -Result $result
    if ($targets.ExternalDatabase) {
        Write-Info 'An external database is configured. Its remote data was not changed.'
    }
    if ($result.Failed.Count -eq 0) { Write-Ok 'Local database and application logs were removed. Saved checkpoints and configuration were preserved.' }
}

function Uninstall-Application {
    param([ValidateSet('Standard', 'Complete')][string]$Mode)
    Import-DotEnv -NoCreate
    Assert-ApplicationStopped
    Reset-CleanupDiscoveryNotes
    if (-not $Mode) {
        if (-not $script:LauncherInteractive) { throw "The uninstall action requires an interactive console; no files were changed." }
        $selection = ([string](Read-Host 'Uninstall mode [1=Standard, 2=Complete removal]')).Trim()
        switch ($selection) {
            '1' { $Mode = 'Standard' }
            '2' { $Mode = 'Complete' }
            default { throw 'Invalid uninstall mode. Enter 1 for Standard or 2 for Complete removal.' }
        }
    }

    $targets = [Collections.Generic.List[object]]::new()
    foreach ($target in @(Get-StandardUninstallTargets)) { [void]$targets.Add($target) }
    if ($Mode -eq 'Complete') {
        foreach ($target in @(Get-CompleteDataCleanupTargets)) { [void]$targets.Add($target) }
    }
    $inventory = Get-CleanupInventory -Targets @(Remove-DuplicateCleanupTargets -Targets @($targets))
    $title = if ($Mode -eq 'Complete') { 'Complete removal: generated files and persistent FAIRS data' } else { 'Standard uninstall: runtimes, caches, build outputs, test reports, and application logs' }
    Write-CleanupPreview -Inventory $inventory -Title $title
    if ($inventory.Failed.Count -gt 0) {
        throw 'Uninstall preview found unsafe or inaccessible targets; no files were changed.'
    }
    $confirmationDescription = if ($Mode -eq 'Complete') { 'remove generated files before complete removal' } else { 'remove standard application files' }
    if (-not (Confirm-DestructiveAction $confirmationDescription)) { return }
    if ($Mode -eq 'Complete' -and -not (Confirm-DestructiveAction -Description 'remove persistent FAIRS data and launcher configuration' -RequiredText 'REMOVE')) { return }
    $result = Invoke-CleanupInventory -Inventory $inventory -Activity 'FAIRS: uninstall application'
    Write-CleanupSummary -Action $title -Result $result
    if ($Mode -eq 'Standard') {
        Write-Ok 'Standard uninstall completed. Local database, checkpoints, database configuration, and settings/.env were preserved.'
    } elseif ($result.Failed.Count -eq 0) {
        Write-Ok 'Complete removal finished for known local FAIRS data. Unknown data-root files and browser localStorage were preserved.'
    }
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
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Cache'; Label = 'Clear cache'; Description = 'Remove disposable caches and regenerable build/test artifacts'; Color = [ConsoleColor]::DarkYellow }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Checkpoints'; Label = 'Remove checkpoints'; Description = 'Delete saved checkpoints only'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'AllData'; Label = 'Remove database + logs'; Description = 'Delete local database and logs; preserve checkpoints and configuration'; Color = [ConsoleColor]::Red }
        [pscustomobject]@{ Section = 'DATA & MAINTENANCE'; Key = 'Uninstall'; Label = 'Uninstall application'; Description = 'Remove generated files; optionally remove persistent FAIRS data'; Color = [ConsoleColor]::Red }
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

if ($Action) {
    try {
        if (-not $WhatIfPreference) { throw 'The -Action parameter is preview-only and must be combined with -WhatIf.' }
        if ($Launch) { throw 'Use either -Launch or -Action, not both.' }
        if ($CompleteRemoval -and $Action -ne 'Uninstall') { throw '-CompleteRemoval is available only with -Action Uninstall -WhatIf.' }
        Import-DotEnv -NoCreate
        Reset-CleanupDiscoveryNotes
        $previewTargets = if ($Action -eq 'Cache') { Get-CacheCleanupTargets } else { Get-StandardUninstallTargets }
        if ($Action -eq 'Uninstall' -and $CompleteRemoval) {
            $previewTargets = @($previewTargets) + @(Get-CompleteDataCleanupTargets)
        }
        $previewInventory = Get-CleanupInventory -Targets @($previewTargets)
        $previewTitle = if ($Action -eq 'Cache') { 'Cache cleanup dry run' } elseif ($CompleteRemoval) { 'Complete uninstall dry run' } else { 'Standard uninstall dry run' }
        Write-CleanupPreview -Inventory $previewInventory -Title $previewTitle
        if ($previewInventory.Failed.Count -gt 0) { exit 1 }
        Write-Info "Dry run complete. $($previewInventory.Entries.Count) existing path(s) would be removed. No files were changed."
        exit 0
    } catch {
        Write-Fatal "Cleanup preview failed: $($_.Exception.Message)"
        exit 1
    }
}
if ($CompleteRemoval) {
    Write-Fatal '-CompleteRemoval requires -Action Uninstall -WhatIf.'
    exit 2
}
if ($WhatIfPreference) {
    Write-Fatal 'Use -Action Cache -WhatIf or -Action Uninstall -WhatIf to preview cleanup targets.'
    exit 2
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
