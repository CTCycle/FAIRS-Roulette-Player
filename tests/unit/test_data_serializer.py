from __future__ import annotations

from unittest.mock import Mock, call

import pandas as pd

from FAIRS.server.common.constants import (
    DATASETS_TABLE,
    DATASET_OUTCOMES_TABLE,
    INFERENCE_SESSIONS_TABLE,
    INFERENCE_SESSION_STEPS_TABLE,
)
from FAIRS.server.repositories.serialization.data import DataSerializer


def test_delete_dataset_removes_dependent_rows_before_dataset() -> None:
    queries = Mock()
    queries.load_filtered_table.return_value = pd.DataFrame(
        [{"session_id": "session_a"}, {"session_id": "session_b"}]
    )
    serializer = DataSerializer(queries=queries)

    serializer.delete_dataset(7)

    queries.load_filtered_table.assert_called_once_with(
        INFERENCE_SESSIONS_TABLE,
        {"dataset_id": "7"},
    )
    assert queries.delete_table_rows.call_args_list == [
        call(INFERENCE_SESSION_STEPS_TABLE, {"session_id": "session_a"}),
        call(INFERENCE_SESSION_STEPS_TABLE, {"session_id": "session_b"}),
        call(INFERENCE_SESSIONS_TABLE, {"dataset_id": "7"}),
        call(DATASET_OUTCOMES_TABLE, {"dataset_id": "7"}),
        call(DATASETS_TABLE, {"dataset_id": "7"}),
    ]
