from __future__ import annotations

import os

import pytest


os.environ.setdefault("KERAS_BACKEND", "torch")

from FAIRS.server.common.constants import CHECKPOINT_PATH
from FAIRS.server.repositories.database.postgres import (
    normalize_table_name as normalize_postgres_table_name,
)
from FAIRS.server.repositories.database.sqlite import (
    normalize_table_name as normalize_sqlite_table_name,
)
from FAIRS.server.repositories.serialization.data import normalize_dataset_name
from FAIRS.server.routes.training import build_checkpoint_path, normalize_checkpoint_name
from FAIRS.server.routes.upload import (
    normalize_csv_separator,
    normalize_filename,
    normalize_sheet_name,
)


def test_checkpoint_name_validation_rejects_path_traversal_patterns() -> None:
    for candidate in ("", ".", "..", "../x", "..\\x", "x/y", "C:temp", "bad\x00name"):
        with pytest.raises(ValueError):
            normalize_checkpoint_name(candidate)

    assert normalize_checkpoint_name("checkpoint_01") == "checkpoint_01"


def test_checkpoint_path_builder_stays_under_checkpoint_root() -> None:
    checkpoint_root = os.path.realpath(CHECKPOINT_PATH)
    resolved = build_checkpoint_path("safe-checkpoint")

    assert os.path.commonpath([checkpoint_root, resolved]) == checkpoint_root
    assert resolved == os.path.realpath(os.path.join(checkpoint_root, "safe-checkpoint"))


def test_upload_parameter_normalizers_apply_bounds() -> None:
    assert normalize_csv_separator(";") == ";"
    assert normalize_sheet_name(0) == 0
    assert normalize_sheet_name("Sheet1") == "Sheet1"
    assert normalize_filename(r"..\dataset.csv") == "dataset.csv"

    with pytest.raises(ValueError):
        normalize_csv_separator("::")
    with pytest.raises(ValueError):
        normalize_sheet_name(-1)
    with pytest.raises(ValueError):
        normalize_sheet_name("x" * 129)
    with pytest.raises(ValueError):
        normalize_filename(None)
    with pytest.raises(ValueError):
        normalize_filename("bad\x00.csv")


def test_dataset_name_normalization_rejects_invalid_values() -> None:
    assert normalize_dataset_name("training_set") == "training_set"

    with pytest.raises(ValueError):
        normalize_dataset_name("")
    with pytest.raises(ValueError):
        normalize_dataset_name("x" * 129)
    with pytest.raises(ValueError):
        normalize_dataset_name("bad\x00name")


def test_table_name_allowlist_blocks_injection_patterns() -> None:
    assert normalize_sqlite_table_name("datasets") == "datasets"
    assert normalize_postgres_table_name("datasets") == "datasets"

    for candidate in (
        "datasets ",
        " datasets",
        "datasets;DROP TABLE datasets",
        "datasets\" OR 1=1 --",
        "unknown_table",
    ):
        with pytest.raises(ValueError):
            normalize_sqlite_table_name(candidate)
        with pytest.raises(ValueError):
            normalize_postgres_table_name(candidate)
