[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$tauri = Join-Path $repoRoot 'app\src-tauri'
$bundle = Join-Path $tauri 'target\release\bundle'
$release = Join-Path $repoRoot 'release\windows'
if (Test-Path $release) { Remove-Item $release -Recurse -Force }
New-Item -ItemType Directory -Force $release | Out-Null
$msi = Get-ChildItem (Join-Path $bundle 'msi') -Filter '*.msi' -File | Select-Object -First 1
if (-not $msi) { throw "MSI not found under $bundle\msi." }
Copy-Item $msi.FullName (Join-Path $release 'FAIRS-v2.4.0-windows-x64.msi')
$portable = Join-Path $release 'portable-root'
New-Item -ItemType Directory -Force $portable | Out-Null
$exe = Get-ChildItem (Join-Path $tauri 'target\release') -Filter '*.exe' -File | Where-Object Name -notmatch 'uninstall|setup' | Select-Object -First 1
if (-not $exe) { throw 'Desktop executable not found.' }
Copy-Item $exe.FullName (Join-Path $portable 'FAIRS.exe')
New-Item -ItemType File (Join-Path $portable 'portable.flag') | Out-Null
Copy-Item (Join-Path $tauri 'runtime') (Join-Path $portable 'runtime') -Recurse
Copy-Item (Join-Path $repoRoot 'LICENSE') (Join-Path $portable 'LICENSE')
Set-Content (Join-Path $portable 'THIRD_PARTY_NOTICES.txt') 'Third-party notices are generated as part of the release build.'
$zip = Join-Path $release 'FAIRS-v2.4.0-windows-x64-portable.zip'
Compress-Archive (Join-Path $portable '*') $zip -CompressionLevel Optimal
Remove-Item $portable -Recurse -Force
$hashes = @($release | Get-ChildItem -File | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash)  $($_.Path | Split-Path -Leaf)" })
Set-Content (Join-Path $release 'FAIRS-v2.4.0-SHA256SUMS.txt') $hashes
Write-Host "[OK] Release artifacts exported to $release"
