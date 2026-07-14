from __future__ import annotations

import os

from fastapi import APIRouter

from server.common.constants import FASTAPI_VERSION

router = APIRouter(tags=["system"])

###############################################################################
@router.get("/health")
def health() -> dict[str, str]:
    mode = "desktop" if os.getenv("FAIRS_TAURI_MODE", "").lower() == "true" else "development"
    return {
        "status": "ok",
        "application": "FAIRS",
        "version": FASTAPI_VERSION,
        "mode": mode,
    }
