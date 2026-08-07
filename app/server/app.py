from __future__ import annotations

import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from server.common.constants import (
    FASTAPI_API_PREFIX,
    FASTAPI_ASSETS_ENDPOINT,
    FASTAPI_DESCRIPTION,
    FASTAPI_DOCS_ENDPOINT,
    FASTAPI_ROOT_ENDPOINT,
    FASTAPI_SPA_FALLBACK_ENDPOINT,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)
from server.common import path as shared_paths
from server.api.datasets import router as datasets_router
from server.api.inference import router as inference_router
from server.api.training import router as training_router
from server.api.upload import router as upload_router
from server.api.system import router as system_router
from server.configurations import get_server_settings
from server.domain.system import RootStatusResponse
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_sqlite_database_if_missing
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository
from server.repositories.serialization.data import DataSerializer
from server.services.checkpoints import CheckpointService
from server.services.datasets import DatasetService
from server.services.importer import DatasetImportService
from server.services.inference import InferenceService
from server.services.jobs import JobManager
from server.services.loader import TabularFileLoader
from server.services.startup_validation import run_startup_validations
from server.services.training import TrainingService

warnings.filterwarnings("ignore", category=FutureWarning)

###############################################################################
def is_api_docs_enabled() -> bool:
    value = os.getenv("ENABLE_API_DOCS", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}

###############################################################################
def _client_build_available() -> bool:
    return shared_paths.CLIENT_INDEX_FILE_PATH.is_file()

###############################################################################
def _resolve_client_file(full_path: str) -> Path | None:
    client_root = shared_paths.CLIENT_DIST_PATH.resolve()
    requested_path = (client_root / full_path).resolve()

    if not requested_path.is_relative_to(client_root):
        return None

    if requested_path.is_file():
        return requested_path

    return None

###############################################################################
def serve_client_root() -> FileResponse:
    return FileResponse(shared_paths.CLIENT_INDEX_FILE_PATH)

###############################################################################
def serve_client_path(full_path: str) -> FileResponse:
    client_file = _resolve_client_file(full_path)
    if client_file is not None:
        return FileResponse(client_file)
    return FileResponse(shared_paths.CLIENT_INDEX_FILE_PATH)

###############################################################################
def redirect_root_to_docs() -> RedirectResponse | RootStatusResponse:
    if is_api_docs_enabled():
        return RedirectResponse(FASTAPI_DOCS_ENDPOINT)
    return RootStatusResponse(status="ok")

###############################################################################
@asynccontextmanager
async def app_lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_server_settings()

    run_startup_validations(settings)

    if settings.database.embedded_database:
        initialize_sqlite_database_if_missing(settings.database)
        database = FAIRSDatabase(settings.database)
    else:
        database = FAIRSDatabase(settings.database)
        try:
            database.check_connection()
        except SQLAlchemyError as exc:
            raise RuntimeError(
                "Unable to connect to the configured PostgreSQL database. "
                "Run the launcher's database initialization command and verify the connection settings."
            ) from exc
    serializer = DataSerializer(
        datasets=DatasetRepository(database),
        inference=InferenceRepository(database),
    )
    job_manager = JobManager()
    checkpoint_service = CheckpointService()

    application.state.database = database
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
def include_api_routers(application: FastAPI) -> None:
    for router in (
        upload_router,
        training_router,
        datasets_router,
        inference_router,
        system_router,
    ):
        application.include_router(router, prefix=FASTAPI_API_PREFIX)

###############################################################################
def configure_client_routes(application: FastAPI) -> None:
    if _client_build_available():
        if shared_paths.CLIENT_ASSETS_PATH.is_dir():
            application.mount(
                FASTAPI_ASSETS_ENDPOINT,
                StaticFiles(directory=shared_paths.CLIENT_ASSETS_PATH),
                name="spa-assets",
            )

        application.add_api_route(
            FASTAPI_ROOT_ENDPOINT,
            serve_client_root,
            methods=["GET"],
            include_in_schema=False,
        )
        application.add_api_route(
            FASTAPI_SPA_FALLBACK_ENDPOINT,
            serve_client_path,
            methods=["GET"],
            include_in_schema=False,
        )
        return

    application.add_api_route(
        FASTAPI_ROOT_ENDPOINT,
        redirect_root_to_docs,
        methods=["GET"],
        include_in_schema=False,
        response_model=RootStatusResponse,
    )

###############################################################################
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
