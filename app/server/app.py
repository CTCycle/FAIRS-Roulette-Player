from __future__ import annotations

import os
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.common.constants import (
    FASTAPI_DESCRIPTION,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)
from server.repositories.database.initializer import (
    initialize_sqlite_on_startup_if_missing,
)
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.queries.data import DataRepositoryQueries
from server.repositories.serialization.data import DataSerializer
from server.api.datasets import router as datasets_router
from server.api.inference import router as inference_router
from server.api.training import router as training_router
from server.api.upload import router as upload_router
from server.services.checkpoints import CheckpointService
from server.services.datasets import DatasetService
from server.services.importer import DatasetImportService
from server.services.inference import InferenceService
from server.services.jobs import create_job_manager
from server.services.loader import TabularFileLoader
from server.services.training import TrainingService

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
def serve_spa_root() -> FileResponse:
    return FileResponse(os.path.join(get_client_dist_path(), "index.html"))


# -----------------------------------------------------------------------------
def serve_spa_entrypoint(full_path: str) -> FileResponse:
    client_dist_path = get_client_dist_path()
    requested_path = os.path.join(client_dist_path, full_path)
    if os.path.isfile(requested_path):
        return FileResponse(requested_path)
    return FileResponse(os.path.join(client_dist_path, "index.html"))


# -----------------------------------------------------------------------------
def redirect_to_docs() -> RedirectResponse | dict[str, str]:
    if is_api_docs_enabled():
        return RedirectResponse(url="/docs")
    return {"status": "ok"}


# -----------------------------------------------------------------------------
def include_api_routers(application: FastAPI) -> None:
    for router in (
        upload_router,
        training_router,
        datasets_router,
        inference_router,
    ):
        application.include_router(router, prefix="/api")


# -----------------------------------------------------------------------------
def configure_client_routes(application: FastAPI) -> None:
    if packaged_client_available():
        client_dist_path = get_client_dist_path()
        assets_path = os.path.join(client_dist_path, "assets")

        if os.path.isdir(assets_path):
            application.mount(
                "/assets",
                StaticFiles(directory=assets_path),
                name="spa-assets",
            )

        application.add_api_route(
            "/",
            serve_spa_root,
            methods=["GET"],
            include_in_schema=False,
        )
        application.add_api_route(
            "/{full_path:path}",
            serve_spa_entrypoint,
            methods=["GET"],
            include_in_schema=False,
        )
        return

    application.add_api_route(
        "/",
        redirect_to_docs,
        methods=["GET"],
        response_model=None,
    )


# -----------------------------------------------------------------------------
def create_app() -> FastAPI:
    enable_api_docs = is_api_docs_enabled()
    application = FastAPI(
        title=FASTAPI_TITLE,
        version=FASTAPI_VERSION,
        description=FASTAPI_DESCRIPTION,
        docs_url="/docs" if enable_api_docs else None,
        redoc_url="/redoc" if enable_api_docs else None,
        openapi_url="/openapi.json" if enable_api_docs else None,
        lifespan=app_lifespan,
    )
    include_api_routers(application)
    configure_client_routes(application)
    return application


###############################################################################
app = create_app()
