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

# [TRAINING CONSTANTS]
###############################################################################
NUMBERS: int = 37
STATES: int = 47
PAD_VALUE: int = -1
