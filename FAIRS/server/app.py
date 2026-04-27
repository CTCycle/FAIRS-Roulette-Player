from __future__ import annotations

import os
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from FAIRS.server.common.constants import (
    FASTAPI_DESCRIPTION,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)
from FAIRS.server.repositories.database.initializer import (
    initialize_sqlite_on_startup_if_missing,
)
from FAIRS.server.repositories.database.backend import FAIRSDatabase
from FAIRS.server.repositories.queries.data import DataRepositoryQueries
from FAIRS.server.repositories.serialization.data import DataSerializer
from FAIRS.server.api.database import router as database_router
from FAIRS.server.api.inference import router as inference_router
from FAIRS.server.api.training import router as training_router
from FAIRS.server.api.upload import router as upload_router
from FAIRS.server.services.checkpoints import CheckpointService
from FAIRS.server.services.datasets import DatasetService
from FAIRS.server.services.importer import DatasetImportService
from FAIRS.server.services.inference import InferenceService
from FAIRS.server.services.jobs import create_job_manager
from FAIRS.server.services.loader import TabularFileLoader
from FAIRS.server.services.training import TrainingService

warnings.filterwarnings("ignore", category=FutureWarning)


###############################################################################
def is_api_docs_enabled() -> bool:
    value = os.getenv("ENABLE_API_DOCS", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


# -----------------------------------------------------------------------------
def tauri_mode_enabled() -> bool:
    value = os.getenv("FAIRS_TAURI_MODE", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


# -----------------------------------------------------------------------------
def get_client_dist_path() -> str:
    project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(project_path, "client", "dist")


# -----------------------------------------------------------------------------
def packaged_client_available() -> bool:
    return tauri_mode_enabled() and os.path.isdir(get_client_dist_path())


ENABLE_API_DOCS = is_api_docs_enabled()


###############################################################################
@asynccontextmanager
async def app_lifespan(application: FastAPI):
    initialize_sqlite_on_startup_if_missing()

    database = FAIRSDatabase()
    queries = DataRepositoryQueries(database)
    serializer = DataSerializer(queries)
    job_manager = create_job_manager()
    checkpoint_service = CheckpointService()

    application.state.database = database
    application.state.data_queries = queries
    application.state.data_serializer = serializer
    application.state.dataset_service = DatasetService(
        serializer=serializer,
        importer=DatasetImportService(serializer=serializer),
        loader=TabularFileLoader(),
    )
    application.state.job_manager = job_manager
    application.state.training_service = TrainingService(
        job_manager=job_manager,
        checkpoint_service=checkpoint_service,
    )
    application.state.inference_service = InferenceService(
        serializer=serializer,
        checkpoint_service=checkpoint_service,
    )

    yield

###############################################################################
app = FastAPI(
    title=FASTAPI_TITLE,
    version=FASTAPI_VERSION,
    description=FASTAPI_DESCRIPTION,
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
    lifespan=app_lifespan,
)

routers = [
    upload_router,
    training_router,
    database_router,
    inference_router,
]

for router in routers:
    app.include_router(router, prefix="/api")

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
