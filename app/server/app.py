# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

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

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
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
from server.api.database_settings import router as database_settings_router
from server.api.inference import router as inference_router
from server.api.settings import router as settings_router
from server.api.training import router as training_router
from server.api.upload import router as upload_router
from server.api.system import router as system_router
from server.configurations.database_config import (
    DatabaseConfigurationStore,
    LoadedDatabaseConfiguration,
)
from server.contracts.configuration import JsonServerSettings
from server.contracts.system import RootStatusResponse
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.runtime import (
    DatabaseSwitchConflict,
    DatabaseUnavailableError,
    RuntimeDatabaseManager,
)
from server.repositories.database.initializer import initialize_database
from server.repositories.application_settings import ApplicationSettingsRepository
from server.services.startup_validation import run_startup_validations
from server.services.settings import SettingsService
from server.services.database_configuration import DatabaseConfigurationService

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
def _activate_runtime_services(
    application: FastAPI,
    database_configuration: LoadedDatabaseConfiguration | None,
    application_settings: Any,
) -> None:
    """Publish service settings only after a database target is ready."""
    if database_configuration is None or application_settings is None:
        for service_name in (
            "dataset_repository",
            "inference_repository",
            "dataset_service",
            "training_run_manager",
            "training_service",
            "settings_service",
            "inference_service",
        ):
            setattr(application.state, service_name, None)
        return

    settings = application_settings.to_server_settings(database_configuration.settings)
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
    resolved: dict[str, Any] = {}
    for name, (module_name, attribute_name) in runtime_imports.items():
        injected = globals()[name]
        if injected is not None:
            resolved[name] = injected
        else:
            module = __import__(module_name, fromlist=[attribute_name])
            resolved[name] = getattr(module, attribute_name)

    runtime_database = application.state.runtime_database
    application.state.database = runtime_database
    dataset_repository = application.state.dataset_repository
    inference_repository = application.state.inference_repository
    training_run_manager = application.state.training_run_manager
    checkpoint_service = application.state.checkpoint_service
    training_service = application.state.training_service
    inference_service = application.state.inference_service

    if dataset_repository is None:
        dataset_repository = resolved["DatasetRepository"](runtime_database)
    application.state.dataset_repository = dataset_repository
    if inference_repository is None:
        inference_repository = resolved["InferenceRepository"](runtime_database)
    application.state.inference_repository = inference_repository
    if training_run_manager is None:
        training_run_manager = resolved["TrainingRunManager"]()
    application.state.training_run_manager = training_run_manager
    if checkpoint_service is None:
        checkpoint_service = resolved["CheckpointService"]()
        application.state.checkpoint_service = checkpoint_service
        checkpoint_service.cleanup_incomplete_workspaces()

    if application.state.dataset_service is None:
        dataset_service = resolved["DatasetService"](
            dataset_repository=dataset_repository,
            importer=resolved["DatasetImportService"](dataset_repository=dataset_repository),
            loader=resolved["TabularFileLoader"](),
            checkpoint_service=checkpoint_service,
        )
    else:
        dataset_service = application.state.dataset_service
    application.state.dataset_service = dataset_service

    if training_service is None:
        training_service = resolved["TrainingService"](
            training_run_manager=training_run_manager,
            checkpoint_service=checkpoint_service,
            dataset_repository=dataset_repository,
        )
        application.state.training_service = training_service
    training_service.apply_runtime_settings(settings.jobs, settings.device)
    training_service.apply_roulette_settings(settings.roulette)
    training_service.apply_database_settings(
        database_configuration.settings,
        database_configuration.sqlite_path,
    )

    if inference_service is None:
        inference_service = resolved["InferenceService"](
            dataset_repository=dataset_repository,
            inference_repository=inference_repository,
            checkpoint_service=checkpoint_service,
        )
        application.state.inference_service = inference_service
    settings_service = SettingsService(runtime_database, training_service)
    application.state.settings_service = settings_service

    application.state.training_service = training_service
    application.state.inference_service = inference_service

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
    application.state.database = None
    application.state.dataset_repository = None
    application.state.inference_repository = None
    application.state.dataset_service = None
    application.state.training_run_manager = None
    application.state.checkpoint_service = None
    application.state.training_service = None
    application.state.settings_service = None
    application.state.inference_service = None
    database_configuration_store: DatabaseConfigurationStore | None = None
    runtime_database = RuntimeDatabaseManager()
    application.state.runtime_database = runtime_database
    startup_database: FAIRSDatabase | None = None
    try:
        bootstrap_runtime()
        warnings.filterwarnings("ignore", category=FutureWarning)
        ensure_single_process_runtime()
        application.version = get_application_version()
        if not getattr(application.state, "client_routes_configured", False):
            configure_client_routes(application)
            application.state.client_routes_configured = True

        database_configuration_store = DatabaseConfigurationStore()
        application.state.database_configuration_service = DatabaseConfigurationService(
            store=database_configuration_store,
            runtime_database=runtime_database,
            application=application,
            activate_services=lambda loaded, app_settings: _activate_runtime_services(
                application, loaded, app_settings
            ),
        )
        try:
            loaded_database = database_configuration_store.load_or_initialize()
            run_startup_validations(
                JsonServerSettings().to_server_settings(loaded_database.settings)
            )
            initialize_database(
                loaded_database.settings,
                database_path=loaded_database.sqlite_path,
            )
            startup_database = FAIRSDatabase(
                loaded_database.settings,
                database_path=loaded_database.sqlite_path,
            )
            app_settings = ApplicationSettingsRepository().ensure_row(
                startup_database
            )
            server_settings = app_settings.to_server_settings(loaded_database.settings)
            run_startup_validations(server_settings)
            with runtime_database.switching():
                runtime_database.activate(startup_database)
                try:
                    _activate_runtime_services(application, loaded_database, app_settings)
                except Exception:
                    runtime_database.activate(None)
                    raise
            startup_database = None
            application.state.lifecycle = "ready"
        except Exception as exc:  # noqa: BLE001
            if startup_database is not None:
                startup_database.dispose()
                startup_database = None
            application.state.recovery_message = (
                "The saved database could not be opened or initialized. Review the Database settings and try again."
            )
            application.state.lifecycle = "recovery"
            logger.error(
                "Database startup entered recovery mode (%s).",
                type(exc).__name__,
            )

        yield
    finally:
        application.state.lifecycle = "stopping"
        inference_service = application.state.inference_service
        training_service = application.state.training_service
        training_run_manager = application.state.training_run_manager
        if inference_service is not None:
            try:
                inference_service.shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Inference service shutdown failed")

        if training_service is not None:
            try:
                training_service.shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Training service shutdown failed")
        if training_run_manager is not None:
            try:
                training_run_manager.shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Training manager shutdown failed")

        try:
            runtime_database.dispose()
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
        settings_router,
        database_settings_router,
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

    @application.middleware("http")
    async def database_runtime_guard(request: Request, call_next):
        api_prefix = f"{FASTAPI_API_PREFIX}/"
        path = request.url.path
        exempt = path == f"{FASTAPI_API_PREFIX}/health" or path.startswith(
            f"{FASTAPI_API_PREFIX}/settings/database"
        )
        if path.startswith(api_prefix) and not exempt:
            if getattr(request.app.state, "lifecycle", "starting") == "recovery":
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Database services are unavailable. Configure a working database."},
                )
            database_manager = getattr(request.app.state, "runtime_database", None)
            if database_manager is not None:
                try:
                    with database_manager.operation():
                        return await call_next(request)
                except DatabaseSwitchConflict as exc:
                    return JSONResponse(status_code=409, content={"detail": str(exc)})
                except DatabaseUnavailableError as exc:
                    return JSONResponse(status_code=503, content={"detail": str(exc)})
        return await call_next(request)

    @application.exception_handler(RequestValidationError)
    async def sanitized_database_validation_error(
        request: Request, _exc: RequestValidationError
    ):
        if "/settings/database" in request.url.path:
            return JSONResponse(
                status_code=422,
                content={"detail": "Invalid database configuration. Review the required fields and options."},
            )
        return await request_validation_exception_handler(request, _exc)

    include_api_routers(application)
    return application


###############################################################################
app = create_app()
