# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

$ErrorActionPreference = 'Stop'

$script:RepositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$script:LauncherPath = Join-Path $script:RepositoryRoot 'start_on_windows.ps1'
$script:RunId = [Guid]::NewGuid().ToString('N')
$script:FixtureRoot = Join-Path $env:TEMP "fairs-val19-$PID-$($script:RunId)"
$script:ExternalRoot = Join-Path $env:TEMP "fairs-val19-external-$PID-$($script:RunId)"
$script:DataRoot = Join-Path $script:FixtureRoot 'isolated-data'
$script:ConfirmationResponse = 'yes'
$script:UninstallMode = 'Standard'
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

function Remove-TreeWithoutFollowingLinks([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $root = Get-Item -LiteralPath $Path -Force
    if (($root.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        if ($root.PSIsContainer) { [IO.Directory]::Delete($root.FullName, $false) } else { [IO.File]::Delete($root.FullName) }
        return
    }
    if (-not $root.PSIsContainer) { [IO.File]::Delete($root.FullName); return }
    $pending = [Collections.Generic.Stack[object]]::new()
    $pending.Push([pscustomobject]@{ Item = $root; Visited = $false })
    while ($pending.Count -gt 0) {
        $work = $pending.Pop()
        $item = $work.Item
        if ($item.PSIsContainer -and -not $work.Visited -and (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)) {
            $pending.Push([pscustomobject]@{ Item = $item; Visited = $true })
            foreach ($child in @(Get-ChildItem -LiteralPath $item.FullName -Force)) {
                $pending.Push([pscustomobject]@{ Item = $child; Visited = $false })
            }
        } elseif (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            if ($item.PSIsContainer) { [IO.Directory]::Delete($item.FullName, $false) } else { [IO.File]::Delete($item.FullName) }
        } elseif ($item.PSIsContainer) {
            [IO.Directory]::Delete($item.FullName, $false)
        } else {
            [IO.File]::Delete($item.FullName)
        }
    }
}

function Remove-SafeTree([string]$Path, [string]$RequiredPrefix) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) { return }
    $resolved = [IO.Path]::GetFullPath($Path)
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    Assert-Condition ($resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove a path outside TEMP: '$resolved'."
    Assert-Condition ([IO.Path]::GetFileName($resolved).StartsWith($RequiredPrefix, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove an unexpected fixture path: '$resolved'."
    Remove-TreeWithoutFollowingLinks $resolved
}

function Remove-SafeQaTree([string]$Path, [string]$RequiredPrefix) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $resolved = [IO.Path]::GetFullPath($Path)
    $qaRoot = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot 'assets\QA')).TrimEnd('\') + '\'
    Assert-Condition ($resolved.StartsWith($qaRoot, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove a path outside assets/QA: '$resolved'."
    Assert-Condition ([IO.Path]::GetFileName($resolved).StartsWith($RequiredPrefix, [StringComparison]::OrdinalIgnoreCase)) "Refusing to remove an unexpected QA fixture path: '$resolved'."
    Remove-TreeWithoutFollowingLinks $resolved
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

function Reset-Fixture([int]$BackendPort = -1, [int]$FrontendPort = -1) {
    if ($BackendPort -lt 1) { $BackendPort = $script:IdleBackendPort }
    if ($FrontendPort -lt 1) { $FrontendPort = $script:IdleFrontendPort }
    Remove-SafeTree $script:FixtureRoot 'fairs-val19-'
    Remove-SafeTree $script:ExternalRoot 'fairs-val19-external-'
    $script:FixtureRoot = Join-Path $env:TEMP "fairs-val19-$PID-$([Guid]::NewGuid().ToString('N'))"
    $script:ExternalRoot = Join-Path $env:TEMP "fairs-val19-external-$PID-$([Guid]::NewGuid().ToString('N'))"
    $script:DataRoot = Join-Path $script:FixtureRoot 'isolated-data'

    $script:repoRoot = $script:FixtureRoot
    $script:runtimeRoot = Join-Path $script:repoRoot 'runtimes'
    $script:pythonDir = Join-Path $script:runtimeRoot 'python'
    $script:uvDir = Join-Path $script:runtimeRoot 'uv'
    $script:nodeDir = Join-Path $script:runtimeRoot 'nodejs'
    $script:runtimeCacheDir = Join-Path $script:runtimeRoot 'cache'
    $script:serverDir = Join-Path $script:repoRoot 'app\server'
    $script:clientDir = Join-Path $script:repoRoot 'app\client'
    $script:testsDir = Join-Path $script:repoRoot 'app\tests'
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
        "FAIRS_DATA_DIR='$script:DataRoot'"
    ) | Set-Content -LiteralPath $script:envFile

    $env:FASTAPI_PORT = [string]$BackendPort
    $env:UI_PORT = [string]$FrontendPort
    $env:FAIRS_DATA_DIR = $script:DataRoot
    $script:ConfirmationResponse = 'yes'
    $script:UninstallMode = 'Standard'
    $script:LauncherInteractive = $false
}

function Test-EnvironmentDatabaseIndependence {
    Reset-Fixture
    @(
        'FASTAPI_HOST=127.0.0.1',
        "FASTAPI_PORT=$script:IdleBackendPort",
        'UI_HOST=127.0.0.1',
        "UI_PORT=$script:IdleFrontendPort",
        'RELOAD=false',
        "FAIRS_DATA_DIR='$script:DataRoot'",
        'EMBEDDED_DATABASE=false',
        'DATABASE_HOST=legacy-host'
    ) | Set-Content -LiteralPath $script:envFile

    foreach ($name in @('EMBEDDED_DATABASE', 'DATABASE_HOST')) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    Import-DotEnv

    Assert-Condition ($env:FASTAPI_HOST -eq '127.0.0.1') 'Import-DotEnv skipped ordinary launcher values.'
    Assert-Condition ([string]::IsNullOrWhiteSpace($env:EMBEDDED_DATABASE)) 'Import-DotEnv loaded legacy database selection.'
    Assert-Condition ([string]::IsNullOrWhiteSpace($env:DATABASE_HOST)) 'Import-DotEnv loaded a legacy database host.'
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
        'Uninstall' { Uninstall-Application -Mode $script:UninstallMode }
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
    if ($Prompt -like 'Uninstall mode*') {
        if ($script:UninstallMode -eq 'Complete') { return '2' }
        return '1'
    }
    if ($Prompt -like 'Type REMOVE*') { return 'REMOVE' }
    $response = $script:ConfirmationResponse
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
    New-FixtureFile (Join-Path $script:runtimeCacheDir '.gitkeep') ''
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'sentinel.cache') 'cache'
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'pytest\nodeids') 'cache child'
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'uv\.gitkeep') ''
    New-FixtureFile (Join-Path $script:serverDir '__pycache__\module.cpython-314.pyc') 'server bytecode'
    New-FixtureFile (Join-Path $script:serverDir 'services\predictions\__pycache__\module.cpython-314.pyc') 'nested bytecode'
    New-FixtureFile (Join-Path $script:venvDir '__pycache__\module.cpython-314.pyc') 'venv bytecode'
    New-FixtureFile (Join-Path $script:serverDir '.pytest_cache\v\cache\nodeids') 'pytest cache'
    New-FixtureFile (Join-Path $script:serverDir '.ruff_cache\content\hash') 'ruff cache'
    New-FixtureFile (Join-Path $script:serverDir '.mypy_cache\3.14\meta.json') 'mypy cache'
    New-FixtureFile (Join-Path $script:serverDir 'tests\.coverage') 'coverage cache'
    New-FixtureFile (Join-Path $script:clientDir '.vite\deps\metadata.json') 'vite cache'
    New-FixtureFile (Join-Path $script:clientDir 'node_modules\package-a\.cache\entry.json') 'dependency cache'
    New-FixtureFile (Join-Path $script:clientDir 'node_modules\package-a\index.js') 'installed package'
    New-FixtureFile (Join-Path $script:clientDir 'tsconfig.tsbuildinfo') 'typescript build info'
    New-FixtureFile (Join-Path $script:repoRoot 'app\tests\unit\__pycache__\test.cpython-314.pyc') 'test bytecode'
    New-FixtureFile (Join-Path $script:repoRoot 'assets\QA\frontend-e2e-artifacts\trace.zip') 'playwright trace'
    New-FixtureFile (Join-Path $script:repoRoot 'assets\QA\frontend-e2e-junit-chromium.xml') 'playwright junit'
    New-FixtureFile (Join-Path $script:repoRoot 'assets\QA\frontend-viewport-1100-chromium.png') 'viewport capture'
    New-FixtureFile (Join-Path $script:repoRoot 'assets\QA\val17-training-active-1440x900.png') 'validation capture'
    New-FixtureFile (Join-Path $script:repoRoot 'assets\QA\keep-note.txt') 'unknown QA file'
    New-FixtureFile (Join-Path $script:DataRoot '.database-config.json.1234567890.tmp') 'configuration temp'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\.broken.staging-0123456789abcdef0123456789abcdef\partial.bin') 'incomplete checkpoint'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\.saved_model.keras.0123456789abcdef0123456789abcdef.tmp.keras') 'checkpoint temp'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\valid-checkpoint\.complete.0123456789abcdef0123456789abcdef.tmp') 'completion marker temp'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\valid-checkpoint\saved_model.keras') 'valid checkpoint model'
    New-FixtureFile (Join-Path $script:repoRoot 'settings\.env.1234567890.tmp') 'environment temp'
    New-FixtureFile (Join-Path $script:runtimeRoot 'python\python.zip') 'partial runtime download'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'persistent database'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\model.pt') 'persistent checkpoint'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\current.log') 'persistent log'
    $neighbor = Join-Path $script:runtimeRoot 'cache-neighbor'
    New-FixtureFile (Join-Path $neighbor 'keep.txt') 'keep neighbor'

    $outsideMarker = Join-Path $script:ExternalRoot 'outside.txt'
    New-FixtureFile $outsideMarker 'outside target'
    $junction = Join-Path $script:runtimeCacheDir 'external-link'
    New-Item -ItemType Junction -Path $junction -Target $script:ExternalRoot -ErrorAction Stop | Out-Null

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'Cache'

    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:runtimeCacheDir 'sentinel.cache'))) 'Clear cache left its root sentinel.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:runtimeCacheDir 'pytest\nodeids'))) 'Clear cache left a nested cache sentinel.'
    Assert-Condition (Test-Path -LiteralPath (Join-Path $script:runtimeCacheDir '.gitkeep')) 'Clear cache removed the canonical cache-root marker.'
    Assert-Condition (@(Get-ChildItem -LiteralPath $script:runtimeCacheDir -Directory -Force).Count -eq 0) 'Clear cache left a runtime cache folder.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:serverDir '__pycache__'))) 'Clear cache left the server bytecode directory.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:serverDir 'services\predictions\__pycache__'))) 'Clear cache left a nested server bytecode directory.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:serverDir '.pytest_cache'))) 'Clear cache left pytest cache output.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:serverDir '.ruff_cache'))) 'Clear cache left Ruff cache output.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:serverDir '.mypy_cache'))) 'Clear cache left mypy cache output.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:serverDir 'tests\.coverage'))) 'Clear cache left coverage data.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:clientDir '.vite'))) 'Clear cache left a client Vite cache.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:clientDir 'node_modules\package-a\.cache'))) 'Clear cache left node_modules cache output.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:clientDir 'tsconfig.tsbuildinfo'))) 'Clear cache left TypeScript build information.'
    Assert-FileContains (Join-Path $script:clientDir 'node_modules\package-a\index.js') 'installed package'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:repoRoot 'app\tests\unit\__pycache__'))) 'Clear cache left test bytecode.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:repoRoot 'assets\QA\frontend-e2e-artifacts'))) 'Clear cache left Playwright reports.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:repoRoot 'assets\QA\frontend-e2e-junit-chromium.xml'))) 'Clear cache left Playwright JUnit output.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:repoRoot 'assets\QA\frontend-viewport-1100-chromium.png'))) 'Clear cache left a generated frontend viewport screenshot.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:repoRoot 'assets\QA\val17-training-active-1440x900.png'))) 'Clear cache left a generated validation screenshot.'
    Assert-FileContains (Join-Path $script:repoRoot 'assets\QA\keep-note.txt') 'unknown QA file'
    foreach ($temporaryPath in @(
        (Join-Path $script:DataRoot '.database-config.json.1234567890.tmp'),
        (Join-Path $script:DataRoot 'checkpoints\.broken.staging-0123456789abcdef0123456789abcdef'),
        (Join-Path $script:DataRoot 'checkpoints\.saved_model.keras.0123456789abcdef0123456789abcdef.tmp.keras'),
        (Join-Path $script:DataRoot 'checkpoints\valid-checkpoint\.complete.0123456789abcdef0123456789abcdef.tmp'),
        (Join-Path $script:repoRoot 'settings\.env.1234567890.tmp'),
        (Join-Path $script:runtimeRoot 'python\python.zip')
    )) { Assert-Condition (-not (Test-Path -LiteralPath $temporaryPath)) "Clear cache left an incomplete temporary artifact '$temporaryPath'." }
    Assert-FileContains (Join-Path $script:DataRoot 'checkpoints\valid-checkpoint\saved_model.keras') 'valid checkpoint model'
    Assert-Condition (-not (Test-Path -LiteralPath $junction)) 'Clear cache left a recognized junction under its owned cache root.'
    Assert-FileContains $outsideMarker 'outside target'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'persistent database'
    Assert-FileContains (Join-Path $script:DataRoot 'checkpoints\model.pt') 'persistent checkpoint'
    Assert-FileContains (Join-Path $script:DataRoot 'logs\current.log') 'persistent log'
    Assert-FileContains (Join-Path $neighbor 'keep.txt') 'keep neighbor'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'Cache'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'persistent database'
}

