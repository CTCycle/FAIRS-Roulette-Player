from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from FAIRS.server.database.database import database
from FAIRS.server.database.schema import (
    CheckpointSummary,
    PredictedGames,
    RouletteSeries,
)
from FAIRS.server.utils.configurations import server_settings


router = APIRouter(prefix="/database", tags=["database"])


TABLE_REGISTRY: dict[str, tuple[str, Any]] = {
    "ROULETTE_SERIES": ("Roulette Series", RouletteSeries),
    "PREDICTED_GAMES": ("Predicted Games", PredictedGames),
    "CHECKPOINTS_SUMMARY": ("Checkpoints Summary", CheckpointSummary),
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


database_endpoint = DatabaseEndpoint(router=router)
database_endpoint.add_routes()
