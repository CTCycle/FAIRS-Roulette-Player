from __future__ import annotations

from pathlib import Path

import pytest

from server.common import cache as cache_config
from server.common import path as shared_paths


REPOSITORY_ROOT = Path(__file__).resolve().parents[2].parent

###############################################################################
def test_pytest_configuration_uses_the_repository_cache_root() -> None:
    configuration = (REPOSITORY_ROOT / "pytest.ini").read_text(encoding="utf-8")

    assert "cache_dir = runtimes/cache/pytest" in configuration
    assert "--basetemp=runtimes/cache/pytest-tmp" in configuration
    assert not (REPOSITORY_ROOT / "app/tests/pytest.ini").exists()

###############################################################################
def test_gitignore_keeps_defensive_cache_rules() -> None:
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")

    for rule in (
        "runtimes/**",
        "**/assets/QA/**",
        "__pycache__/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".mypy_cache/",
        ".uv-cache/",
    ):
        assert rule in gitignore

###############################################################################
def test_tooling_cache_paths_are_below_the_canonical_root() -> None:
    expected_fragments = {
        "ruff.toml": 'cache-dir = "runtimes/cache/ruff"',
        "app/client/vite.config.ts": "cacheDir: path.join(cacheRoot, 'vite')",
        "app/client/tsconfig.app.json": "../../runtimes/cache/typescript/tsconfig.app.tsbuildinfo",
        "app/client/tsconfig.node.json": "../../runtimes/cache/typescript/tsconfig.node.tsbuildinfo",
        "app/tests/run_tests.bat": "--basetemp \"%PYTEST_BASETEMP_DIR%\"",
    }

    for relative_path, expected_fragment in expected_fragments.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert expected_fragment in content

    server_project = (REPOSITORY_ROOT / "app/server/pyproject.toml").read_text(encoding="utf-8")
    assert "cache-dir" not in server_project
    test_runner = (REPOSITORY_ROOT / "app/tests/run_tests.bat").read_text(encoding="utf-8")
    assert "-m playwright install chromium" in test_runner

###############################################################################
def test_cache_environment_contains_only_canonical_paths() -> None:
    canonical_root = shared_paths.CACHE_PATH.resolve()
    for cache_path in cache_config.CACHE_DIRECTORIES.values():
        assert cache_path.resolve().is_relative_to(canonical_root)

    for configured_path in cache_config.CACHE_ENVIRONMENT.values():
        assert Path(configured_path).resolve().is_relative_to(canonical_root)

###############################################################################
def test_data_directory_cannot_overlap_canonical_cache_root() -> None:
    original_data_dir = shared_paths.DATA_DIR
    try:
        with pytest.raises(ValueError, match="disposable cache root"):
            shared_paths.configure_runtime_paths(shared_paths.CACHE_PATH / "data")
        with pytest.raises(ValueError, match="disposable cache root"):
            shared_paths.configure_runtime_paths(shared_paths.ROOT_DIR)
    finally:
        shared_paths.configure_runtime_paths(original_data_dir)
