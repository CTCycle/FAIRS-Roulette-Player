from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2].parent
LAUNCHER_PATH = REPOSITORY_ROOT / "start_on_windows.ps1"


def _launcher_source() -> str:
    return LAUNCHER_PATH.read_text(encoding="utf-8")


def _section(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_launcher_has_no_legacy_always_rebuild_switch() -> None:
    assert "always_rebuild" not in _launcher_source().lower()


def test_launch_uses_port_resolver_before_runtime_work() -> None:
    source = _launcher_source()
    start_application = _section(
        source,
        "function Start-Application {",
        "# -----------------------------------------------------------------------------\n# Database and validation operations",
    )

    assert "Assert-ApplicationStopped" not in start_application
    assert start_application.index("Resolve-LaunchPortConflicts") < start_application.index(
        "Ensure-PortableRuntimes"
    )
    assert "if (-not (Resolve-LaunchPortConflicts" in start_application
    assert "return $false" in start_application
    assert "return $true" in start_application


def test_port_conflicts_are_grouped_and_stopped_once_per_pid() -> None:
    source = _launcher_source()
    conflict_discovery = _section(
        source,
        "function Get-ConfiguredPortConflicts {",
        "function Get-PortConflictDescription",
    )
    stop_conflicts = _section(
        source,
        "function Stop-PortConflictProcesses {",
        "function Resolve-LaunchPortConflicts",
    )

    assert "$recordsByPid" in conflict_discovery
    assert "Get-PortProcessIds" in conflict_discovery
    assert "Ports =" in conflict_discovery
    assert "PortLabels =" in conflict_discovery
    assert "HashSet[int]" in stop_conflicts
    assert "Stop-Process -Id $processId" in stop_conflicts
    assert "TargetedProcessIds" in stop_conflicts


def test_frontend_freshness_uses_content_fingerprint_state() -> None:
    source = _launcher_source()
    assert "LastWriteTimeUtc" not in source
    assert "function Get-ContentFingerprint" in source
    assert "Get-FileHash -LiteralPath $fullPath -Algorithm SHA256" in source
    assert "function Get-FrontendBuildFingerprint" in source
    assert "function Read-FrontendBuildState" in source
    assert "function Write-FrontendBuildState" in source
    assert "dist\\.fairs-build-state.json" in source
    assert "fingerprint" in source


def test_frontend_build_inputs_match_documented_invalidation_scope() -> None:
    source = _launcher_source()
    build_inputs = _section(
        source,
        "function Get-FrontendBuildInputFiles {",
        "function Get-FrontendBuildFingerprint",
    )

    for input_name in (
        "index.html",
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "tsconfig.app.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "'src'",
        "'public'",
    ):
        assert input_name in build_inputs
    assert "README.md" not in build_inputs
    assert "eslint.config.js" not in build_inputs


def test_backend_and_frontend_dependency_recovery_are_independent() -> None:
    source = _launcher_source()
    start_application = _section(
        source,
        "function Start-Application {",
        "# -----------------------------------------------------------------------------\n# Database and validation operations",
    )

    for symbol in (
        "Test-BackendDependenciesCurrent",
        "Sync-BackendDependencies",
        "Test-FrontendDependenciesCurrent",
        "Sync-FrontendDependencies",
        "Test-FrontendBuildCurrent",
        "Invoke-FrontendBuild",
    ):
        assert symbol in start_application
    assert start_application.index("Test-BackendDependenciesCurrent") < start_application.index(
        "Test-FrontendDependenciesCurrent"
    )
    assert start_application.index("Test-FrontendDependenciesCurrent") < start_application.index(
        "Test-FrontendBuildCurrent"
    )
    assert "Test-DependenciesReady" not in source
    assert "Test-BackendPackageCurrent" not in source


def test_explicit_install_and_rebuild_options_still_build_frontend() -> None:
    source = _launcher_source()
    menu = _section(source, "function Show-Menu {", "Set-CacheEnvironment\nShow-Menu")

    assert "'Install'" in menu
    assert "Install-Dependencies -PruneCache -InstallationType $installationType" in menu
    assert "Build-Frontend" in menu
    assert "'Rebuild' { Build-Frontend }" in menu
    assert "'Launch' { if (Start-Application) { exit 0 } }" in menu


def test_maintenance_menu_entries_dispatch_their_handlers() -> None:
    source = _launcher_source()
    menu = _section(source, "function Show-Menu {", "Set-CacheEnvironment\nShow-Menu")

    for key, handler in (
        ("Logs", "Remove-Logs"),
        ("Cache", "Clear-Cache"),
        ("Checkpoints", "Remove-Checkpoints"),
        ("AllData", "Remove-AllData"),
        ("Uninstall", "Uninstall-Application"),
        ("StopProcesses", "Stop-ApplicationProcesses"),
    ):
        assert f"'{key}' {{ {handler} }}" in menu


def test_standard_runner_supports_isolated_cache_root() -> None:
    runner = (REPOSITORY_ROOT / "app" / "tests" / "run_tests.bat").read_text(encoding="utf-8")

    cache_root_override = 'if not "%STANDARD_TEST_CACHE_ROOT%"=="" set "RUNTIME_CACHE_DIR=%STANDARD_TEST_CACHE_ROOT%"'
    assert cache_root_override in runner
    assert runner.index(cache_root_override) < runner.index('set "UV_CACHE_DIR=%RUNTIME_CACHE_DIR%\\uv"')
    assert runner.index(cache_root_override) < runner.index('set "PYTEST_BASETEMP_DIR=%RUNTIME_CACHE_DIR%\\pytest-tmp"')


def test_standard_runner_builds_frontend_from_the_client_directory() -> None:
    runner = (REPOSITORY_ROOT / "app" / "tests" / "run_tests.bat").read_text(encoding="utf-8")
    build_phase = runner.split("echo [INFO] Building frontend...", 1)[1].split(
        "curl -s --max-time 2 \"%APP_TEST_FRONTEND_URL%\"", 1
    )[0]

    assert 'pushd "%CLIENT_DIR%" >nul' in build_phase
    assert 'call "%NPM_CMD%" run build' in build_phase
    assert 'set "FRONTEND_BUILD_RC=!ERRORLEVEL!"' in build_phase
    assert 'if not "!FRONTEND_BUILD_RC!"=="0"' in build_phase
    assert 'popd >nul' in build_phase


def test_standard_runner_wait_loops_do_not_depend_on_interactive_stdin() -> None:
    runner = (REPOSITORY_ROOT / "app" / "tests" / "run_tests.bat").read_text(encoding="utf-8")
    wait_loop = runner.split(":wait_loop", 1)[1].split("echo [STEP] Running Python tests...", 1)[0]

    assert wait_loop.count('powershell.exe -NoProfile -Command "Start-Sleep -Seconds 1"') == 2
    assert "timeout /t 1 /nobreak" not in wait_loop


def test_dependency_state_is_published_only_by_successful_sync_paths() -> None:
    source = _launcher_source()
    backend_sync = _section(
        source,
        "function Sync-BackendDependencies {",
        "function Sync-FrontendDependencies",
    )
    frontend_sync = _section(
        source,
        "function Sync-FrontendDependencies {",
        "function Invoke-FrontendBuild",
    )

    assert ".fairs-install-state.json" in source
    assert "uv sync failed with exit code" in backend_sync
    assert "npm dependency installation failed with exit code" in frontend_sync
    assert "Write-JsonStateFile" in backend_sync
    assert "Write-JsonStateFile" in frontend_sync
