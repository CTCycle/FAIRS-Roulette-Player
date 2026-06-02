from __future__ import annotations

import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.common.constants import (
    CLIENT_ASSETS_PATH,
    CLIENT_DIST_PATH,
    CLIENT_INDEX_FILE_PATH,
    FASTAPI_API_PREFIX,
    FASTAPI_ASSETS_ENDPOINT,
    FASTAPI_DESCRIPTION,
    FASTAPI_DOCS_ENDPOINT,
    FASTAPI_ROOT_ENDPOINT,
    FASTAPI_SPA_FALLBACK_ENDPOINT,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)
from server.api.datasets import router as datasets_router
from server.api.inference import router as inference_router
from server.api.training import router as training_router
from server.api.upload import router as upload_router
from server.configurations import get_server_settings
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.queries.data import DataRepositoryQueries
from server.repositories.serialization.data import DataSerializer
from server.services.checkpoints import CheckpointService
from server.services.datasets import DatasetService
from server.services.importer import DatasetImportService
from server.services.inference import InferenceService
from server.services.jobs import create_job_manager
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
    return os.path.isfile(CLIENT_INDEX_FILE_PATH)


###############################################################################
def _resolve_client_file(full_path: str) -> Path | None:
    client_root = Path(CLIENT_DIST_PATH).resolve()
    requested_path = (client_root / full_path).resolve()

    if not requested_path.is_relative_to(client_root):
        return None

    if requested_path.is_file():
        return requested_path

    return None


###############################################################################
def serve_client_root() -> FileResponse:
    return FileResponse(CLIENT_INDEX_FILE_PATH)


###############################################################################
def serve_client_path(full_path: str) -> FileResponse:
    client_file = _resolve_client_file(full_path)
    if client_file is not None:
        return FileResponse(client_file)
    return FileResponse(CLIENT_INDEX_FILE_PATH)


###############################################################################
def redirect_root_to_docs() -> RedirectResponse | dict[str, str]:
    if is_api_docs_enabled():
        return RedirectResponse(FASTAPI_DOCS_ENDPOINT)
    return {"status": "ok"}


@asynccontextmanager
async def app_lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_server_settings()

    initialize_database(settings.database)
    run_startup_validations(settings)

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
def include_api_routers(application: FastAPI) -> None:
    for router in (
        upload_router,
        training_router,
        datasets_router,
        inference_router,
    ):
        application.include_router(router, prefix=FASTAPI_API_PREFIX)


def configure_client_routes(application: FastAPI) -> None:
    if _client_build_available():
        if os.path.isdir(CLIENT_ASSETS_PATH):
            application.mount(
                FASTAPI_ASSETS_ENDPOINT,
                StaticFiles(directory=CLIENT_ASSETS_PATH),
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
