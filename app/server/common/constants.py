from __future__ import annotations

# [FASTAPI]
###############################################################################
FASTAPI_ROOT_ENDPOINT = "/"
FASTAPI_DOCS_ENDPOINT = "/docs"
FASTAPI_API_PREFIX = "/api"
FASTAPI_ASSETS_ENDPOINT = "/assets"
FASTAPI_SPA_FALLBACK_ENDPOINT = "/{full_path:path}"
FASTAPI_TITLE = "FAIRS Roulette Backend"
FASTAPI_DESCRIPTION = "FastAPI backend"
FASTAPI_VERSION = "2.4.0"

# [ENDPOINS]
###############################################################################
BASE_URL = "/base/tags"

# [EXTERNAL DATA SOURCES]
###############################################################################
CONSTANT = 1.0

# [DATABASE TABLES]
###############################################################################
ROULETTE_OUTCOMES_TABLE = "roulette_outcomes"
DATASETS_TABLE = "datasets"
DATASET_OUTCOMES_TABLE = "dataset_outcomes"
INFERENCE_SESSIONS_TABLE = "inference_sessions"
INFERENCE_SESSION_STEPS_TABLE = "inference_session_steps"

# [DATABASE COLUMNS]
###############################################################################
ROULETTE_OUTCOMES_COLUMNS = [
    "outcome_id",
    "color",
    "color_code",
    "wheel_position",
]
DATASETS_COLUMNS = [
    "dataset_id",
    "dataset_name",
    "dataset_kind",
    "created_at",
]
DATASET_OUTCOMES_COLUMNS = [
    "id",
    "dataset_id",
    "sequence_index",
    "outcome_id",
]
DATASET_OUTCOMES_WRITE_COLUMNS = [
    "dataset_id",
    "sequence_index",
    "outcome_id",
]
INFERENCE_SESSIONS_COLUMNS = [
    "session_id",
    "dataset_id",
    "checkpoint_name",
    "initial_capital",
    "started_at",
    "ended_at",
]
INFERENCE_SESSION_STEPS_COLUMNS = [
    "id",
    "session_id",
    "step_number",
    "bet_amount",
    "predicted_action",
    "predicted_confidence",
    "observed_outcome_id",
    "reward",
    "capital_after",
    "recorded_at",
]

# [ROULETTE WHEEL CONSTANTS]
###############################################################################
ROULETTE_POSITION_MAP: dict[int, int] = {
    0: 0, 32: 1, 15: 2, 19: 3, 4: 4, 21: 5, 2: 6, 25: 7, 17: 8, 34: 9,
    6: 10, 27: 11, 13: 12, 36: 13, 11: 14, 30: 15, 8: 16, 23: 17, 10: 18,
    5: 19, 24: 20, 16: 21, 33: 22, 1: 23, 20: 24, 14: 25, 31: 26, 9: 27,
    22: 28, 18: 29, 29: 30, 7: 31, 28: 32, 12: 33, 35: 34, 3: 35, 26: 36,
}

ROULETTE_COLOR_MAP: dict[str, list[int]] = {
    "black": [
        15, 4, 2, 17, 6, 13, 11, 8, 10, 24, 33, 20, 31, 22, 29, 28, 35, 26,
    ],
    "red": [
        32, 19, 21, 25, 34, 27, 36, 30, 23, 5, 16, 1, 14, 9, 18, 7, 12, 3,
    ],
    "green": [0],
}

ROULETTE_COLOR_CODE: dict[str, int] = {"green": 0, "black": 1, "red": 2}

# [TRAINING CONSTANTS]
###############################################################################
NUMBERS: int = 37
STATES: int = 47
PAD_VALUE: int = -1
