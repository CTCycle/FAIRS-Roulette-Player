from __future__ import annotations

import os

from server.common import path as shared_paths
from server.common.utils.logger import configure_logging
from server.configurations.environment import load_environment

###############################################################################
def bootstrap_runtime(*, force: bool = False) -> None:
    """Load environment and configure runtime paths/logging explicitly."""
    load_environment(force=force)
    shared_paths.configure_runtime_paths(os.getenv("FAIRS_DATA_DIR"))
    configure_logging(os.getenv("FAIRS_LOG_DIR"), force=force)
