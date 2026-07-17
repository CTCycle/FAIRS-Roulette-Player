from __future__ import annotations

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from server.common import path as shared_paths

###############################################################################
def _build_log_config() -> dict[str, Any]:
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    configured_log_dir = os.getenv("FAIRS_LOG_DIR")
    log_directory = (
        Path(configured_log_dir).expanduser()
        if configured_log_dir
        else shared_paths.LOGS_PATH
    )
    log_directory.mkdir(parents=True, exist_ok=True)
    log_filename = log_directory / f"FAIRS_{current_timestamp}.log"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%d-%m-%Y %H:%M:%S",
            },
            "minimal": {
                "format": "[%(levelname)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "minimal",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "default",
                "filename": str(log_filename),
                "mode": "a",
                "delay": True,
            },
        },
        "loggers": {
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "matplotlib": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
        },
    }


logging.config.dictConfig(_build_log_config())
logger = logging.getLogger()
