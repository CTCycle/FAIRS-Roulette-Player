from __future__ import annotations

import os
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

from FAIRS.server.common.utils.variables import env_variables  # noqa: F401

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from FAIRS.server.common.constants import (
    FASTAPI_DESCRIPTION,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)
from FAIRS.server.repositories.database.initializer import (
    initialize_sqlite_on_startup_if_missing,
)
from FAIRS.server.routes.database import router as database_router
from FAIRS.server.routes.inference import router as inference_router
from FAIRS.server.routes.training import router as training_router
from FAIRS.server.routes.upload import router as upload_router


###############################################################################
def is_api_docs_enabled() -> bool:
    raw = os.getenv("ENABLE_API_DOCS", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


ENABLE_API_DOCS = is_api_docs_enabled()

###############################################################################
app = FastAPI(
    title=FASTAPI_TITLE,
    version=FASTAPI_VERSION,
    description=FASTAPI_DESCRIPTION,
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)

app.include_router(upload_router)
app.include_router(training_router)
app.include_router(database_router)
app.include_router(inference_router)


@app.on_event("startup")
def initialize_embedded_database() -> None:
    initialize_sqlite_on_startup_if_missing()


@app.get("/")
def redirect_to_docs() -> RedirectResponse | dict[str, str]:
    if ENABLE_API_DOCS:
        return RedirectResponse(url="/docs")
    return {"status": "ok"}
