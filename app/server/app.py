from __future__ import annotations

# Runtime bootstrap must run before importing Keras-backed application modules.
# ruff: noqa: E402
from server.bootstrap import bootstrap_runtime

bootstrap_runtime()

import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.common.constants import (
    FASTAPI_API_PREFIX,
    FASTAPI_ASSETS_ENDPOINT,
    FASTAPI_DESCRIPTION,
    FASTAPI_DOCS_ENDPOINT,
    FASTAPI_ROOT_ENDPOINT,
    FASTAPI_SPA_FALLBACK_ENDPOINT,
    FASTAPI_TITLE,
)
from server.common import path as shared_paths
from server.common.version import get_application_version
from server.api.datasets import router as datasets_router
from server.api.inference import router as inference_router
from server.api.training import router as training_router
from server.api.upload import router as upload_router
from server.api.system import router as system_router
from server.configurations import get_server_settings
from server.contracts.system import RootStatusResponse
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.initializer import initialize_database
from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository
from server.services.checkpoints import CheckpointService
from server.services.datasets import DatasetService
from server.services.importer import DatasetImportService
from server.services.inference import InferenceService
from server.services.loader import TabularFileLoader
from server.services.startup_validation import run_startup_validations
from server.services.training import TrainingService
from server.services.training_run import TrainingRunManager

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
    initialize_database(settings.database)
    database = FAIRSDatabase(settings.database)
    try:
        dataset_repository = DatasetRepository(database)
        inference_repository = InferenceRepository(database)
        training_run_manager = TrainingRunManager()
        checkpoint_service = CheckpointService()

        application.state.database = database
        application.state.dataset_repository = dataset_repository
        application.state.inference_repository = inference_repository
        application.state.dataset_service = DatasetService(
            dataset_repository=dataset_repository,
            importer=DatasetImportService(dataset_repository=dataset_repository),
            loader=TabularFileLoader(),
            checkpoint_service=checkpoint_service,
        )
        application.state.training_run_manager = training_run_manager
        application.state.training_service = TrainingService(
            training_run_manager=training_run_manager,
            checkpoint_service=checkpoint_service,
            database_settings=settings.database,
            database_path=shared_paths.DATABASE_PATH,
            polling_interval_seconds=settings.jobs.polling_interval,
            jit_compile=settings.device.jit_compile,
            jit_backend=settings.device.jit_backend,
        )
        application.state.inference_service = InferenceService(
            dataset_repository=dataset_repository,
            inference_repository=inference_repository,
            checkpoint_service=checkpoint_service,
        )

        yield
    finally:
        database.dispose()


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
        version=get_application_version(),
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
