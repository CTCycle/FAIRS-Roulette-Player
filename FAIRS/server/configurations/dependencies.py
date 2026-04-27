from __future__ import annotations

from fastapi import Request

from FAIRS.server.repositories.serialization.data import DataSerializer
from FAIRS.server.services.datasets import DatasetService
from FAIRS.server.services.inference import InferenceService
from FAIRS.server.services.training import TrainingService


###############################################################################
def get_data_serializer(request: Request) -> DataSerializer:
    return request.app.state.data_serializer


###############################################################################
def get_dataset_service(request: Request) -> DatasetService:
    return request.app.state.dataset_service


###############################################################################
def get_training_service(request: Request) -> TrainingService:
    return request.app.state.training_service


###############################################################################
def get_inference_service(request: Request) -> InferenceService:
    return request.app.state.inference_service
