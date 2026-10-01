from __future__ import annotations

from pathlib import Path

import pytest

from server.common import cache as cache_config
from server.common import path as shared_paths


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
