from __future__ import annotations

from FAIRS.server.api.upload import router as upload_router
from FAIRS.server.api.training import router as training_router
from FAIRS.server.api.database import router as database_router

__all__ = ["upload_router", "training_router", "database_router"]