function Test-CleanupDryRunAndPathValidation {
    Reset-Fixture
    $ownedRoot = Join-Path $script:FixtureRoot 'owned'
    $ownedFile = Join-Path $ownedRoot 'nested\cache.bin'
    New-FixtureFile $ownedFile 'keep during preview'
    $target = New-CleanupTarget -Path (Join-Path $ownedRoot 'nested') -AllowedRoot $ownedRoot
    $inventory = Get-CleanupInventory -Targets @($target)
    $result = Invoke-CleanupInventory -Inventory $inventory -WhatIf
    $resolvedOwnedFile = (Get-Item -LiteralPath $ownedFile).FullName
    Assert-Condition ($result.Planned -contains $resolvedOwnedFile) 'Dry run did not include the nested file target.'
    Assert-FileContains $ownedFile 'keep during preview'

    $outsideFile = Join-Path $script:ExternalRoot 'outside-cache.bin'
    New-FixtureFile $outsideFile 'outside remains'
    $unsafe = New-CleanupTarget -Path $outsideFile -AllowedRoot $ownedRoot -Mode 'File'
    $unsafeInventory = Get-CleanupInventory -Targets @($unsafe)
    Assert-Condition ($unsafeInventory.Failed.Count -gt 0) 'Path validation did not reject a target outside its allowed root.'
    Assert-FileContains $outsideFile 'outside remains'

    $linkedRoot = Join-Path $ownedRoot 'linked-root'
    New-Item -ItemType Junction -Path $linkedRoot -Target $script:ExternalRoot -ErrorAction Stop | Out-Null
    $linkedTarget = New-CleanupTarget -Path (Join-Path $linkedRoot 'outside-cache.bin') -AllowedRoot $linkedRoot -Mode 'File'
    $linkedInventory = Get-CleanupInventory -Targets @($linkedTarget)
    Assert-Condition ($linkedInventory.Failed.Count -gt 0) 'Path validation allowed a target below a reparse-point root.'
    Assert-FileContains $outsideFile 'outside remains'

    $lockedPath = Join-Path $ownedRoot 'locked.cache'
    New-FixtureFile $lockedPath 'locked remains'
    $lockedStream = [IO.File]::Open($lockedPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
    try {
        $lockedInventory = Get-CleanupInventory -Targets @((New-CleanupTarget -Path $lockedPath -AllowedRoot $ownedRoot -Mode 'File'))
        $lockedResult = Invoke-CleanupInventory -Inventory $lockedInventory
        Assert-Condition ($lockedResult.Failed.Count -gt 0) 'A locked file was not reported as a cleanup failure.'
    } finally { $lockedStream.Dispose() }
    Assert-FileContains $lockedPath 'locked remains'

    $inaccessibleDirectory = Join-Path $ownedRoot 'inaccessible'
    New-FixtureFile (Join-Path $inaccessibleDirectory 'protected.bin') 'permission protected'
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $denyRule = [Security.AccessControl.FileSystemAccessRule]::new(
        $sid,
        [Security.AccessControl.FileSystemRights]::ListDirectory,
        [Security.AccessControl.AccessControlType]::Deny
    )
    $originalAcl = Get-Acl -LiteralPath $inaccessibleDirectory
    $originalAcl.AddAccessRule($denyRule)
    Set-Acl -LiteralPath $inaccessibleDirectory -AclObject $originalAcl
    try {
        $inaccessibleTarget = New-CleanupTarget -Path $inaccessibleDirectory -AllowedRoot $ownedRoot
        $inaccessibleInventory = Get-CleanupInventory -Targets @($inaccessibleTarget)
        Assert-Condition ($inaccessibleInventory.Failed.Count -gt 0) 'An inaccessible directory was not reported as a cleanup failure.'
    } finally {
        $restoredAcl = Get-Acl -LiteralPath $inaccessibleDirectory
        [void]$restoredAcl.RemoveAccessRuleSpecific($denyRule)
        Set-Acl -LiteralPath $inaccessibleDirectory -AclObject $restoredAcl
    }
    Assert-FileContains (Join-Path $inaccessibleDirectory 'protected.bin') 'permission protected'

    $linkedDataRoot = Join-Path $ownedRoot 'linked-data-root'
    New-Item -ItemType Junction -Path $linkedDataRoot -Target $script:ExternalRoot -ErrorAction Stop | Out-Null
    $env:FAIRS_DATA_DIR = $linkedDataRoot
    Assert-Throws { Assert-DataCacheIsolation } 'traverses a symbolic link or junction'
    $env:FAIRS_DATA_DIR = $script:DataRoot

    $overlappingDataRoot = Join-Path $script:clientDir 'dist\persistent-data'
    New-FixtureFile (Join-Path $overlappingDataRoot 'database-config.json') '{"schema_version":1,"backend":"postgresql","postgresql":{"engine":"postgresql+psycopg"}}'
    $env:FAIRS_DATA_DIR = $overlappingDataRoot
    Assert-Throws { Get-CacheCleanupTargets } 'overlaps persistent FAIRS data root'
    Assert-FileContains (Join-Path $overlappingDataRoot 'database-config.json') '{"schema_version":1,"backend":"postgresql","postgresql":{"engine":"postgresql+psycopg"}}'
    $env:FAIRS_DATA_DIR = $script:DataRoot
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
    Reset-Fixture
    $configuredDatabase = Join-Path $script:DataRoot 'database-custom.sqlite'
    $databaseConfiguration = @{
        schema_version = 1
        backend = 'sqlite'
        sqlite = @{ path = $configuredDatabase; insert_batch_size = 1000 }
    } | ConvertTo-Json -Depth 4
    New-FixtureFile (Join-Path $script:DataRoot 'database-config.json') $databaseConfiguration
    New-FixtureFile $configuredDatabase 'configured database'
    New-FixtureFile "$configuredDatabase-shm" 'shared memory'
    New-FixtureFile "$configuredDatabase-wal" 'write ahead log'
    New-FixtureFile "$configuredDatabase-journal" 'rollback journal'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'database'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\run.log') 'log'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\notes.txt') 'keep note'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'AllData'

    foreach ($path in @($configuredDatabase, "$configuredDatabase-shm", "$configuredDatabase-wal", "$configuredDatabase-journal")) {
        Assert-Condition (-not (Test-Path -LiteralPath $path)) "Remove all data left configured SQLite file '$path'."
    }
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'database'
    Assert-Condition (Test-Path -LiteralPath (Join-Path $script:DataRoot 'database-config.json')) 'Remove all data deleted the standalone database configuration.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:DataRoot 'logs\run.log'))) 'Remove all data left a log file.'
    Assert-FileContains (Join-Path $script:DataRoot 'logs\notes.txt') 'keep note'
    Assert-FileContains (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'

    Reset-Fixture
    $postgresConfiguration = @{
        schema_version = 1
        backend = 'postgresql'
        postgresql = @{ engine = 'postgresql+psycopg'; host = 'localhost' }
    } | ConvertTo-Json -Depth 4
    New-FixtureFile (Join-Path $script:DataRoot 'database-config.json') $postgresConfiguration
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'inactive SQLite database'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\run.log') 'log'

    $script:LauncherInteractive = $true
    Invoke-MaintenanceAction 'AllData'

    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'inactive SQLite database'
    Assert-Condition (Test-Path -LiteralPath (Join-Path $script:DataRoot 'database-config.json')) 'Remove all data deleted PostgreSQL configuration.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:DataRoot 'logs\run.log'))) 'Remove all data left a log file in PostgreSQL mode.'
}

function Test-Uninstall {
    Reset-Fixture
    New-FixtureFile (Join-Path $script:runtimeRoot '.gitkeep') ''
    New-FixtureFile (Join-Path $script:runtimeCacheDir '.gitkeep') ''
    New-FixtureFile (Join-Path $script:runtimeRoot 'python\python.exe') 'runtime'
    New-FixtureFile (Join-Path $script:runtimeCacheDir 'cache.bin') 'cache'
    New-FixtureFile (Join-Path $script:venvDir 'Scripts\python.exe') 'venv'
    New-FixtureFile (Join-Path $script:clientDir 'node_modules\marker') 'dependency'
    New-FixtureFile (Join-Path $script:clientDir 'dist\index.html') 'build'
    New-FixtureFile (Join-Path $script:runtimeRoot 'custom-tool\keep.txt') 'unknown runtime sibling'
    New-FixtureFile (Join-Path $script:serverDir 'pyproject.toml') 'server project metadata'
    New-FixtureFile (Join-Path $script:serverDir 'uv.lock') 'server lockfile'
    New-FixtureFile (Join-Path $script:clientDir 'package-lock.json') 'frontend lock metadata'
    $configuredDatabase = Join-Path $script:ExternalRoot 'standard-user.sqlite'
    $databaseConfiguration = @{ schema_version = 1; backend = 'sqlite'; sqlite = @{ path = $configuredDatabase } } | ConvertTo-Json -Compress -Depth 4
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'user database'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db-shm') 'user database shared memory'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db-wal') 'user database write ahead log'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db-journal') 'user database rollback journal'
    New-FixtureFile (Join-Path $script:DataRoot 'database-config.json') $databaseConfiguration
    New-FixtureFile $configuredDatabase 'external configured database'
    New-FixtureFile "$configuredDatabase-shm" 'external shared memory'
    New-FixtureFile "$configuredDatabase-wal" 'external write ahead log'
    New-FixtureFile "$configuredDatabase-journal" 'external rollback journal'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\run.log') 'application log'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\notes.txt') 'keep log note'
    New-FixtureFile (Join-Path $script:DataRoot 'unknown.txt') 'unknown data'

    $script:LauncherInteractive = $true
    $script:UninstallMode = 'Standard'
    Invoke-MaintenanceAction 'Uninstall'

    Assert-Condition (Test-Path -LiteralPath (Join-Path $script:runtimeRoot '.gitkeep')) 'Uninstall removed the runtime marker.'
    foreach ($path in @(
        (Join-Path $script:runtimeRoot 'python'),
        $script:venvDir,
        (Join-Path $script:clientDir 'node_modules'),
        (Join-Path $script:clientDir 'dist')
    )) {
        Assert-Condition (-not (Test-Path -LiteralPath $path)) "Uninstall left owned path '$path'."
    }
    Assert-Condition (Test-Path -LiteralPath (Join-Path $script:runtimeCacheDir '.gitkeep')) 'Uninstall removed the canonical cache marker.'
    Assert-Condition (@(Get-ChildItem -LiteralPath $script:runtimeCacheDir -Force | Where-Object { $_.Name -ne '.gitkeep' }).Count -eq 0) 'Uninstall left disposable cache content.'
    Assert-FileContains (Join-Path $script:runtimeRoot 'custom-tool\keep.txt') 'unknown runtime sibling'
    Assert-FileContains (Join-Path $script:serverDir 'pyproject.toml') 'server project metadata'
    Assert-FileContains (Join-Path $script:serverDir 'uv.lock') 'server lockfile'
    Assert-FileContains (Join-Path $script:clientDir 'package-lock.json') 'frontend lock metadata'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'user database'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db-shm') 'user database shared memory'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db-wal') 'user database write ahead log'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db-journal') 'user database rollback journal'
    Assert-FileContains (Join-Path $script:DataRoot 'database-config.json') $databaseConfiguration
    foreach ($path in @($configuredDatabase, "$configuredDatabase-shm", "$configuredDatabase-wal", "$configuredDatabase-journal")) {
        Assert-Condition (Test-Path -LiteralPath $path) "Standard uninstall deleted configured persistent database path '$path'."
    }
    Assert-FileContains (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:DataRoot 'logs\run.log'))) 'Standard uninstall left an application log.'
    Assert-FileContains (Join-Path $script:DataRoot 'logs\notes.txt') 'keep log note'
    Assert-FileContains (Join-Path $script:DataRoot 'unknown.txt') 'unknown data'
    Assert-Condition (Test-Path -LiteralPath $script:envFile) 'Standard uninstall removed settings/.env.'
}

