$ErrorActionPreference = 'Stop'

$script:RepositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$script:LauncherPath = Join-Path $script:RepositoryRoot 'start_on_windows.ps1'
$script:RunId = [Guid]::NewGuid().ToString('N')
$script:FixtureRoot = Join-Path $env:TEMP "fairs-val19-$PID-$($script:RunId)"
$script:ExternalRoot = Join-Path $env:TEMP "fairs-val19-external-$PID-$($script:RunId)"
$script:DataRoot = Join-Path $script:FixtureRoot 'isolated-data'
$script:ConfirmationResponse = 'yes'
$script:ProcessFixtureRoot = $null
$script:ProcessExternalRoot = $null
$script:OwnedProcessIds = [Collections.Generic.List[int]]::new()
$script:OtherProcessIds = [Collections.Generic.List[int]]::new()
$script:PowerShellExecutable = (Get-Command pwsh, powershell -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty Source)

function Assert-Condition([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "VAL-19 assertion failed: $Message" }
}

function Assert-FileContains([string]$Path, [string]$Expected) {
    Assert-Condition (Test-Path -LiteralPath $Path -PathType Leaf) "Expected file '$Path' to exist."
    $actual = Get-Content -LiteralPath $Path -Raw
    Assert-Condition ($actual -eq $Expected) "Unexpected contents in '$Path'."
}

function New-FixtureFile([string]$Path, [string]$Contents = 'fixture') {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Set-Content -LiteralPath $Path -Value $Contents -NoNewline
}

