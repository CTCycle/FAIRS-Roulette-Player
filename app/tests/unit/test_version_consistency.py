from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from server.common.constants import FASTAPI_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def test_application_version_is_consistent_and_semver() -> None:
    client_package = json.loads(
        (PROJECT_ROOT / "client" / "package.json").read_text(encoding="utf-8")
    )
    client_lock = json.loads(
        (PROJECT_ROOT / "client" / "package-lock.json").read_text(encoding="utf-8")
    )
    server_project = tomllib.loads(
        (PROJECT_ROOT / "server" / "pyproject.toml").read_text(encoding="utf-8")
    )
    server_lock = tomllib.loads(
        (PROJECT_ROOT / "server" / "uv.lock").read_text(encoding="utf-8")
    )
    openapi = json.loads(
        (PROJECT_ROOT / "shared" / "openapi.json").read_text(encoding="utf-8")
    )

    server_lock_version = next(
        package["version"]
        for package in server_lock["package"]
        if package["name"] == "fairs-server"
    )
    versions = {
        client_package["version"],
        client_lock["version"],
        client_lock["packages"][""]["version"],
        server_project["project"]["version"],
        server_lock_version,
        FASTAPI_VERSION,
        openapi["info"]["version"],
    }

    assert len(versions) == 1
    version = versions.pop()
    assert version != "0.0.0"
    assert SEMVER_PATTERN.fullmatch(version)