function Test-CompleteUninstall {
    Reset-Fixture
    $configuredDatabase = Join-Path $script:ExternalRoot 'outside-database.sqlite'
    $configuration = @{ schema_version = 1; backend = 'sqlite'; sqlite = @{ path = $configuredDatabase; insert_batch_size = 1000 } } | ConvertTo-Json -Depth 4
    New-FixtureFile (Join-Path $script:DataRoot 'database-config.json') $configuration
    New-FixtureFile $configuredDatabase 'configured database'
    New-FixtureFile "$configuredDatabase-shm" 'shared memory'
    New-FixtureFile "$configuredDatabase-wal" 'write ahead log'
    New-FixtureFile "$configuredDatabase-journal" 'rollback journal'
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'inactive database'
    New-FixtureFile (Join-Path $script:DataRoot 'checkpoints\model.pt') 'checkpoint'
    New-FixtureFile (Join-Path $script:DataRoot 'logs\run.log') 'application log'
    New-FixtureFile (Join-Path $script:DataRoot 'unknown.txt') 'preserve unknown'

    $script:LauncherInteractive = $true
    $script:UninstallMode = 'Complete'
    Invoke-MaintenanceAction 'Uninstall'

    foreach ($path in @($configuredDatabase, "$configuredDatabase-shm", "$configuredDatabase-wal", "$configuredDatabase-journal", (Join-Path $script:DataRoot 'database-config.json'), (Join-Path $script:DataRoot 'checkpoints\model.pt'), (Join-Path $script:DataRoot 'logs\run.log'), $script:envFile)) {
        Assert-Condition (-not (Test-Path -LiteralPath $path)) "Complete uninstall left known application data '$path'."
    }
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'inactive database'
    Assert-FileContains (Join-Path $script:DataRoot 'unknown.txt') 'preserve unknown'

    Reset-Fixture
    $postgresConfiguration = @{ schema_version = 1; backend = 'postgresql'; postgresql = @{ engine = 'postgresql+psycopg'; host = 'localhost' } } | ConvertTo-Json -Depth 4
    New-FixtureFile (Join-Path $script:DataRoot 'database-config.json') $postgresConfiguration
    New-FixtureFile (Join-Path $script:DataRoot 'database.db') 'local inactive database'
    $script:LauncherInteractive = $true
    $script:UninstallMode = 'Complete'
    Invoke-MaintenanceAction 'Uninstall'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $script:DataRoot 'database-config.json'))) 'Complete uninstall left local PostgreSQL configuration.'
    Assert-FileContains (Join-Path $script:DataRoot 'database.db') 'local inactive database'

    Reset-Fixture
    New-FixtureFile (Join-Path $script:runtimeRoot 'python\python.exe') 'runtime'
    New-FixtureFile (Join-Path $script:DataRoot 'database-config.json') '{invalid json'
    $before = @(Get-FixtureSnapshot)
    $script:LauncherInteractive = $true
    $script:UninstallMode = 'Complete'
    Assert-Throws { Uninstall-Application -Mode Complete } 'refusing persistent data removal'
    Assert-SnapshotEqual $before @(Get-FixtureSnapshot) 'Invalid database configuration fail-closed behavior'
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
    Cleanup-TestProcesses
}