function Remove-SafeTree([string]$Path, [string]$RequiredPrefix) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $resolved = [IO.Path]::GetFullPath($Path)
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    Assert-Condition ($resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove a path outside TEMP: '$resolved'."
    Assert-Condition ([IO.Path]::GetFileName($resolved).StartsWith($RequiredPrefix, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove an unexpected fixture path: '$resolved'."
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

function Remove-SafeQaTree([string]$Path, [string]$RequiredPrefix) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $resolved = [IO.Path]::GetFullPath($Path)
    $qaRoot = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot 'assets\QA')).TrimEnd('\') + '\'
    Assert-Condition ($resolved.StartsWith($qaRoot, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove a path outside assets/QA: '$resolved'."
    Assert-Condition ([IO.Path]::GetFileName($resolved).StartsWith($RequiredPrefix, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove an unexpected QA fixture path: '$resolved'."
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

function Get-FreeTcpPort {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    try {
        $listener.Start()
        return [int]$listener.LocalEndpoint.Port
    } finally {
        $listener.Stop()
    }
}

$script:IdleBackendPort = Get-FreeTcpPort
do { $script:IdleFrontendPort = Get-FreeTcpPort } while ($script:IdleFrontendPort -eq $script:IdleBackendPort)

function Reset-Fixture([string]$EmbeddedDatabase = 'true', [int]$BackendPort = -1, [int]$FrontendPort = -1) {
    if ($BackendPort -lt 1) { $BackendPort = $script:IdleBackendPort }
    if ($FrontendPort -lt 1) { $FrontendPort = $script:IdleFrontendPort }
    Remove-SafeTree $script:FixtureRoot 'fairs-val19-'
    Remove-SafeTree $script:ExternalRoot 'fairs-val19-external-'
    $script:FixtureRoot = Join-Path $env:TEMP "fairs-val19-$PID-$([Guid]::NewGuid().ToString('N'))"
    $script:ExternalRoot = Join-Path $env:TEMP "fairs-val19-external-$PID-$([Guid]::NewGuid().ToString('N'))"
    $script:DataRoot = Join-Path $script:FixtureRoot 'isolated-data'

    $script:repoRoot = $script:FixtureRoot
    $script:runtimeRoot = Join-Path $script:repoRoot 'runtimes'
    $script:runtimeCacheDir = Join-Path $script:runtimeRoot 'cache'
    $script:serverDir = Join-Path $script:repoRoot 'app\server'
    $script:clientDir = Join-Path $script:repoRoot 'app\client'
    $script:venvDir = Join-Path $script:serverDir '.venv'
    $script:envFile = Join-Path $script:repoRoot 'settings\.env'
    $script:envExample = Join-Path $script:repoRoot 'settings\.env.example'
    $script:cacheDirectories = [ordered]@{}
    foreach ($name in @(
        'uv', 'npm', 'pip', 'python', 'pytest', 'pytest-tmp', 'ruff', 'mypy',
        'coverage', 'playwright-browsers', 'vite', 'typescript', 'keras', 'torch',
        'torch-inductor', 'triton', 'matplotlib', 'xdg', 'cuda'
    )) {
        $script:cacheDirectories[$name] = Join-Path $script:runtimeCacheDir $name
    }

    New-Item -ItemType Directory -Path (Join-Path $script:repoRoot 'settings') -Force | Out-Null
    New-Item -ItemType Directory -Path $script:DataRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $script:ExternalRoot -Force | Out-Null
    @(
        'FASTAPI_HOST=127.0.0.1',
        "FASTAPI_PORT=$BackendPort",
        'UI_HOST=127.0.0.1',
        "UI_PORT=$FrontendPort",
        'RELOAD=false',
        "EMBEDDED_DATABASE=$EmbeddedDatabase",
        "FAIRS_DATA_DIR='$script:DataRoot'"
    ) | Set-Content -LiteralPath $script:envFile

    $env:FASTAPI_PORT = [string]$BackendPort
    $env:UI_PORT = [string]$FrontendPort
    $env:FAIRS_DATA_DIR = $script:DataRoot
    $script:ConfirmationResponse = 'yes'
    $script:LauncherInteractive = $false
}

function Get-FixtureSnapshot {
    $files = @(Get-ChildItem -LiteralPath $script:FixtureRoot -File -Recurse -Force -ErrorAction SilentlyContinue | Sort-Object FullName)
    $snapshot = foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($script:FixtureRoot.Length).TrimStart('\')
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        "$relativePath=$hash"
    }
    return ,([string[]]@($snapshot))
}

function Assert-SnapshotEqual([string[]]$Before, [string[]]$After, [string]$Context) {
    $beforeText = [string]::Join("`n", @($Before))
    $afterText = [string]::Join("`n", @($After))
    Assert-Condition ($beforeText -ceq $afterText) "$Context changed fixture files."
}

function Invoke-MaintenanceAction([string]$Name) {
    switch ($Name) {
        'Logs' { Remove-Logs }
        'Cache' { Clear-Cache }
        'Checkpoints' { Remove-Checkpoints }
        'AllData' { Remove-AllData }
        'Uninstall' { Uninstall-Application }
        'StopProcesses' { Stop-ApplicationProcesses }
        default { throw "Unknown maintenance action '$Name'." }
    }
}

function Assert-Throws([scriptblock]$Action, [string]$ExpectedText) {
    $didThrow = $false
    try {
        & $Action
    } catch {
        if ($_.Exception.Message -notlike "*$ExpectedText*") { throw }
        $didThrow = $true
    }
    Assert-Condition $didThrow "Expected an error containing '$ExpectedText'."
}

function Read-Host([string]$Prompt) {
    $response = $script:ConfirmationResponse
    $script:LauncherInteractive = $false
    return $response
}

function Test-DeclinedAndNoninteractiveActions {
    $actions = @('Logs', 'Cache', 'Checkpoints', 'AllData', 'Uninstall')
    foreach ($actionName in $actions) {
        Reset-Fixture
        $marker = Join-Path $script:FixtureRoot 'sentinel.txt'
        New-FixtureFile $marker "$actionName sentinel"
        $before = @(Get-FixtureSnapshot)

        $script:LauncherInteractive = $false
        Assert-Throws { Invoke-MaintenanceAction $actionName } 'requires an interactive console'
        Assert-SnapshotEqual $before @(Get-FixtureSnapshot) "$actionName noninteractive confirmation"

        $script:LauncherInteractive = $true
        $script:ConfirmationResponse = 'n'
        Invoke-MaintenanceAction $actionName
        Assert-SnapshotEqual $before @(Get-FixtureSnapshot) "$actionName declined confirmation"
    }
}

function Test-RunningApplicationGuards {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $occupiedPort = [int]$listener.LocalEndpoint.Port
    try {
        foreach ($actionName in @('Logs', 'Cache', 'Checkpoints', 'AllData', 'Uninstall')) {
            Reset-Fixture -BackendPort $occupiedPort -FrontendPort $script:IdleFrontendPort
            $marker = Join-Path $script:FixtureRoot 'sentinel.txt'
            New-FixtureFile $marker "$actionName sentinel"
            $before = @(Get-FixtureSnapshot)
            $script:LauncherInteractive = $true
            Assert-Throws { Invoke-MaintenanceAction $actionName } 'Application is still running'
            Assert-SnapshotEqual $before @(Get-FixtureSnapshot) "$actionName running-application guard"
        }
    } finally {
        $listener.Stop()
    }
}

function Test-RemoveLogs {
    Reset-Fixture
    $logs = Join-Path $script:DataRoot 'logs'
    New-FixtureFile (Join-Path $logs 'current.log') 'log'
    New-FixtureFile (Join-Path $logs 'nested\old.log') 'old log'
    New-FixtureFile (Join-Path $logs 'nested\notes.txt') 'keep note'
    New-FixtureFile (Join-Path $script:DataRoot 'outside.log') 'keep outside'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'Logs'

    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $logs 'current.log'))) 'Remove logs left a root log file.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $logs 'nested\old.log'))) 'Remove logs left a nested log file.'
    Assert-FileContains (Join-Path $logs 'nested\notes.txt') 'keep note'
    Assert-FileContains (Join-Path $script:DataRoot 'outside.log') 'keep outside'
}

function Test-ClearCache {
    Reset-Fixture
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'sentinel.cache') 'cache'
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'pytest\nodeids') 'cache child'
    $neighbor = Join-Path $script:runtimeRoot 'cache-neighbor'
    New-FixtureFile (Join-Path $neighbor 'keep.txt') 'keep neighbor'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'Cache'

    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:runtimeCacheDir 'sentinel.cache'))) 'Clear cache left its root sentinel.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:runtimeCacheDir 'pytest\nodeids'))) 'Clear cache left a nested cache sentinel.'
    Assert-FileContains (Join-Path $neighbor 'keep.txt') 'keep neighbor'
    Assert-Condition ($env:FAIRS_CACHE_DIR -eq $script:runtimeCacheDir) 'Clear cache did not restore cache environment paths.'
}

