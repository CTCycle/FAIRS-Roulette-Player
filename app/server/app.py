from __future__ import annotations

# Runtime bootstrap occurs inside the ASGI lifespan so importing the app does not
# create files, configure handlers, or initialize application resources.
from server.bootstrap import bootstrap_runtime

import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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
from server.common.utils.logger import close_application_logging, logger
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
from server.services.startup_validation import run_startup_validations

# These names are deliberately unresolved until the lifespan has bootstrapped
# the runtime.  Keeping injectable placeholders preserves the test seam
# without importing Keras-backed services during module import.
DatasetRepository: Any = None
InferenceRepository: Any = None
CheckpointService: Any = None
DatasetService: Any = None
DatasetImportService: Any = None
TabularFileLoader: Any = None
InferenceService: Any = None
TrainingService: Any = None
TrainingRunManager: Any = None


###############################################################################
def is_api_docs_enabled() -> bool:
    value = os.getenv("ENABLE_API_DOCS", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


###############################################################################
def ensure_single_process_runtime() -> None:
    """Reject process counts that cannot safely share in-memory state."""
    for variable_name in ("WEB_CONCURRENCY", "UVICORN_WORKERS", "FAIRS_WORKERS"):
        raw_value = os.getenv(variable_name)
        if raw_value is None or not raw_value.strip():
            continue
        try:
            worker_count = int(raw_value)
        except ValueError as exc:
            raise RuntimeError(
                f"{variable_name} must be an integer; this application requires one worker."
            ) from exc
        if worker_count != 1:
            raise RuntimeError(
                "FAIRS Roulette Player requires exactly one backend worker because "
                "training jobs and inference models are process-local."
            )


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
    application.state.lifecycle = "starting"
    previous_warning_filters = list(warnings.filters)
    database = None
    training_run_manager = None
    training_service = None
    inference_service = None
    try:
        bootstrap_runtime()
        warnings.filterwarnings("ignore", category=FutureWarning)
        settings = get_server_settings()
        ensure_single_process_runtime()
        application.version = get_application_version()

        run_startup_validations(settings)
        initialize_database(settings.database)
        database = FAIRSDatabase(settings.database)

        # Import ML-backed services only after the runtime bootstrap has
        # selected the configured Keras backend.
        runtime_imports = {
            "DatasetRepository": ("server.repositories.datasets", "DatasetRepository"),
            "InferenceRepository": ("server.repositories.inference", "InferenceRepository"),
            "CheckpointService": ("server.services.checkpoints", "CheckpointService"),
            "DatasetService": ("server.services.datasets", "DatasetService"),
            "DatasetImportService": ("server.services.importer", "DatasetImportService"),
            "TabularFileLoader": ("server.services.loader", "TabularFileLoader"),
            "InferenceService": ("server.services.inference", "InferenceService"),
            "TrainingService": ("server.services.training", "TrainingService"),
            "TrainingRunManager": ("server.services.training_run", "TrainingRunManager"),
        }
        resolved_imports: dict[str, Any] = {}
        for name, (module_name, attribute_name) in runtime_imports.items():
            injected = globals()[name]
            if injected is not None:
                resolved_imports[name] = injected
                continue
            module = __import__(module_name, fromlist=[attribute_name])
            resolved_imports[name] = getattr(module, attribute_name)

        DatasetRepository = resolved_imports["DatasetRepository"]
        InferenceRepository = resolved_imports["InferenceRepository"]
        CheckpointService = resolved_imports["CheckpointService"]
        DatasetService = resolved_imports["DatasetService"]
        DatasetImportService = resolved_imports["DatasetImportService"]
        TabularFileLoader = resolved_imports["TabularFileLoader"]
        InferenceService = resolved_imports["InferenceService"]
        TrainingService = resolved_imports["TrainingService"]
        TrainingRunManager = resolved_imports["TrainingRunManager"]

        dataset_repository = DatasetRepository(database)
        inference_repository = InferenceRepository(database)
        training_run_manager = TrainingRunManager()
        checkpoint_service = CheckpointService()
        cleanup_workspaces = getattr(checkpoint_service, "cleanup_incomplete_workspaces", None)
        if callable(cleanup_workspaces):
            cleanup_workspaces()

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
        training_service = TrainingService(
            training_run_manager=training_run_manager,
            checkpoint_service=checkpoint_service,
            database_settings=settings.database,
            database_path=shared_paths.DATABASE_PATH,
            polling_interval_seconds=settings.jobs.polling_interval,
            jit_compile=settings.device.jit_compile,
            jit_backend=settings.device.jit_backend,
        )
        application.state.training_service = training_service
        inference_service = InferenceService(
            dataset_repository=dataset_repository,
            inference_repository=inference_repository,
            checkpoint_service=checkpoint_service,
        )
        application.state.inference_service = inference_service
        if not getattr(application.state, "client_routes_configured", False):
            configure_client_routes(application)
            application.state.client_routes_configured = True
        application.state.lifecycle = "ready"

        yield
    finally:
        application.state.lifecycle = "stopping"
        if inference_service is not None:
            try:
                shutdown = getattr(inference_service, "shutdown", None)
                if callable(shutdown):
                    shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Inference service shutdown failed")

        if training_service is not None:
            try:
                shutdown = getattr(training_service, "shutdown", None)
                if callable(shutdown):
                    shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Training service shutdown failed")
        if training_run_manager is not None:
            try:
                shutdown = getattr(training_run_manager, "shutdown", None)
                if callable(shutdown):
                    shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Training manager shutdown failed")

        if database is not None:
            try:
                database.dispose()
            except Exception:  # noqa: BLE001
                logger.exception("Database shutdown failed")

        application.state.lifecycle = "stopped"
        warnings.filters[:] = previous_warning_filters
        try:
            close_application_logging()
        except Exception:  # noqa: BLE001
            logger.exception("Application logging shutdown failed")


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
        version="0.0.0",
        description=FASTAPI_DESCRIPTION,
        docs_url="/docs" if enable_api_docs else None,
        redoc_url="/redoc" if enable_api_docs else None,
        openapi_url="/openapi.json" if enable_api_docs else None,
        lifespan=app_lifespan,
    )
    include_api_routers(application)
    return application


###############################################################################
app = create_app()
