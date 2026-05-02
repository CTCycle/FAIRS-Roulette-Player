from __future__ import annotations

from server.api.upload import router as upload_router
from server.api.training import router as training_router
from server.api.datasets import router as datasets_router
from server.api.inference import router as inference_router

__all__ = [
    "upload_router",
    "training_router",
    "datasets_router",
    "inference_router",
]