function Test-RemoveCheckpoints {
    Reset-Fixture
    $checkpointRoot = Join-Path $script:DataRoot 'checkpoints'
    New-FixtureFile (Join-Path $checkpointRoot 'model.pt') 'checkpoint'
    New-FixtureFile (Join-Path $checkpointRoot '.gitkeep') ''
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'database'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\run.log') 'log'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'Checkpoints'

    $remaining = @(Get-ChildItem -LiteralPath $checkpointRoot -File -Force | Select-Object -ExpandProperty Name)
    Assert-Condition (($remaining -join ',') -eq '.gitkeep') 'Remove checkpoints did not preserve only the checkpoint-directory marker.'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'database'
    Assert-FileContains (Join-Path $script:DataRoot 'logs\run.log') 'log'
}

function Test-RemoveAllData {
    Reset-Fixture 'false'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'database'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db-shm') 'shared memory'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db-wal') 'write ahead log'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\run.log') 'log'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\notes.txt') 'keep note'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'
    $externalSentinel = Join-Path $script:ExternalRoot 'external-database.marker'
    New-FixtureFile $externalSentinel 'remote data untouched'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'AllData'

    foreach ($name in @('database.db', 'database.db-shm', 'database.db-wal')) {
        Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:DataRoot $name))) "Remove all data left '$name'."
    }
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:DataRoot 'logs\run.log'))) 'Remove all data left a log file.'
    Assert-FileContains (Join-Path $script:DataRoot 'logs\notes.txt') 'keep note'
    Assert-FileContains (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'
    Assert-FileContains $externalSentinel 'remote data untouched'
}

function Test-Uninstall {
    Reset-Fixture
    New-FixtureFile (Join-Path $script:runtimeRoot 'python\python.exe') 'runtime'
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'cache.bin') 'cache'
    New-FixtureFile (Join-Path $script:venvDir 'Scripts\python.exe') 'venv'
    New-FixtureFile (Join-Path $script:clientDir 'node_modules\marker') 'dependency'
    New-FixtureFile (Join-Path $script:clientDir 'dist\index.html') 'build'
    New-FixtureFile (Join-Path $script:serverDir 'pyproject.toml') 'server project metadata'
    New-FixtureFile (Join-Path $script:serverDir 'uv.lock') 'server lockfile'
    New-FixtureFile (Join-Path $script:clientDir 'package-lock.json') 'frontend lock metadata'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'user database'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'Uninstall'

    Assert-Condition (Test-Path -LiteralPath (Join-Path $script:runtimeRoot '.gitkeep')) 'Uninstall did not recreate the runtime marker.'
    foreach ($path in @(
        (Join-Path $script:runtimeRoot 'python'),
        $script:runtimeCacheDir,
        $script:venvDir,
        (Join-Path $script:clientDir 'node_modules'),
        (Join-Path $script:clientDir 'dist')
    )) {
        Assert-Condition (-not (Test-Path -LiteralPath $path)) "Uninstall left owned path '$path'."
    }
    Assert-FileContains (Join-Path $script:serverDir 'pyproject.toml') 'server project metadata'
    Assert-FileContains (Join-Path $script:serverDir 'uv.lock') 'server lockfile'
    Assert-FileContains (Join-Path $script:clientDir 'package-lock.json') 'frontend lock metadata'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'user database'
}