function Test-LauncherOwnedProcessTreeCleanup {
    Reset-Fixture
    $qaRoot = Join-Path $script:RepositoryRoot 'assets\QA'
    Remove-SafeQaTree $script:ProcessFixtureRoot '.scratch-val19-process-'
    $script:ProcessFixtureRoot = Join-Path $qaRoot ".scratch-val19-launch-$PID-$([Guid]::NewGuid().ToString('N'))"
    $childScript = Join-Path $script:ProcessFixtureRoot 'owned-child-sleeper.ps1'
    $childPidPath = Join-Path $script:ProcessFixtureRoot 'owned-child.pid'
    $parentScript = Join-Path $script:ProcessFixtureRoot 'uvicorn-parent.ps1'
    $ordinaryScript = Join-Path $script:ProcessFixtureRoot 'ordinary-sleeper.ps1'
    New-FixtureFile $childScript 'Start-Sleep -Seconds 300'
    New-FixtureFile $ordinaryScript 'Start-Sleep -Seconds 300'
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
    Assert-Condition (Test-Path -LiteralPath $childPidPath) 'The launcher-owned process tree did not start its child.'
    $childId = [int](Get-Content -LiteralPath $childPidPath -Raw)
    $script:OwnedProcessIds.Add($childId)

    $ordinary = New-SleeperProcess $ordinaryScript
    $script:OtherProcessIds.Add($ordinary.Id)
    Stop-OwnedApplicationProcessTree -RootProcessId $parent.Id -Process $parent -GraceSeconds 0

    foreach ($processId in $script:OwnedProcessIds) {
        Assert-Condition ($null -eq (Get-Process -Id $processId -ErrorAction SilentlyContinue)) "Launcher cleanup left owned PID $processId running."
    }
    Assert-Condition ($null -ne (Get-Process -Id $ordinary.Id -ErrorAction SilentlyContinue)) 'Launcher cleanup stopped an unrelated process in the same fixture folder.'
    Cleanup-TestProcesses
}

