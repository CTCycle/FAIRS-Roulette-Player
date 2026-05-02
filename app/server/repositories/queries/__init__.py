from __future__ import annotations

from server.repositories.queries.data import (
    DataRepositoryQueries as DataRepositoryQueries,
)
from server.repositories.queries.training import (
    TrainingRepositoryQueries as TrainingRepositoryQueries,
)

__all__ = ["DataRepositoryQueries", "TrainingRepositoryQueries"]
