from __future__ import annotations

from FAIRS.server.routes.endpoint import router as base_router
from FAIRS.server.routes.upload import router as upload_router

__all__ = ["base_router", "upload_router"]
