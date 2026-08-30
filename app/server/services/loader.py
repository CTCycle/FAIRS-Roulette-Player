from __future__ import annotations

from io import BytesIO
from pathlib import PurePath
from typing import Any

import pandas as pd


###############################################################################
class TabularFileLoader:
    # -------------------------------------------------------------------------
    def load_bytes(
        self,
        content: bytes,
        filename: str,
        *,
        csv_separator: str = ";",
        sheet_name: str | int = 0,
        kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        extension = PurePath(filename).suffix.lower()
        payload = kwargs or {}
        if extension == ".csv":
            return pd.read_csv(
                BytesIO(content),
                sep=csv_separator,
                encoding="utf-8",
                **payload,
            )
        if extension in {".xlsx", ".xls"}:
            return pd.read_excel(
                BytesIO(content),
                sheet_name=sheet_name,
                **payload,
            )
        raise ValueError(f"Unsupported file extension: {extension}")
