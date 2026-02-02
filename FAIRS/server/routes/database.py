from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from FAIRS.server.repositories.database import database
from FAIRS.server.repositories.schema import (
    GameSessions,
    InferenceContext,
    RouletteSeries,
)
from FAIRS.server.utils.constants import ROULETTE_SERIES_TABLE
from FAIRS.server.configurations import server_settings
from FAIRS.server.repositories.serializer import DataSerializer


router = APIRouter(prefix="/database", tags=["database"])


TABLE_REGISTRY: dict[str, tuple[str, Any]] = {
    "ROULETTE_SERIES": ("Roulette Series", RouletteSeries),
    "INFERENCE_CONTEXT": ("Inference Context", InferenceContext),
    "GAME_SESSIONS": ("Game Sessions", GameSessions),
}


###############################################################################
class DatabaseEndpoint:
    
    def __init__(self, router: APIRouter) -> None:
        self.router = router
        self.fetch_limit = server_settings.database.fetch_row_limit

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
        df = database.load_paginated(table_name, offset, self.fetch_limit)
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
        row_count = database.count_rows(table_name)
        col_count = database.count_columns(table_name)
        return {
            "table_name": table_name,
            "verbose_name": verbose_name,
            "row_count": row_count,
            "column_count": col_count,
        }

    # -------------------------------------------------------------------------
    def list_roulette_datasets(self) -> dict[str, Any]:
        datasets = database.load_distinct_values(ROULETTE_SERIES_TABLE, "dataset_name")
        return {"datasets": datasets}

    # -------------------------------------------------------------------------
    def list_roulette_datasets_summary(self) -> dict[str, Any]:
        grouped = database.load_grouped_counts(ROULETTE_SERIES_TABLE, "dataset_name")
        datasets = []
        for row in grouped:
            value = row.get("value")
            count = row.get("count", 0)
            if value is None:
                continue
            datasets.append({"dataset_name": str(value), "row_count": int(count or 0)})
        return {"datasets": datasets}

    # -------------------------------------------------------------------------
    def delete_roulette_dataset(self, dataset_name: str) -> dict[str, str]:
        serializer = DataSerializer()
        serializer.delete_roulette_dataset(dataset_name)
        return {"status": "deleted", "dataset_name": dataset_name}

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
            "/roulette-series/datasets/{dataset_name}",
            self.delete_roulette_dataset,
            methods=["DELETE"],
            status_code=status.HTTP_200_OK,
        )


database_endpoint = DatabaseEndpoint(router=router)
database_endpoint.add_routes()
