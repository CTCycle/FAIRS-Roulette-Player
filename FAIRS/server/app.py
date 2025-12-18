from __future__ import annotations

# Load environment variables early (before Keras imports)
from FAIRS.server.utils.variables import env_variables  # noqa: F401

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from FAIRS.server.routes.upload import router as upload_router
from FAIRS.server.routes.training import router as training_router
from FAIRS.server.routes.database import router as database_router
from FAIRS.server.routes.inference import router as inference_router
from FAIRS.server.utils.configurations import server_settings

###############################################################################
app = FastAPI(
    title=server_settings.fastapi.title,
    version=server_settings.fastapi.version,
    description=server_settings.fastapi.description,
)

app.include_router(upload_router)
app.include_router(training_router)
app.include_router(inference_router)
app.include_router(database_router)

@app.get("/")
def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")
