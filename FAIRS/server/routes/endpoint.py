from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Body, status

from FAIRS.server.schemas.base import GeneralModel


router = APIRouter(prefix="/base", tags=["tags"])


###############################################################################
class Endpoint:
    def __init__(
        self,
        router: APIRouter,      
    ) -> None:
        self.router = router     

    # -------------------------------------------------------------------------
    def first_method(
        self,
        payload: GeneralModel = Body(...),
    ) -> dict[str, Any]:
        return {"param_A": payload.param_A, "param_B": payload.param_B}

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/base",
            self.first_method,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )

      

base_endpoint = Endpoint(router=router)
base_endpoint.add_routes()
