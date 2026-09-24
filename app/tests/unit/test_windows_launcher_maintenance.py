from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


TEST_SCRIPT = Path(__file__).with_name("windows_launcher_maintenance.ps1")


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
