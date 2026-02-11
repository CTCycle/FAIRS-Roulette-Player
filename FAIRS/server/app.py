from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

from FAIRS.server.common.utils.variables import env_variables  # noqa: F401

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from FAIRS.server.routes.upload import router as upload_router
from FAIRS.server.routes.training import router as training_router
from FAIRS.server.routes.database import router as database_router
from FAIRS.server.routes.inference import router as inference_router
from FAIRS.server.repositories.database.initializer import initialize_database
from FAIRS.server.common.constants import (
    FASTAPI_DESCRIPTION,
    FASTAPI_TITLE,
    FASTAPI_VERSION,
)

###############################################################################
app = FastAPI(
    title=FASTAPI_TITLE,
    version=FASTAPI_VERSION,
    description=FASTAPI_DESCRIPTION,
)

app.include_router(upload_router)
app.include_router(training_router)
app.include_router(inference_router)
app.include_router(database_router)


@app.on_event("startup")
def ensure_database_initialized() -> None:
    initialize_database()


@app.get("/")
def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")