function Test-ExitedLauncherParentCleanup {
    Reset-Fixture
    $qaRoot = Join-Path $script:RepositoryRoot 'assets\QA'
    Remove-SafeQaTree $script:ProcessFixtureRoot '.scratch-val19-launch-'
    $script:ProcessFixtureRoot = Join-Path $qaRoot ".scratch-val19-launch-$PID-$([Guid]::NewGuid().ToString('N'))"
    $childScript = Join-Path $script:ProcessFixtureRoot 'orphaned-child-sleeper.ps1'
    $childPidPath = Join-Path $script:ProcessFixtureRoot 'orphaned-child.pid'
    $parentScript = Join-Path $script:ProcessFixtureRoot 'exiting-parent.ps1'
    $ordinaryScript = Join-Path $script:ProcessFixtureRoot 'ordinary-sleeper.ps1'
    New-FixtureFile $childScript 'Start-Sleep -Seconds 300'
    New-FixtureFile $ordinaryScript 'Start-Sleep -Seconds 300'
    $quotedChild = $childScript.Replace("'", "''")
    $quotedChildPid = $childPidPath.Replace("'", "''")
    $parentContents = @"
`$child = Start-Process -FilePath '$script:PowerShellExecutable' -ArgumentList '-NoLogo -NoProfile -File `"$quotedChild`"' -PassThru -WindowStyle Hidden
Set-Content -LiteralPath '$quotedChildPid' -Value `$child.Id
exit 0
"@
    New-FixtureFile $parentScript $parentContents

    $parent = New-SleeperProcess $parentScript
    $script:OwnedProcessIds.Add($parent.Id)
    $deadline = (Get-Date).AddSeconds(10)
    while (-not (Test-Path -LiteralPath $childPidPath) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
    Assert-Condition (Test-Path -LiteralPath $childPidPath) 'The exiting launcher parent did not start its child.'
    $childId = [int](Get-Content -LiteralPath $childPidPath -Raw)
    $script:OwnedProcessIds.Add($childId)
    Assert-Condition ($parent.WaitForExit(5000)) 'The launcher parent did not exit as expected.'
    Assert-Condition ($null -ne (Get-Process -Id $childId -ErrorAction SilentlyContinue)) 'The child did not survive long enough to test orphan cleanup.'

    $ordinary = New-SleeperProcess $ordinaryScript
    $script:OtherProcessIds.Add($ordinary.Id)
    Stop-OwnedApplicationProcessTree -RootProcessId $parent.Id -Process $parent -GraceSeconds 0

    Assert-Condition ($null -eq (Get-Process -Id $childId -ErrorAction SilentlyContinue)) 'Cleanup of an exited launcher parent left its child alive.'
    Assert-Condition ($null -ne (Get-Process -Id $ordinary.Id -ErrorAction SilentlyContinue)) 'Cleanup of an exited launcher parent stopped an unrelated process.'
    Cleanup-TestProcesses
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
    Test-EnvironmentDatabaseIndependence
    Test-DeclinedAndNoninteractiveActions
    Test-RunningApplicationGuards
    Test-RemoveLogs
    Test-ClearCache
    Test-CleanupDryRunAndPathValidation
    Test-RemoveCheckpoints
    Test-RemoveAllData
    Test-Uninstall
    Test-CompleteUninstall
    Test-StopApplicationProcesses
    Test-LauncherOwnedProcessTreeCleanup
    Test-ExitedLauncherParentCleanup
    Write-Output 'VAL-19 maintenance behavior passed in isolated fixtures.'
} finally {
    Cleanup-TestProcesses
    Remove-SafeTree $script:FixtureRoot 'fairs-val19-'
    Remove-SafeTree $script:ExternalRoot 'fairs-val19-external-'
    Remove-SafeQaTree $script:ProcessFixtureRoot '.scratch-val19-launch-'
    Remove-SafeQaTree $script:ProcessExternalRoot '.scratch-val19-external-'
}
