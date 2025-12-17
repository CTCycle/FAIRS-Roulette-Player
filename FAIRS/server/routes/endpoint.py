from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status


router = APIRouter(prefix="/base", tags=["base"])


###############################################################################
class Endpoint:
    def __init__(
        self,
        router: APIRouter,      
    ) -> None:
        self.router = router     

    # -------------------------------------------------------------------------
    def health_check(self) -> dict[str, Any]:
        return {"status": "healthy"}

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/health",
            self.health_check,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )

      

base_endpoint = Endpoint(router=router)
base_endpoint.add_routes()

