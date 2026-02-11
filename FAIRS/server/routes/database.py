from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from FAIRS.server.repositories.serialization.data import DataSerializer


router = APIRouter(prefix="/database", tags=["database"])


###############################################################################
class DatabaseEndpoint:
    
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.serializer = DataSerializer()

    # -------------------------------------------------------------------------
    def list_roulette_datasets(self) -> dict[str, Any]:
        datasets = self.serializer.list_datasets(dataset_kind="training")
        return {"datasets": datasets}

    # -------------------------------------------------------------------------
    def list_roulette_datasets_summary(self) -> dict[str, Any]:
        datasets = self.serializer.list_datasets_summary(dataset_kind="training")
        return {"datasets": datasets}

    # -------------------------------------------------------------------------
    def delete_roulette_dataset(self, dataset_id: int) -> dict[str, Any]:
        self.serializer.delete_dataset(dataset_id)
        return {"status": "deleted", "dataset_id": dataset_id}

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/roulette-series/datasets",
            self.list_roulette_datasets,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/roulette-series/datasets/summary",
            self.list_roulette_datasets_summary,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/roulette-series/datasets/{dataset_id}",
            self.delete_roulette_dataset,
            methods=["DELETE"],
            status_code=status.HTTP_200_OK,
        )


database_endpoint = DatabaseEndpoint(router=router)
database_endpoint.add_routes()
