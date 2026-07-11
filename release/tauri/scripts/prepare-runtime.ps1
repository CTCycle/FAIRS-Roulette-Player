[CmdletBinding()]
param([string]$OutputPath = '')

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$server = Join-Path $repoRoot 'app\server'
$client = Join-Path $repoRoot 'app\client'
$venv = Join-Path $server '.venv'
$pythonRuntime = Join-Path $repoRoot 'runtimes\python'
$runtime = if ($OutputPath) { [IO.Path]::GetFullPath($OutputPath) } else { Join-Path $repoRoot 'app\src-tauri\runtime' }

if (-not (Test-Path (Join-Path $pythonRuntime 'python.exe'))) { throw "Missing Python 3.14 runtime: $pythonRuntime" }
if (-not (Test-Path (Join-Path $venv 'Lib\site-packages'))) { throw "Missing prepared backend environment: $venv. Run start_on_windows.ps1 install first." }
if (-not (Test-Path (Join-Path $client 'dist\index.html'))) { throw 'Missing frontend build. Run npm run build first.' }

if (Test-Path $runtime) { Remove-Item $runtime -Recurse -Force }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Copy-Item (Join-Path $pythonRuntime '*') $runtime -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $runtime 'Lib\site-packages') | Out-Null
Copy-Item (Join-Path $venv 'Lib\site-packages\*') (Join-Path $runtime 'Lib\site-packages') -Recurse -Force

$excluded = @('pytest*','playwright*','pytest_playwright*','ruff*','psutil*','iniconfig*','pluggy*','_pytest*')
foreach ($pattern in $excluded) {
    Get-ChildItem (Join-Path $runtime 'Lib\site-packages') -Force -ErrorAction SilentlyContinue |
        Where-Object Name -like $pattern | Remove-Item -Recurse -Force
}

$pth = Join-Path $runtime 'python314._pth'
$pthLines = Get-Content $pth | Where-Object { $_ -notmatch '^Lib\\site-packages$' -and $_ -notmatch '^import site$' -and $_ -notmatch '^#' -and $_.Trim() -ne '' }
@($pthLines + 'Lib\site-packages' + 'import site') | Set-Content -Encoding ascii $pth

New-Item -ItemType Directory -Force -Path (Join-Path $runtime 'app\server'),(Join-Path $runtime 'app\client\dist'),(Join-Path $runtime 'settings') | Out-Null
Copy-Item (Join-Path $server '*') (Join-Path $runtime 'app\server') -Recurse -Force -Exclude '.venv','__pycache__','.pytest_cache'
Copy-Item (Join-Path $client 'dist\*') (Join-Path $runtime 'app\client\dist') -Recurse -Force
Copy-Item (Join-Path $repoRoot 'settings\configurations.json') (Join-Path $runtime 'settings\configurations.json') -Force
Copy-Item (Join-Path $repoRoot 'LICENSE') (Join-Path $runtime 'LICENSE') -Force
Get-ChildItem $runtime -Recurse -Force -Include '__pycache__','*.pyc','*.pyo','*.whl' | Remove-Item -Recurse -Force

$probe = Join-Path $runtime 'python.exe'
$modules = @('fastapi','uvicorn','sqlalchemy','torch','keras','pandas')
foreach ($module in $modules) {
    & $probe -c "import $module" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Packaged runtime import failed: $module" }
}
Write-Host "[OK] Prepared offline runtime: $runtime"
