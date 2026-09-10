// Generated from the canonical FastAPI/Pydantic contract.
// Do not edit manually. Run app/scripts/generate_frontend_contracts.py.

export type Body_upload_api_data_upload_post = {
    "file": string;
};

export type DatasetDeleteResponse = {
    "dataset_id": number;
    "status": string;
};

export type DatasetListResponse = {
    "datasets": Array<DatasetRecord>;
};

export type DatasetRecord = {
    "created_at"?: string | null;
    "dataset_id": number;
    "dataset_kind": string;
    "dataset_name": string;
};

export type DatasetSummaryRecord = {
    "created_at"?: string | null;
    "dataset_id": number;
    "dataset_kind": string;
    "dataset_name": string;
    "row_count": number;
};

export type DatasetSummaryResponse = {
    "datasets": Array<DatasetSummaryRecord>;
};

export type HTTPValidationError = {
    "detail"?: Array<ValidationError>;
};

export type HealthResponse = {
    "application": string;
    "status": string;
    "version": string;
};

export type InferenceBetUpdateRequest = {
    "bet_amount": number;
};

export type InferenceBetUpdateResponse = {
    "bet_amount": number;
    "session_id": string;
};

export type InferenceContextClearResponse = {
    "status": string;
};

export type InferenceNextResponse = {
    "prediction": PredictionResponse;
    "session_id": string;
};

export type InferenceRowsClearResponse = {
    "session_id": string;
    "status": string;
};

export type InferenceSessionStatusResponse = {
    "checkpoint": string;
    "current_bet": number;
    "current_capital": number;
    "dataset_id": number;
    "initial_capital": number;
    "last_prediction"?: PredictionResponse | null;
    "prediction_pending": boolean;
    "session_id": string;
    "step_count": number;
    "steps": Array<InferenceSessionStepResponse>;
};

export type InferenceSessionStepResponse = {
    "bet_amount": number;
    "capital_after": number;
    "observed_outcome_id": number | null;
    "predicted_action": number;
    "predicted_action_desc": string;
    "predicted_relative_preference": number | null;
    "reward": number | null;
    "step": number;
};

export type InferenceShutdownResponse = {
    "session_id": string;
    "status": string;
};

export type InferenceStartRequest = {
    "checkpoint": string;
    "dataset_id": number;
    "game_bet"?: number;
    "game_capital"?: number;
};

export type InferenceStartResponse = {
    "checkpoint": string;
    "current_capital": number;
    "game_bet": number;
    "game_capital": number;
    "prediction": PredictionResponse;
    "session_id": string;
};

export type InferenceStepRequest = {
    "extraction": number;
};

export type InferenceStepResponse = {
    "capital_after": number;
    "predicted_action": number;
    "predicted_action_desc": string;
    "real_extraction": number;
    "reward": number;
    "session_id": string;
    "step": number;
};

export type JobCancelResponse = {
    "job_id": string;
    "message": string;
    "success": boolean;
};

export type JobStartResponse = {
    "job_id": string;
    "job_type": string;
    "message": string;
    "poll_interval"?: number;
    "status": string;
};

export type JobStatusResponse = {
    "error"?: string | null;
    "job_id": string;
    "job_type": string;
    "poll_interval"?: number | null;
    "progress": number;
    "result"?: Record<string, unknown> | null;
    "status": string;
};

export type PredictionResponse = {
    "action": number;
    "bet_strategy_id"?: number | null;
    "bet_strategy_name"?: string | null;
    "current_bet_amount"?: number | null;
    "description": string;
    "relative_preference"?: number | null;
    "suggested_bet_amount"?: number | null;
};

export type ResumeConfig = {
    "additional_episodes"?: number;
    "checkpoint": string;
};

export type TrainingCheckpointDeleteResponse = {
    "message": string;
    "status": string;
};

export type TrainingCheckpointListResponse = Array<string>;

export type TrainingCheckpointMetadataResponse = {
    "checkpoint": string;
    "summary": TrainingCheckpointSummary;
};

