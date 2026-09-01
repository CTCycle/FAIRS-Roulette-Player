from __future__ import annotations

from typing import Any

from fastapi import Request


###############################################################################
def get_dataset_service(request: Request) -> Any:
    return request.app.state.dataset_service


###############################################################################
def get_training_service(request: Request) -> Any:
    return request.app.state.training_service


###############################################################################
def get_inference_service(request: Request) -> Any:
    return request.app.state.inference_service
