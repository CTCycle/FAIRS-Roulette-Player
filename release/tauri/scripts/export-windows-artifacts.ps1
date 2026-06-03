[CmdletBinding()]
param(
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$clientDir = Join-Path $repoRoot "app\\client"
$tauriDir = Join-Path $clientDir "src-tauri"
$releaseDir = Join-Path $clientDir "src-tauri\target\release"
$bundleDir = Join-Path $releaseDir "bundle"

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $outputDir = Join-Path $repoRoot "release\windows"
} else {
  $outputDir = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputPath))
}

$installersDir = Join-Path $outputDir "installers"
$portableDir = Join-Path $outputDir "portable"
$portableRuntimeDir = Join-Path $portableDir "runtime"

if (-not (Test-Path $bundleDir)) {
  throw "Bundle directory not found. Run 'npm run tauri:build' first. Missing: $bundleDir"
}

if (Test-Path $outputDir) {
  Remove-Item -Recurse -Force $outputDir
}

New-Item -ItemType Directory -Path $installersDir -Force | Out-Null
New-Item -ItemType Directory -Path $portableDir -Force | Out-Null
New-Item -ItemType Directory -Path $portableRuntimeDir -Force | Out-Null

$installerArtifacts = @()

$nsisDir = Join-Path $bundleDir "nsis"
if (Test-Path $nsisDir) {
  $nsisFiles = Get-ChildItem -Path $nsisDir -Filter "*.exe" -File
  foreach ($file in $nsisFiles) {
    Copy-Item -Path $file.FullName -Destination $installersDir -Force
    $installerArtifacts += Join-Path $installersDir $file.Name
  }
}

$msiDir = Join-Path $bundleDir "msi"
if (Test-Path $msiDir) {
  $msiFiles = Get-ChildItem -Path $msiDir -Filter "*.msi" -File
  foreach ($file in $msiFiles) {
    Copy-Item -Path $file.FullName -Destination $installersDir -Force
    $installerArtifacts += Join-Path $installersDir $file.Name
  }
}

$portableExeCandidates = Get-ChildItem -Path $releaseDir -Filter "*.exe" -File |
  Where-Object { $_.Name -notmatch "(?i)(setup|installer|uninstall|updater)" }

if ($portableExeCandidates.Count -eq 0) {
  throw "No portable desktop executable found in $releaseDir. Run release\tauri\build_with_tauri.bat and confirm Tauri release output."
}

foreach ($file in $portableExeCandidates) {
  Copy-Item -Path $file.FullName -Destination $portableDir -Force
}

$portablePayloadSourceDir = Join-Path $tauriDir "runtime"
if (Test-Path $portablePayloadSourceDir) {
  Copy-Item -Path (Join-Path $portablePayloadSourceDir "*") -Destination $portableRuntimeDir -Recurse -Force
} else {
  $portablePayloadEntries = @("app", "settings", "runtimes", "resources", "_up_")

  foreach ($entry in $portablePayloadEntries) {
    $sourcePath = Join-Path $releaseDir $entry
    if (Test-Path $sourcePath) {
      $destinationPath = Join-Path $portableRuntimeDir $entry
      Copy-Item -Path $sourcePath -Destination $destinationPath -Recurse -Force
    }
  }
}

$requiredPortableEntries = @(
  "app\server",
  "app\scripts",
  "settings",
  "app\client\dist",
  "app\resources\database.db",
  "runtimes\uv\uv.exe",
  "runtimes\python\python.exe"
)

foreach ($entry in $requiredPortableEntries) {
  $portablePath = Join-Path $portableRuntimeDir $entry
  if (-not (Test-Path $portablePath)) {
    throw "Portable export is incomplete. Missing required payload path: $portablePath"
  }
}

$instructions = @"
FAIRS desktop build output

1) Preferred for users:
   Open installers\ and run the setup executable (.exe) or .msi.

2) Portable executable:
   portable\ contains the app .exe.
   portable\runtime\ contains the required runtime payload.
   Keep the .exe beside the runtime\ folder.

Generated from:
$bundleDir
"@
Set-Content -Path (Join-Path $outputDir "README.txt") -Value $instructions -Encoding ascii

Write-Host "[OK] Exported Windows artifacts to: $outputDir"
Write-Host "[INFO] Installers:"
if ($installerArtifacts.Count -eq 0) {
  Write-Host " - none found"
} else {
  $installerArtifacts | ForEach-Object { Write-Host " - $_" }
}
Write-Host "[INFO] Portable executables:"
$portableFiles = Get-ChildItem -Path $portableDir -Filter "*.exe" -File
if ($portableFiles.Count -eq 0) {
  Write-Host " - none found"
} else {
  $portableFiles | ForEach-Object { Write-Host " - $($_.FullName)" }
}
Write-Host "[INFO] Portable runtime payload:"
Write-Host " - $portableRuntimeDir"
