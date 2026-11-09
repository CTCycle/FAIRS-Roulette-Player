# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


TEST_SCRIPT = Path(__file__).with_name("windows_launcher_maintenance.ps1")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


###############################################################################
def test_launcher_maintenance_actions_in_isolated_fixture() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only launcher maintenance harness")

    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required for Windows launcher maintenance coverage")

    result = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(TEST_SCRIPT),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, (
        f"PowerShell maintenance harness failed ({result.returncode}).\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


###############################################################################
def test_batch_entrypoint_uses_windows_powershell_and_menu_hides_launch() -> None:
    launcher = (REPOSITORY_ROOT / "setup_and_maintenance.ps1").read_text(
        encoding="utf-8"
    )
    wrapper = (REPOSITORY_ROOT / "start_on_windows.bat").read_text(encoding="utf-8")
    menu_start = launcher.index("function Get-LauncherMenuEntries")
    menu_end = launcher.index("\nfunction Write-MenuItem", menu_start)
    menu = launcher[menu_start:menu_end]

    assert "powershell.exe" in wrapper
    assert "pwsh.exe" not in wrapper
    assert "setup_and_maintenance.ps1" in wrapper
    assert "-Launch" in wrapper
    assert "if ($Launch)" in launcher
    assert "Key = 'Launch'" not in menu