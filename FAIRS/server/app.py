from __future__ import annotations

import os
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from FAIRS.server.common.constants import (
    FASTAPI_DESCRIPTION,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)
from FAIRS.server.configurations.server import app_settings
from FAIRS.server.repositories.database.initializer import (
    initialize_sqlite_on_startup_if_missing,
)
from FAIRS.server.api.database import router as database_router
from FAIRS.server.api.inference import router as inference_router
from FAIRS.server.api.training import router as training_router
from FAIRS.server.api.upload import router as upload_router


###############################################################################
def is_api_docs_enabled() -> bool:
    return bool(app_settings.enable_api_docs)


# -----------------------------------------------------------------------------
def is_direct_api_routes_enabled() -> bool:
    return bool(app_settings.fairs_allow_direct_api_routes)


# -----------------------------------------------------------------------------
def tauri_mode_enabled() -> bool:
    return bool(app_settings.fairs_tauri_mode)


# -----------------------------------------------------------------------------
def get_client_dist_path() -> str:
    project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(project_path, "client", "dist")


# -----------------------------------------------------------------------------
def packaged_client_available() -> bool:
    return tauri_mode_enabled() and os.path.isdir(get_client_dist_path())


ENABLE_API_DOCS = is_api_docs_enabled()
ALLOW_DIRECT_API_ROUTES = is_direct_api_routes_enabled()

###############################################################################
app = FastAPI(
    title=FASTAPI_TITLE,
    version=FASTAPI_VERSION,
    description=FASTAPI_DESCRIPTION,
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)

routers = [
    upload_router,
    training_router,
    database_router,
    inference_router,
]

for router in routers:
    app.include_router(
        router,
        prefix="/api",
        include_in_schema=not ALLOW_DIRECT_API_ROUTES,
    )
    if ALLOW_DIRECT_API_ROUTES:
        app.include_router(router)


@app.on_event("startup")
def initialize_embedded_database() -> None:
    initialize_sqlite_on_startup_if_missing()


if packaged_client_available():
    client_dist_path = get_client_dist_path()
    assets_path = os.path.join(client_dist_path, "assets")

    if os.path.isdir(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="spa-assets")

    @app.get("/", include_in_schema=False)
    def serve_spa_root() -> FileResponse:
        return FileResponse(os.path.join(client_dist_path, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa_entrypoint(full_path: str) -> FileResponse:
        requested_path = os.path.join(client_dist_path, full_path)
        if os.path.isfile(requested_path):
            return FileResponse(requested_path)
        return FileResponse(os.path.join(client_dist_path, "index.html"))

else:

    @app.get("/", response_model=None)
    def redirect_to_docs() -> RedirectResponse | dict[str, str]:
        if ENABLE_API_DOCS:
            return RedirectResponse(url="/docs")
        return {"status": "ok"}
