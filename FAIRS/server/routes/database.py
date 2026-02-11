from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from FAIRS.server.repositories.schemas.models import (
    DatasetOutcomes,
    Datasets,
    InferenceSessions,
    InferenceSessionSteps,
    RouletteOutcomes,
)
from FAIRS.server.configurations import server_settings
from FAIRS.server.repositories.queries.data import DataRepositoryQueries
from FAIRS.server.repositories.serialization.data import DataSerializer


router = APIRouter(prefix="/database", tags=["database"])


TABLE_REGISTRY: dict[str, tuple[str, Any]] = {
    "roulette_outcomes": ("Roulette Outcomes", RouletteOutcomes),
    "datasets": ("Datasets", Datasets),
    "dataset_outcomes": ("Dataset Outcomes", DatasetOutcomes),
    "inference_sessions": ("Inference Sessions", InferenceSessions),
    "inference_session_steps": ("Inference Session Steps", InferenceSessionSteps),
}


###############################################################################
class DatabaseEndpoint:
    
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.fetch_limit = server_settings.database.browse_batch_size
        self.queries = DataRepositoryQueries()
        self.serializer = DataSerializer()

    # -------------------------------------------------------------------------
    def list_tables(self) -> list[dict[str, str]]:
        tables = []
        for table_name, (verbose_name, _) in TABLE_REGISTRY.items():
            tables.append({"name": table_name, "verbose_name": verbose_name})
        return tables

    # -------------------------------------------------------------------------
    def get_table_data(
        self,
        table_name: str,
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        if table_name not in TABLE_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found",
            )
        df = self.queries.load_table(
            table_name,
            limit=self.fetch_limit,
            offset=offset,
        )
        return {
            "columns": df.columns.tolist(),
            "rows": df.to_dict(orient="records"),
            "offset": offset,
            "limit": self.fetch_limit,
        }

    # -------------------------------------------------------------------------
    def get_table_stats(self, table_name: str) -> dict[str, Any]:
        if table_name not in TABLE_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found",
            )
        verbose_name = TABLE_REGISTRY[table_name][0]
        row_count = self.queries.count_rows(table_name)
        col_count = self.queries.count_columns(table_name)
        return {
            "table_name": table_name,
            "verbose_name": verbose_name,
            "row_count": row_count,
            "column_count": col_count,
        }

    # -------------------------------------------------------------------------
    def list_roulette_datasets(self) -> dict[str, Any]:
        datasets = self.serializer.list_datasets(dataset_kind="training")
        return {"datasets": datasets}

    # -------------------------------------------------------------------------
    def list_roulette_datasets_summary(self) -> dict[str, Any]:
        datasets = self.serializer.list_datasets_summary(dataset_kind="training")
        return {"datasets": datasets}

    # -------------------------------------------------------------------------
    def delete_roulette_dataset(self, dataset_id: str) -> dict[str, str]:
        self.serializer.delete_dataset(dataset_id)
        return {"status": "deleted", "dataset_id": dataset_id}

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/tables",
            self.list_tables,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/tables/{table_name}",
            self.get_table_data,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/tables/{table_name}/stats",
            self.get_table_stats,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
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
