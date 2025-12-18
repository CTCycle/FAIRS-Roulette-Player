from __future__ import annotations

from pydantic import BaseModel, Field


###############################################################################
class TrainingConfig(BaseModel):
    """Configuration for starting a new training session."""
    
    # Agent parameters
    perceptive_field_size: int = Field(64, ge=1, le=1024)
    QNet_neurons: int = Field(64, ge=1, le=10000)
    embedding_dimensions: int = Field(200, ge=8)
    exploration_rate: float = Field(0.75, ge=0.0, le=1.0)
    exploration_rate_decay: float = Field(0.995, ge=0.0, le=1.0)
    minimum_exploration_rate: float = Field(0.10, ge=0.0, le=1.0)
    discount_rate: float = Field(0.50, ge=0.0, le=1.0)
    model_update_frequency: int = Field(10, ge=1)
    
    # Environment parameters
    bet_amount: int = Field(10, ge=1)
    initial_capital: int = Field(1000, ge=1)
    render_environment: bool = False
    render_update_frequency: int = Field(20, ge=1)
    
    # Dataset parameters
    use_data_generator: bool = False
    num_generated_samples: int = Field(10000, ge=100)
    sample_size: float = Field(1.0, gt=0.0, le=1.0)
    validation_size: float = Field(0.2, ge=0.0, lt=1.0)
    seed: int = 42
    shuffle_dataset: bool = True
    shuffle_size: int = Field(256, ge=1)
    
    # Session parameters
    episodes: int = Field(10, ge=1)
    max_steps_episode: int = Field(2000, ge=100)
    batch_size: int = Field(32, ge=1)
    learning_rate: float = Field(0.0001, gt=0.0)
    max_memory_size: int = Field(10000, ge=100)
    replay_buffer_size: int = Field(1000, ge=100)
    training_seed: int = 42
    
    # Device parameters
    use_device_GPU: bool = False
    device_ID: int = Field(0, ge=0)
    
    # Checkpointing
    save_checkpoints: bool = False
    checkpoints_frequency: int = Field(1, ge=1)
    use_tensorboard: bool = False


###############################################################################
class ResumeConfig(BaseModel):
    """Configuration for resuming a training session from a checkpoint."""
    
    checkpoint: str
    additional_episodes: int = Field(10, ge=1)


###############################################################################
class TrainingRuntimeSettings(BaseModel):
    render_environment: bool = False
    render_update_frequency: int = Field(20, ge=1)
