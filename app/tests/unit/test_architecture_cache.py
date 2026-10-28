# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import ast
import pytest
from pathlib import Path
from server.common import cache as cache_config, path as shared_paths

SERVER_ROOT = Path(__file__).resolve().parents[2] / "server"

BOUNDARY_RULES: dict[str, tuple[str, ...]] = {
    "server.contracts": (
        "server.api",
        "server.services",
        "server.repositories",
        "server.configurations",
        "server.learning",
    ),
    "server.api": ("server.repositories", "server.learning"),
    "server.repositories": ("server.api", "server.services"),
    "server.learning": ("server.api", "server.services", "server.repositories"),
}


###############################################################################
def _module_name(path: Path) -> str:
    relative = path.relative_to(SERVER_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(("server", *parts))


###############################################################################
def _imported_modules(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return {name for name in imported if name.startswith("server.")}


###############################################################################
def test_backend_module_boundaries_remain_explicit() -> None:
    violations: list[str] = []

    for path in SERVER_ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        module = _module_name(path)
        for imported in _imported_modules(ast.parse(path.read_text(encoding="utf-8"))):
            forbidden = BOUNDARY_RULES.get(module)
            if forbidden is None:
                forbidden = tuple(
                    target
                    for owner, targets in BOUNDARY_RULES.items()
                    if module == owner or module.startswith(f"{owner}.")
                    for target in targets
                )
            if any(
                imported == target or imported.startswith(f"{target}.")
                for target in forbidden
            ):
                violations.append(f"{module} imports {imported}")

    assert not violations, "Architectural boundary violations:\n" + "\n".join(
        sorted(violations)
    )






REPOSITORY_ROOT = Path(__file__).resolve().parents[2].parent


###############################################################################
def test_cache_environment_contains_only_canonical_paths() -> None:
    canonical_root = shared_paths.CACHE_PATH.resolve()
    for cache_path in cache_config.CACHE_DIRECTORIES.values():
        assert cache_path.resolve().is_relative_to(canonical_root)

    for configured_path in cache_config.CACHE_ENVIRONMENT.values():
        assert Path(configured_path).resolve().is_relative_to(canonical_root)


###############################################################################
def test_custom_data_directory_remains_selectable() -> None:
    original_data_dir = shared_paths.DATA_DIR
    custom_root = REPOSITORY_ROOT / "custom-data-root-test"
    try:
        shared_paths.configure_runtime_paths(custom_root)
        expected_root = custom_root.resolve()
        assert shared_paths.DATA_DIR == expected_root
        assert shared_paths.DATA_ROOT == expected_root
        assert shared_paths.DATABASE_PATH == expected_root / "database.db"
        assert shared_paths.CHECKPOINT_PATH == expected_root / "checkpoints"
    finally:
        shared_paths.configure_runtime_paths(original_data_dir)


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