function New-SleeperProcess([string]$ScriptPath) {
    $arguments = '-NoLogo -NoProfile -File "{0}"' -f $ScriptPath
    return Start-Process -FilePath $script:PowerShellExecutable -ArgumentList $arguments -PassThru -WindowStyle Hidden
}

function Test-StopApplicationProcesses {
    Reset-Fixture
    $qaRoot = Join-Path $script:RepositoryRoot 'assets\QA'
    $script:ProcessFixtureRoot = Join-Path $qaRoot ".scratch-val19-process-$PID-$([Guid]::NewGuid().ToString('N'))"
    $script:ProcessExternalRoot = Join-Path $qaRoot ".scratch-val19-external-$PID-$([Guid]::NewGuid().ToString('N'))"
    $childScript = Join-Path $script:ProcessFixtureRoot 'owned-child-sleeper.ps1'
    $childPidPath = Join-Path $script:ProcessFixtureRoot 'owned-child.pid'
    $parentScript = Join-Path $script:ProcessFixtureRoot 'uvicorn-parent.ps1'
    $ordinaryScript = Join-Path $script:ProcessFixtureRoot 'ordinary-sleeper.ps1'
    $outsideScript = Join-Path $script:ProcessExternalRoot 'uvicorn-outsider.ps1'
    New-FixtureFile $childScript 'Start-Sleep -Seconds 300'
    New-FixtureFile $ordinaryScript 'Start-Sleep -Seconds 300'
    New-FixtureFile $outsideScript 'Start-Sleep -Seconds 300'
    $quotedChild = $childScript.Replace("'", "''")
    $quotedChildPid = $childPidPath.Replace("'", "''")
    $parentContents = @"
`$child = Start-Process -FilePath '$script:PowerShellExecutable' -ArgumentList '-NoLogo -NoProfile -File `"$quotedChild`"' -PassThru -WindowStyle Hidden
Set-Content -LiteralPath '$quotedChildPid' -Value `$child.Id
Wait-Process -Id `$child.Id
"@
    New-FixtureFile $parentScript $parentContents

    $parent = New-SleeperProcess $parentScript
    $script:OwnedProcessIds.Add($parent.Id)
    $deadline = (Get-Date).AddSeconds(10)
    while (-not (Test-Path -LiteralPath $childPidPath) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
    Assert-Condition (Test-Path -LiteralPath $childPidPath) 'The owned process tree did not start its child.'
    $childId = [int](Get-Content -LiteralPath $childPidPath -Raw)
    $script:OwnedProcessIds.Add($childId)

    $ordinary = New-SleeperProcess $ordinaryScript
    $outside = New-SleeperProcess $outsideScript
    $script:OtherProcessIds.Add($ordinary.Id)
    $script:OtherProcessIds.Add($outside.Id)

    $repoRoot = [IO.Path]::GetFullPath($script:ProcessFixtureRoot)
    $script:repoRoot = $repoRoot
    $liveProcessRecords = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    $expectedProcessIds = [Collections.Generic.HashSet[int]]::new()
    [void]$expectedProcessIds.Add($parent.Id)
    [void]$expectedProcessIds.Add($childId)
    do {
        $addedExpectedProcess = $false
        foreach ($process in $liveProcessRecords) {
            if (-not $expectedProcessIds.Contains([int]$process.ProcessId) -and
                $expectedProcessIds.Contains([int]$process.ParentProcessId)) {
                [void]$expectedProcessIds.Add([int]$process.ProcessId)
                $addedExpectedProcess = $true
            }
        }
    } while ($addedExpectedProcess)

    $ownedRecords = @(Get-ApplicationProcessRecords)
    $discoveredIds = @($ownedRecords | Select-Object -ExpandProperty ProcessId)
    if ($discoveredIds.Count -ne $expectedProcessIds.Count) {
        $details = @($ownedRecords | ForEach-Object {
            "PID $($_.ProcessId), parent $($_.ParentProcessId), executable '$($_.ExecutablePath)', command '$($_.CommandLine)'"
        }) -join '; '
        throw "VAL-19 process discovery expected process tree [$(@($expectedProcessIds) -join ',')]; found $($discoveredIds -join ','): $details"
    }
    foreach ($processId in $discoveredIds) {
        if (-not $script:OwnedProcessIds.Contains([int]$processId)) {
            $script:OwnedProcessIds.Add([int]$processId)
        }
    }
    Assert-Condition ($discoveredIds -contains $parent.Id) 'Process discovery missed the repo-qualified application process.'
    Assert-Condition ($discoveredIds -contains $childId) 'Process discovery missed a child of the application process.'
    Assert-Condition (-not ($discoveredIds -contains $ordinary.Id)) 'Process discovery included an unrelated process under the fixture root.'
    Assert-Condition (-not ($discoveredIds -contains $outside.Id)) 'Process discovery included an app-like process outside the fixture root.'

    $script:LauncherInteractive = $false
    Assert-Throws { Stop-ApplicationProcesses } 'requires an interactive console'
    foreach ($processId in $script:OwnedProcessIds) {
        Assert-Condition ($null -ne (Get-Process -Id $processId -ErrorAction SilentlyContinue)) 'Noninteractive process stop terminated a test process.'
    }

    $script:ConfirmationResponse = 'no'
    $script:LauncherInteractive = $true
    Stop-ApplicationProcesses
    foreach ($processId in $script:OwnedProcessIds) {
        Assert-Condition ($null -ne (Get-Process -Id $processId -ErrorAction SilentlyContinue)) 'Declined process stop terminated a test process.'
    }

    $script:ConfirmationResponse = 'yes'
    $script:LauncherInteractive = $true
    Stop-ApplicationProcesses
    $deadline = (Get-Date).AddSeconds(5)
    while ((Get-Process -Id $parent.Id -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
    foreach ($processId in $script:OwnedProcessIds) {
        Assert-Condition ($null -eq (Get-Process -Id $processId -ErrorAction SilentlyContinue)) "Confirmed stop left owned PID $processId running."
    }
    foreach ($processId in $script:OtherProcessIds) {
        Assert-Condition ($null -ne (Get-Process -Id $processId -ErrorAction SilentlyContinue)) "Confirmed stop terminated unrelated PID $processId."
    }
}

function Cleanup-TestProcesses {
    foreach ($processId in @($script:OwnedProcessIds) + @($script:OtherProcessIds)) {
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
    $script:OwnedProcessIds.Clear()
    $script:OtherProcessIds.Clear()
}

$source = Get-Content -LiteralPath $script:LauncherPath -Raw
$entryPointPattern = '(?m)^Set-CacheEnvironment\r?\nShow-Menu\r?\nClear-LauncherProgress\r?$'
if ([regex]::Matches($source, $entryPointPattern).Count -ne 1) {
    throw 'VAL-19 could not isolate the launcher menu entry point for behavioral testing.'
}
$testableSource = [regex]::Replace($source, $entryPointPattern, '')
$testableSource = $testableSource.Replace('$repoRoot = $PSScriptRoot', '$repoRoot = $script:RepositoryRoot')
. ([scriptblock]::Create($testableSource))

try {
    Test-DeclinedAndNoninteractiveActions
    Test-RunningApplicationGuards
    Test-RemoveLogs
    Test-ClearCache
    Test-RemoveCheckpoints
    Test-RemoveAllData
    Test-Uninstall
    Test-StopApplicationProcesses
    Write-Output 'VAL-19 maintenance behavior passed in isolated fixtures.'
} finally {
    Cleanup-TestProcesses
    Remove-SafeTree $script:FixtureRoot 'fairs-val19-'
    Remove-SafeTree $script:ExternalRoot 'fairs-val19-external-'
    Remove-SafeQaTree $script:ProcessFixtureRoot '.scratch-val19-process-'
    Remove-SafeQaTree $script:ProcessExternalRoot '.scratch-val19-external-'
}