export type TrainingCheckpointSummary = {
    "batch_size": number;
    "bet_amount": number;
    "dataset_id": number | null;
    "discount_rate": number;
    "embedding_dimensions": number;
    "episodes": number;
    "exploration_rate": number;
    "exploration_rate_decay": number;
    "final_loss": number | null;
    "final_rmse": number | null;
    "final_val_loss": number | null;
    "final_val_rmse": number | null;
    "initial_capital": number;
    "learning_rate": number;
    "model_update_frequency": number;
    "perceptive_field_size": number;
    "qnet_neurons": number;
    "sample_size": number;
    "seed": number;
};

export type TrainingConfig = {
    "batch_size"?: number;
    "bet_amount"?: number;
    "bet_enforce_capital"?: boolean;
    "bet_max"?: number | null;
    "bet_strategy_fixed_id"?: number;
    "bet_strategy_model_enabled"?: boolean;
    "bet_unit"?: number | null;
    "checkpoint_name"?: string | null;
    "dataset_id"?: number | null;
    "device_id"?: number;
    "discount_rate"?: number;
    "dynamic_betting_enabled"?: boolean;
    "embedding_dimensions"?: number;
    "episodes"?: number;
    "exploration_rate"?: number;
    "exploration_rate_decay"?: number;
    "initial_capital"?: number;
    "learning_rate"?: number;
    "max_memory_size"?: number;
    "max_steps_episode"?: number;
    "minimum_exploration_rate"?: number;
    "model_update_frequency"?: number;
    "num_generated_samples"?: number;
    "perceptive_field_size"?: number;
    "qnet_neurons"?: number;
    "replay_buffer_size"?: number;
    "sample_size"?: number;
    "seed"?: number;
    "strategy_hold_steps"?: number;
    "training_seed"?: number;
    "use_data_generator"?: boolean;
    "use_device_gpu"?: boolean;
    "use_mixed_precision"?: boolean;
    "validation_size"?: number;
};

export type TrainingStatusResponse = {
    "history": Array<Record<string, unknown>>;
    "is_training": boolean;
    "job_id": string | null;
    "latest_env": Record<string, unknown>;
    "latest_stats": Record<string, unknown>;
    "poll_interval": number;
};

export type TrainingStopResponse = {
    "message": string;
    "status": string;
};

export type UploadResponse = {
    "columns": Array<string>;
    "dataset_id": number | null;
    "dataset_kind": string | null;
    "dataset_name": string | null;
    "filename": string;
    "rows_imported": number;
};

export type ValidationError = {
    "loc": Array<string | number>;
    "msg": string;
    "type": string;
};

export const INFERENCE_START_REQUEST_DEFAULTS = {
    "game_bet": 1,
    "game_capital": 100,
} as const satisfies Partial<InferenceStartRequest>;

export const RESUME_CONFIG_DEFAULTS = {
    "additional_episodes": 10,
} as const satisfies Partial<ResumeConfig>;

export const TRAINING_CONFIG_DEFAULTS = {
    "batch_size": 32,
    "bet_amount": 10,
    "bet_enforce_capital": true,
    "bet_max": null,
    "bet_strategy_fixed_id": 0,
    "bet_strategy_model_enabled": false,
    "bet_unit": null,
    "checkpoint_name": null,
    "dataset_id": null,
    "device_id": 0,
    "discount_rate": 0.5,
    "dynamic_betting_enabled": false,
    "embedding_dimensions": 200,
    "episodes": 10,
    "exploration_rate": 0.75,
    "exploration_rate_decay": 0.995,
    "initial_capital": 1000,
    "learning_rate": 0.0001,
    "max_memory_size": 10000,
    "max_steps_episode": 2000,
    "minimum_exploration_rate": 0.1,
    "model_update_frequency": 10,
    "num_generated_samples": 10000,
    "perceptive_field_size": 64,
    "qnet_neurons": 64,
    "replay_buffer_size": 1000,
    "sample_size": 1.0,
    "seed": 42,
    "strategy_hold_steps": 1,
    "training_seed": 42,
    "use_data_generator": false,
    "use_device_gpu": false,
    "use_mixed_precision": false,
    "validation_size": 0.2,
} as const satisfies Partial<TrainingConfig>;
